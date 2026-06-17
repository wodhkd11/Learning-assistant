# docs/interfaces.md — 모듈 간 인터페이스 계약

> **이 파일은 모든 코더의 단일 진실 공급원(Single Source of Truth)이다.**
> 함수 시그니처, 클래스 구조, API 응답 형식이 여기 정의된 것과 다를 경우 모듈 간 연동이 깨진다.
> 변경 시 반드시 오케스트레이터 승인 후 이 파일을 먼저 업데이트하고 구현한다.

---

## 1. Repository 인터페이스 (모듈 E, F, X)

```python
# backend/storage/repository.py

from abc import ABC, abstractmethod
from backend.schemas.document import DocumentRecord

class BaseRepository(ABC):
    @abstractmethod
    async def save(self, doc: DocumentRecord) -> str:
        """문서를 저장하고 file_path를 반환한다."""
        ...

    @abstractmethod
    async def get(self, title: str) -> DocumentRecord | None:
        """제목으로 문서를 조회한다."""
        ...

    @abstractmethod
    async def exists_by_url(self, url: str) -> bool:
        """URL 중복 여부를 확인한다. 파일 파싱 없이 DB 조회로 처리."""
        ...

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[dict]:
        """하이브리드 검색. 벡터 + 메타데이터 필터 결합."""
        ...
```

```python
# backend/storage/composite.py

class CompositeRepository(BaseRepository):
    def __init__(
        self,
        obsidian: ObsidianRepository,
        chroma: ChromaRepository
    ): ...

    async def save(self, doc: DocumentRecord) -> str:
        """
        1. obsidian.save(doc) → file_path
        2. chroma.index(doc, file_path)
        순서 고정. 두 작업을 atomic하게 처리.
        """
        ...

    async def exists_by_url(self, url: str) -> bool:
        """chroma.exists_by_url() 위임. 파일 파싱 없음."""
        ...

    async def list_documents(
        self,
        category: str | None = None,
        tag: str | None = None,
        series: str | None = None,
        document_type: str | None = None,
    ) -> list[dict]:
        """chroma.list_documents() 위임. 파일 파싱 없음."""
        ...

    async def get_stats(self) -> dict:
        """chroma.get_stats() 위임."""
        ...
```

---

## 2. LLM 클라이언트 인터페이스 (모듈 C, D)

```python
# backend/llm/factory.py

from abc import ABC, abstractmethod
from backend.schemas.llm import AnalysisResult

class BaseLLMClient(ABC):
    @abstractmethod
    async def analyze(
        self,
        content: str,
        title: str,
        vault_context: list[dict],  # ChromaDB metadata 쿼리 결과
        url: str = "",              # series 판단에 활용
    ) -> AnalysisResult:
        """
        문서를 분석하여 AnalysisResult를 반환한다.
        저장 로직은 포함하지 않는다.
        vault_context는 연관 후보 문서 목록 (최대 5개).
        """
        ...

class LLMFactory:
    @staticmethod
    def get_priority_list() -> list[str]:
        """settings.LLM_PRIORITY 콤마 구분 문자열을 순서 있는 리스트로 반환."""
        ...

    @staticmethod
    def create(provider: str) -> BaseLLMClient:
        """
        provider: 'xai' | 'groq' | 'gemini' | 'claude'
        settings.LLM_PRIORITY 순서로 순회하며 호출.
        """
        ...
```

---

## 3. Worker 인터페이스 (모듈 B, C, D)

```python
# backend/workers/queue_manager.py

import asyncio

# 전역 싱글턴 큐 — 라우터와 워커가 공유
ingestion_queue: asyncio.Queue  # CollectRequest 객체를 담음

async def worker_1_loop() -> None:
    """
    ingestion_queue에서 CollectRequest를 꺼내
    classifier.classify()를 호출한다.
    True 판정 시 analysis_queue에 적재.
    Ollama 장애 시 queue_db.save_failed()로 영속화.
    """
    ...

async def worker_2_loop() -> None:
    """
    analysis_queue에서 CollectRequest를 꺼내
    analyzer.analyze()를 호출한다.
    결과를 CompositeRepository.save()에 전달.
    """
    ...
```

```python
# backend/workers/classifier.py

from backend.schemas.llm import ClassificationResult
from backend.schemas.document import CollectRequest

async def classify(request: CollectRequest) -> ClassificationResult:
    """
    Ollama API를 호출하여 문서의 지식 가치를 이진 분류한다.
    반환: ClassificationResult
    예외: OllamaUnavailableError (호출자가 failed_tasks.db에 저장)
    """
    ...
```

