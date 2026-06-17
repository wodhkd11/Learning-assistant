from abc import ABC, abstractmethod

from backend.schemas.document import DocumentRecord


class BaseRepository(ABC):
    @abstractmethod
    async def save(self, doc: DocumentRecord) -> str:
        """문서를 저장하고 file_path를 반환한다."""

    @abstractmethod
    async def get(self, title: str) -> DocumentRecord | None:
        """제목으로 문서를 조회한다."""

    @abstractmethod
    async def exists_by_url(self, url: str) -> bool:
        """URL 중복 여부를 확인한다. 파일 파싱 없이 DB 조회로 처리."""

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[dict]:
        """하이브리드 검색. 벡터 + 메타데이터 필터 결합."""
