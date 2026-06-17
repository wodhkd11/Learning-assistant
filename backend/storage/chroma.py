import asyncio
import hashlib
from typing import Optional

import chromadb
import structlog
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from backend.config import settings
from backend.schemas.document import DocumentRecord
from backend.storage.repository import BaseRepository

log = structlog.get_logger()


def init_chroma() -> "ChromaRepository":
    """lifespan에서 호출하는 팩토리 함수. PersistentClient 사용."""
    return ChromaRepository()


class ChromaRepository(BaseRepository):
    COLLECTION_NAME = "kalf_documents"

    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        self._ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _url_to_id(url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()

    def _to_result_dict(self, meta: dict, score: float = 1.0) -> dict:
        tags_raw = meta.get("tags", "") or ""
        tags = [t for t in tags_raw.split(",") if t]
        series_order = meta.get("series_order")
        return {
            "title": meta.get("title", ""),
            "url": meta.get("url", ""),
            "summary": meta.get("summary", ""),
            "category": meta.get("category", ""),
            "tags": tags,
            "collected_at": meta.get("collected_at", ""),
            "score": round(score, 4),
            "file_path": meta.get("file_path", ""),
            "series": meta.get("series") or None,
            "series_title": meta.get("series_title") or None,
            "series_order": int(series_order) if series_order is not None else None,
            "document_type": meta.get("document_type") or None,
        }

    @staticmethod
    def _keyword_score(query: str, meta: dict) -> float:
        terms = set(query.lower().split())
        if not terms:
            return 0.0
        haystack = " ".join([
            meta.get("tags", "") or "",
            meta.get("category", "") or "",
            meta.get("summary", "") or "",
        ]).lower()
        matched = sum(1 for t in terms if t in haystack)
        return matched / len(terms)

    # ------------------------------------------------------------------
    # BaseRepository interface
    # ------------------------------------------------------------------

    async def save(self, doc: DocumentRecord) -> str:
        raise NotImplementedError(
            "ChromaRepository.save()는 직접 호출 금지. CompositeRepository를 사용하세요."
        )

    async def get(self, title: str) -> DocumentRecord | None:
        # ChromaDB에는 전문이 없음. CompositeRepository가 ObsidianRepository로 위임.
        return None

    async def exists_by_url(self, url: str) -> bool:
        """SHA256 해시 id로 중복 확인. 파일 파싱 없음."""
        doc_id = self._url_to_id(url)
        result = await asyncio.to_thread(
            self._collection.get, ids=[doc_id], include=[]
        )
        return len(result["ids"]) > 0

    async def search(self, query: str, limit: int = 5) -> list[dict]:
        return await self.search_hybrid(query, limit=limit)

    # ------------------------------------------------------------------
    # ChromaRepository-specific API
    # ------------------------------------------------------------------

    async def index(self, doc: DocumentRecord, file_path: str) -> None:
        """
        ChromaDB에 문서를 색인한다.
        tags는 콤마 구분 문자열로 저장 (list 타입 금지).
        """
        doc_id = self._url_to_id(doc.url)
        metadata: dict = {
            "url": doc.url,
            "title": doc.title,
            "summary": doc.summary,
            "category": doc.category,
            "tags": ",".join(doc.tags),          # list 금지, 콤마 구분 문자열 필수
            "collected_at": doc.collected_at.isoformat(),
            "file_path": file_path,
        }
        if doc.series is not None:
            metadata["series"] = doc.series
        if doc.series_title is not None:
            metadata["series_title"] = doc.series_title
        if doc.series_order is not None:
            metadata["series_order"] = doc.series_order
        metadata["document_type"] = doc.document_type or "other"
        if doc.paper_meta:
            pm = doc.paper_meta
            metadata["paper_authors"] = ",".join(pm.get("authors") or [])
            metadata["paper_year"] = pm.get("published_year") or 0
            metadata["paper_venue"] = pm.get("venue") or ""
        await asyncio.to_thread(
            self._collection.upsert,
            ids=[doc_id],
            documents=[doc.refined_content],
            metadatas=[metadata],
        )
        log.info("chroma.indexed", title=doc.title, url=doc.url)

    async def search_hybrid(
        self,
        query: str,
        limit: int = 5,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """
        벡터 유사도 × HYBRID_VECTOR_WEIGHT + 키워드 스코어 × (1 - HYBRID_VECTOR_WEIGHT).
        where 절은 category 등 $eq 필터에만 사용. 파일 파싱 없음.
        """
        total = await asyncio.to_thread(self._collection.count)
        if total == 0:
            return []

        n_results = min(limit, total)
        kwargs: dict = {
            "query_texts": [query],
            "n_results": n_results,
            "include": ["metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        try:
            results = await asyncio.to_thread(self._collection.query, **kwargs)
        except Exception as exc:
            log.error("chroma.query_failed", error=str(exc))
            return []

        output: list[dict] = []
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for meta, dist in zip(metas, distances):
            # cosine distance ∈ [0, 2] → similarity ∈ [0, 1]
            vector_score = max(0.0, 1.0 - dist / 2.0)
            kw_score = self._keyword_score(query, meta)
            hybrid = (
                vector_score * settings.HYBRID_VECTOR_WEIGHT
                + kw_score * (1.0 - settings.HYBRID_VECTOR_WEIGHT)
            )
            output.append(self._to_result_dict(meta, score=hybrid))

        return sorted(output, key=lambda x: x["score"], reverse=True)

    async def get_metadata_by_title(self, title: str) -> dict | None:
        """제목으로 metadata 조회. tags는 list[str]로 복원."""
        results = await asyncio.to_thread(
            self._collection.get,
            where={"title": {"$eq": title}},
            include=["metadatas"],
        )
        if not results["ids"]:
            return None
        meta = results["metadatas"][0].copy()
        tags_raw = meta.get("tags", "") or ""
        meta["tags"] = [t for t in tags_raw.split(",") if t]
        return meta

    async def list_documents(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        series: Optional[str] = None,
        document_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        전체 문서 목록. category/series/document_type은 where 절, tag는 클라이언트 사이드 필터.
        파일 파싱 없음 — ChromaDB 단일 쿼리.
        """
        where_conditions: list[dict] = []
        if category:
            where_conditions.append({"category": {"$eq": category}})
        if series:
            where_conditions.append({"series": {"$eq": series}})
        if document_type:
            where_conditions.append({"document_type": {"$eq": document_type}})

        where: dict = {}
        if len(where_conditions) == 1:
            where = where_conditions[0]
        elif len(where_conditions) > 1:
            where = {"$and": where_conditions}

        kwargs: dict = {"include": ["metadatas"], "limit": limit}
        if where:
            kwargs["where"] = where

        results = await asyncio.to_thread(self._collection.get, **kwargs)

        output: list[dict] = []
        for meta in results["metadatas"]:
            item = self._to_result_dict(meta, score=1.0)
            if tag and tag not in item["tags"]:
                continue
            output.append(item)
        return output

    async def get_stats(self) -> dict:
        """볼트 전체 통계. 파일 파싱 없음 — ChromaDB metadata 집계."""
        results = await asyncio.to_thread(
            self._collection.get, include=["metadatas"]
        )
        categories: dict[str, int] = {}
        tags_set: set[str] = set()
        latest: Optional[str] = None

        for meta in results["metadatas"]:
            cat = meta.get("category") or ""
            if cat:
                categories[cat] = categories.get(cat, 0) + 1

            for t in (meta.get("tags") or "").split(","):
                if t:
                    tags_set.add(t)

            ts = meta.get("collected_at") or ""
            if ts and (latest is None or ts > latest):
                latest = ts

        return {
            "total_documents": len(results["ids"]),
            "categories": categories,
            "latest_collected_at": latest,
            "total_tags": len(tags_set),
        }
