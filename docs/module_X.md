# 모듈 X — CompositeRepository (저장소 단일화 계층)

**담당 코더:** 코더 B
**브랜치:** `feat/module-E-X-storage`
**담당 파일:** `backend/storage/composite.py`, `backend/storage/repository.py`

---

## 목표

파일 저장(`ObsidianRepository`)과 벡터 색인(`ChromaRepository`)을 단일 `save()` 호출로 처리하여 역할 모순을 해소하고 원자성을 보장한다.

---

## 설계 원칙

- **모든 문서 저장은 반드시 `CompositeRepository.save()`를 통해서만 이루어진다.**
- 모듈 D(분석)의 `analyzer.py`는 `AnalysisResult`를 생성한 후 `CompositeRepository.save()`를 호출하지 않는다. `worker_2_loop`가 호출한다.
- 라우터, LLM 클라이언트가 `ObsidianRepository`나 `ChromaRepository`를 직접 호출하는 것을 금지한다.

---

## 인터페이스

`docs/interfaces.md` 섹션 1 참고.

```python
# backend/storage/repository.py
class BaseRepository(ABC):
    @abstractmethod
    async def save(self, doc: DocumentRecord) -> str: ...

    @abstractmethod
    async def get(self, title: str) -> DocumentRecord | None: ...

    @abstractmethod
    async def exists_by_url(self, url: str) -> bool: ...

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[dict]: ...
```

```python
# backend/storage/composite.py
class CompositeRepository(BaseRepository):
    def __init__(
        self,
        obsidian: ObsidianRepository,
        chroma: ChromaRepository
    ):
        self._obsidian = obsidian
        self._chroma = chroma

    async def save(self, doc: DocumentRecord) -> str:
        """
        1. obsidian.save(doc) → file_path 획득
        2. chroma.index(doc, file_path) → 벡터+메타데이터 색인
        순서 고정. 파일 저장 실패 시 색인하지 않음.
        """
        file_path = await self._obsidian.save(doc)
        await self._chroma.index(doc, file_path)
        return file_path

    async def exists_by_url(self, url: str) -> bool:
        """ChromaDB에 위임. 파일 파싱 없음."""
        return await self._chroma.exists_by_url(url)

    async def search(self, query: str, limit: int = 5) -> list[dict]:
        """ChromaDB 하이브리드 검색에 위임."""
        return await self._chroma.search_hybrid(query, limit)

    async def get(self, title: str) -> DocumentRecord | None:
        """파일에서 직접 읽어 반환."""
        return await self._obsidian.get(title)
```

---

## 호출 흐름

```
worker_2_loop
    → analyzer.analyze() → AnalysisResult
    → DocumentRecord 조립
    → composite_repo.save(doc)
        → obsidian.save(doc) → file_path
        → chroma.index(doc, file_path)
```

---

## 파일 구조

```
backend/storage/
├── repository.py    # BaseRepository 추상 인터페이스
├── composite.py     # CompositeRepository 구현체
├── obsidian.py      # ObsidianRepository (모듈 E)
└── chroma.py        # ChromaRepository (모듈 F)
```
