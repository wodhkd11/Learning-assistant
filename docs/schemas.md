# docs/schemas.md — 전체 Pydantic 스키마 정의

> 모든 스키마의 단일 진실 공급원. 임의로 필드를 추가/삭제하지 않는다.
> 변경 필요 시 오케스트레이터 승인 후 이 파일을 먼저 업데이트한다.

---

## 수집 요청/응답

```python
# backend/schemas/document.py

from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Literal

class CollectRequest(BaseModel):
    url: str
    title: str
    content: str          # Readability 추출 본문
    timestamp: datetime   # ISO 8601
    document_title: str | None = None  # document.title (브라우저 탭 제목)

class CollectResponse(BaseModel):
    status: Literal["queued", "duplicate", "blacklisted"]
    id: UUID
```

---

## 문서 레코드

```python
class RelatedDoc(BaseModel):
    title: str            # 연관 문서 제목 (Obsidian [[링크]] 대상)
    reason: str           # LLM이 서술한 연관 이유

class DocumentRecord(BaseModel):
    url: str
    title: str
    source_title: str     # 원본 페이지 제목 (가공 전)
    refined_content: str  # LLM이 정제·요약한 본문
    summary: str
    tags: list[str]
    category: str
    related_docs: list[RelatedDoc]
    collected_at: datetime
    updated_at: datetime
    series: str | None = None          # URL 패턴으로 감지한 시리즈 ID (예: "wikidocs-300272")
    series_title: str | None = None    # LLM이 판단한 사람 가독 시리즈 제목
    series_order: int | None = None    # 챕터/페이지 순서
    document_type: str | None = None   # paper | tutorial | blog | wiki | docs | news | other
    paper_meta: dict | None = None     # 논문일 때만: {authors, doi, published_year, venue}
```

---

## LLM 분류/분석 결과

```python
# backend/schemas/llm.py

class ClassificationResult(BaseModel):
    is_knowledge: bool
    confidence: float     # 0.0 ~ 1.0
    reason: str
    model_used: str       # 예: 'ollama/llama3:8b'
    latency_ms: int

class AnalysisResult(BaseModel):
    summary: str
    tags: list[str]
    category: str
    related_docs: list[RelatedDoc]
    refined_content: str
    series: str | None = None          # LLM이 판단한 시리즈 슬러그 (영문 소문자, 하이픈 구분)
    series_title: str | None = None    # LLM이 판단한 시리즈 한국어 제목
    series_order: int | None = None    # 시리즈 내 순서 (파악 불가능하면 None)
    document_type: str | None = None   # paper | tutorial | blog | wiki | docs | news | other
    paper_meta: dict | None = None     # 논문일 때만: {authors: list[str], doi: str, published_year: int, venue: str}
    # 저장 경로, ChromaDB id 등 저장 관련 필드 포함하지 않음
```

---

## 검색 결과

```python
# backend/schemas/search.py

class SearchResult(BaseModel):
    title: str
    url: str
    summary: str
    category: str
    tags: list[str]       # ChromaDB에서 조회 시 split(",")으로 복원
    collected_at: datetime
    score: float          # 하이브리드 스코어 0.0~1.0
    file_path: str        # obsidian_vault/ 내 상대 경로
    snippet: str | None   # 질의 관련 본문 발췌
    series: str | None = None
    series_title: str | None = None
    series_order: int | None = None
    document_type: str | None = None   # paper | tutorial | blog | wiki | docs | news | other

class VaultStats(BaseModel):
    total_documents: int
    categories: dict[str, int]   # {"AI/Software Engineering": 42, ...}
    latest_collected_at: datetime | None
    total_tags: int
```

---

## 예외 클래스

```python
# backend/exceptions.py

class OllamaUnavailableError(Exception):
    """Ollama 미가동 또는 타임아웃 시 발생. worker_1_loop가 캐치하여 영속 큐에 저장."""
    pass

class LLMRateLimitError(Exception):
    """상용 LLM 429 에러. LLMFactory fallback 트리거."""
    pass

class LLMAllProvidersFailedError(Exception):
    """Claude, Gemini 모두 실패 시 발생."""
    pass
```

---

## 환경변수 스키마

```python
# backend/config.py

from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # 저장소
    VAULT_PATH: str = str(Path(__file__).parent.parent / "obsidian_vault")
    CHROMA_DB_PATH: str = "./data/chroma"
    TEMP_DIR: str = "./.temp"

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3:8b"
    OLLAMA_TIMEOUT: int = 10  # seconds

    # 상용 LLM
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    XAI_API_KEY: str = ""
    LLM_PRIORITY: str = "xai,groq,gemini,claude"  # 콤마 구분 우선순위. 앞부터 순서대로 시도.

    # 검색
    HYBRID_VECTOR_WEIGHT: float = 0.7  # 키워드 가중치 = 1 - 이 값

    # 기타
    LOG_LEVEL: str = "INFO"
    KALF_API_URL: str = "http://localhost:8000"  # MCP 서버용

    class Config:
        env_file = ".env"

settings = Settings()
```
