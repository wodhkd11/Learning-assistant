import structlog

from backend.schemas.document import DocumentRecord
from backend.storage.chroma import ChromaRepository
from backend.storage.obsidian import ObsidianRepository
from backend.storage.repository import BaseRepository

log = structlog.get_logger()


class CompositeRepository(BaseRepository):
    """
    저장소 단일 진입점.
    obsidian.save → chroma.index 순서를 보장하며,
    파일 저장 실패 시 색인을 실행하지 않는다.
    """

    def __init__(
        self,
        obsidian: ObsidianRepository,
        chroma: ChromaRepository,
    ) -> None:
        self._obsidian = obsidian
        self._chroma = chroma

    async def save(self, doc: DocumentRecord) -> str:
        """
        1. obsidian.save(doc) → file_path
        2. chroma.index(doc, file_path)
        3. 연관 문서에 양방향 backlink 추가 (대상 파일 없으면 조용히 스킵)
        순서 고정.
        """
        file_path = await self._obsidian.save(doc)
        await self._chroma.index(doc, file_path)

        for related in doc.related_docs:
            await self._obsidian.add_backlink(
                target_title=related.title,
                new_title=doc.title,
                reason=related.reason,
            )

        log.info("composite_saved", title=doc.title, file_path=file_path)
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

    async def list_documents(
        self,
        category: str | None = None,
        tag: str | None = None,
        series: str | None = None,
        document_type: str | None = None,
    ) -> list[dict]:
        """chroma.list_documents() 위임. 파일 파싱 없음."""
        return await self._chroma.list_documents(
            category=category, tag=tag, series=series, document_type=document_type
        )

    async def get_stats(self) -> dict:
        """chroma.get_stats() 위임."""
        return await self._chroma.get_stats()