```python
# backend/workers/analyzer.py

from backend.schemas.document import CollectRequest, DocumentRecord
from backend.schemas.llm import AnalysisResult

async def analyze(request: CollectRequest, repo: BaseRepository) -> DocumentRecord:
    """
    1. repo.search()로 연관 후보 추출 (ChromaDB 쿼리)
    2. LLMFactory.create()로 클라이언트 생성
    3. client.analyze()로 AnalysisResult 생성
    4. DocumentRecord 조립 후 반환
    저장은 호출자(worker_2_loop)가 repo.save()로 처리.
    """
    ...
```

---

## 4. ChromaDB 저장 스키마 (모듈 F, X)

```python
# backend/storage/chroma.py

class ChromaRepository:
    COLLECTION_NAME = "kalf_documents"

    async def index(self, doc: DocumentRecord, file_path: str) -> None:
        """
        ChromaDB에 문서를 색인한다.
        id: hashlib.sha256(doc.url.encode()).hexdigest()
        document: doc.refined_content  (임베딩 대상)
        metadata: {
            "url":          str,
            "title":        str,
            "summary":      str,
            "category":     str,
            "tags":         str,   # ",".join(doc.tags) — list 금지
            "collected_at": str,   # ISO 8601
            "file_path":    str,   # obsidian_vault/ 내 상대 경로
            # optional (존재할 때만 저장)
            "series":       str,   # URL 패턴으로 감지한 시리즈 ID
            "series_title": str,   # LLM이 판단한 사람 가독 제목
            "series_order": int,   # 챕터/페이지 순서
            # 항상 저장 (없으면 "other")
            "document_type": str,  # paper | tutorial | blog | wiki | docs | news | other
            # optional (paper일 때만 저장)
            "paper_authors": str,  # ",".join(authors) — list 금지
            "paper_year":    int,  # published_year (없으면 0)
            "paper_venue":   str,  # 학술지/학회명
        }
        """
        ...

    async def search_hybrid(
        self,
        query: str,
        limit: int = 5,
        where: dict | None = None
    ) -> list[dict]:
        """
        벡터 검색 + metadata where 절 필터 결합.
        반환: [{"title", "url", "summary", "category", "tags", "score", "file_path"}]
        tags는 split(",")으로 list[str]로 변환하여 반환.
        """
        ...

    async def exists_by_url(self, url: str) -> bool:
        """SHA256 해시 id로 중복 확인. 파일 파싱 없음."""
        ...

    async def get_metadata_by_title(self, title: str) -> dict | None:
        """제목으로 metadata 조회."""
        ...
```

---

## 5. MCP Tool 인터페이스 (모듈 G)

MCP 서버는 아래 Tool을 구현한다. 모두 FastAPI 엔드포인트를 내부 HTTP 호출로 위임한다.

| Tool 이름 | 파라미터 | 반환 |
|-----------|---------|------|
| `search_vault` | `query: str`, `limit: int = 5`, `series: str \| None`, `document_type: str \| None` | `list[SearchResult]` |
| `get_document` | `title: str` | `DocumentRecord \| None` |
| `list_documents` | `category: str \| None`, `tag: str \| None`, `series: str \| None`, `document_type: str \| None` | `list[SearchResult]` |
| `get_related` | `title: str` | `list[dict]` |
| `get_stats` | 없음 | `VaultStats` |

---

## 6. FastAPI API 엔드포인트 계약

### 수집
```
POST /api/v1/collect
Body: CollectRequest
Response 200: CollectResponse
```

### 검색
```
GET  /api/v1/search?q={query}&limit={n}                    → list[SearchResult]
GET  /api/v1/search?tag={tag}                              → list[SearchResult]
GET  /api/v1/search?series={series_id}                     → list[SearchResult]
GET  /api/v1/search?type={document_type}                   → list[SearchResult]
GET  /api/v1/document/{title}                              → DocumentRecord | 404
GET  /api/v1/documents?category=&tag=&series=&document_type= → list[SearchResult]
POST /api/v1/index/rebuild                                 → {"status": "started"}
```

---

## 7. 글로벌 싱글턴 의존성 (backend/main.py에서 초기화)

```python
# 아래 객체들은 lifespan에서 초기화되어 app.state에 저장된다.
# 라우터/워커는 Depends()를 통해 주입받는다.

app.state.composite_repo: CompositeRepository
app.state.ingestion_queue: asyncio.Queue
app.state.analysis_queue: asyncio.Queue
```
