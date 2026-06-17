"""tests/test_search.py — ChromaRepository 및 검색 API 단위 테스트.

ChromaDB: tmp_path의 PersistentClient 사용.
SentenceTransformerEmbeddingFunction: 고정 벡터를 반환하는 Mock으로 대체.
"""

import hashlib
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import chromadb
import pytest

from backend.schemas.document import DocumentRecord, RelatedDoc
from backend.schemas.search import SearchResult
from backend.storage.chroma import ChromaRepository


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

class _MockEF:
    """고정 임베딩을 반환하는 더미 EmbeddingFunction."""

    def __call__(self, input: list[str]) -> list[list[float]]:
        return [[0.1] * 384 for _ in input]

    def embed_query(self, input: list[str]) -> list[list[float]]:
        return [[0.1] * 384 for _ in input]

    def name(self) -> str:
        return "mock_ef"


@pytest.fixture()
def sample_doc() -> DocumentRecord:
    return DocumentRecord(
        url="https://example.com/fastapi-async",
        title="FastAPI 비동기 처리",
        source_title="FastAPI Async Processing Guide",
        refined_content="FastAPI에서 asyncio.Queue를 활용한 비동기 파이프라인 구축 방법",
        summary="FastAPI 비동기 처리 개요",
        tags=["fastapi", "async", "python"],
        category="AI/Software Engineering",
        related_docs=[],
        collected_at=datetime(2024, 6, 1, 12, 0, 0),
        updated_at=datetime(2024, 6, 1, 12, 0, 0),
    )


@pytest.fixture()
def chroma_repo(tmp_path: Path):
    """임시 경로 PersistentClient + Mock EF로 ChromaRepository를 생성한다."""
    mock_ef = _MockEF()
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))

    with patch("backend.storage.chroma.SentenceTransformerEmbeddingFunction", return_value=mock_ef):
        with patch("backend.storage.chroma.settings") as s:
            s.CHROMA_DB_PATH = str(tmp_path / "chroma")
            s.HYBRID_VECTOR_WEIGHT = 0.7

            repo = ChromaRepository.__new__(ChromaRepository)
            repo._client = client
            repo._ef = mock_ef
            repo._collection = client.get_or_create_collection(
                name=ChromaRepository.COLLECTION_NAME,
                embedding_function=mock_ef,
                metadata={"hnsw:space": "cosine"},
            )
            yield repo


# ------------------------------------------------------------------
# ChromaRepository 단위 테스트
# ------------------------------------------------------------------

class TestChromaRepository:

    @pytest.mark.asyncio
    async def test_index_and_exists_by_url(self, chroma_repo, sample_doc):
        assert await chroma_repo.exists_by_url(sample_doc.url) is False
        await chroma_repo.index(sample_doc, "FastAPI 비동기 처리.md")
        assert await chroma_repo.exists_by_url(sample_doc.url) is True

    @pytest.mark.asyncio
    async def test_tags_stored_as_comma_string(self, chroma_repo, sample_doc):
        """tags는 ChromaDB에 반드시 콤마 구분 문자열로 저장되어야 한다."""
        await chroma_repo.index(sample_doc, "test.md")
        doc_id = hashlib.sha256(sample_doc.url.encode()).hexdigest()
        raw = chroma_repo._collection.get(ids=[doc_id], include=["metadatas"])
        tags_raw = raw["metadatas"][0]["tags"]
        assert isinstance(tags_raw, str), "tags는 list가 아닌 str이어야 한다"
        assert tags_raw == "fastapi,async,python"

    @pytest.mark.asyncio
    async def test_get_metadata_by_title_found(self, chroma_repo, sample_doc):
        await chroma_repo.index(sample_doc, "test.md")
        meta = await chroma_repo.get_metadata_by_title(sample_doc.title)
        assert meta is not None
        assert meta["title"] == sample_doc.title
        assert isinstance(meta["tags"], list), "tags는 조회 시 list[str]로 복원되어야 한다"
        assert "fastapi" in meta["tags"]

    @pytest.mark.asyncio
    async def test_get_metadata_by_title_not_found(self, chroma_repo):
        meta = await chroma_repo.get_metadata_by_title("존재하지 않는 문서")
        assert meta is None

    @pytest.mark.asyncio
    async def test_list_documents_by_category(self, chroma_repo, sample_doc):
        await chroma_repo.index(sample_doc, "test.md")
        results = await chroma_repo.list_documents(category="AI/Software Engineering")
        assert len(results) == 1
        assert results[0]["title"] == sample_doc.title

    @pytest.mark.asyncio
    async def test_list_documents_by_tag(self, chroma_repo, sample_doc):
        await chroma_repo.index(sample_doc, "test.md")
        results = await chroma_repo.list_documents(tag="fastapi")
        assert len(results) == 1

        no_match = await chroma_repo.list_documents(tag="nonexistent_tag")
        assert len(no_match) == 0

    @pytest.mark.asyncio
    async def test_list_documents_wrong_category(self, chroma_repo, sample_doc):
        await chroma_repo.index(sample_doc, "test.md")
        results = await chroma_repo.list_documents(category="Other Category")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_list_documents_by_series(self, chroma_repo, tmp_path):
        """series 필터로 해당 시리즈 문서만 반환되어야 한다."""
        from datetime import datetime

        doc_with_series = DocumentRecord(
            url="https://wikidocs.net/300272/1",
            title="WikiDocs 1챕터",
            source_title="WikiDocs Chapter 1",
            refined_content="내용",
            summary="요약",
            tags=["python"],
            category="AI/Software Engineering",
            related_docs=[],
            collected_at=datetime(2024, 6, 1, 12, 0, 0),
            updated_at=datetime(2024, 6, 1, 12, 0, 0),
            series="wikidocs-300272",
            series_order=1,
        )
        await chroma_repo.index(doc_with_series, "wiki1.md")

        results = await chroma_repo.list_documents(series="wikidocs-300272")
        assert len(results) == 1
        assert results[0]["series"] == "wikidocs-300272"
        assert results[0]["series_order"] == 1

        no_match = await chroma_repo.list_documents(series="wikidocs-999999")
        assert len(no_match) == 0

    @pytest.mark.asyncio
    async def test_series_fields_in_result_dict(self, chroma_repo):
        """시리즈 없는 문서의 result dict에 series 키가 None으로 존재해야 한다."""
        from datetime import datetime

        doc = DocumentRecord(
            url="https://example.com/standalone",
            title="독립 문서",
            source_title="Standalone",
            refined_content="내용",
            summary="요약",
            tags=["test"],
            category="General",
            related_docs=[],
            collected_at=datetime(2024, 6, 1, 12, 0, 0),
            updated_at=datetime(2024, 6, 1, 12, 0, 0),
        )
        await chroma_repo.index(doc, "standalone.md")
        results = await chroma_repo.list_documents()
        assert len(results) == 1
        assert "series" in results[0]
        assert results[0]["series"] is None
        assert results[0]["series_order"] is None

    @pytest.mark.asyncio
    async def test_search_hybrid_empty_collection(self, chroma_repo):
        results = await chroma_repo.search_hybrid("fastapi")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_hybrid_returns_results(self, chroma_repo, sample_doc):
        await chroma_repo.index(sample_doc, "test.md")
        results = await chroma_repo.search_hybrid("fastapi async", limit=5)
        assert len(results) >= 1
        assert results[0]["title"] == sample_doc.title
        assert 0.0 <= results[0]["score"] <= 1.0
        assert isinstance(results[0]["tags"], list)

    @pytest.mark.asyncio
    async def test_get_stats(self, chroma_repo, sample_doc):
        await chroma_repo.index(sample_doc, "test.md")
        stats = await chroma_repo.get_stats()
        assert stats["total_documents"] == 1
        assert "AI/Software Engineering" in stats["categories"]
        assert stats["categories"]["AI/Software Engineering"] == 1
        assert stats["total_tags"] >= 3
        assert stats["latest_collected_at"] is not None

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, chroma_repo):
        stats = await chroma_repo.get_stats()
        assert stats["total_documents"] == 0
        assert stats["categories"] == {}
        assert stats["total_tags"] == 0
        assert stats["latest_collected_at"] is None

    @pytest.mark.asyncio
    async def test_upsert_idempotent(self, chroma_repo, sample_doc):
        """같은 URL로 두 번 색인해도 중복되지 않아야 한다."""
        await chroma_repo.index(sample_doc, "test.md")
        await chroma_repo.index(sample_doc, "test.md")
        stats = await chroma_repo.get_stats()
        assert stats["total_documents"] == 1

    def test_keyword_score_full_match(self):
        meta = {"tags": "fastapi,python", "category": "engineering", "summary": "async python"}
        score = ChromaRepository._keyword_score("fastapi python", meta)
        assert score == 1.0

    def test_keyword_score_no_match(self):
        meta = {"tags": "java,spring", "category": "backend", "summary": "spring boot"}
        score = ChromaRepository._keyword_score("fastapi python", meta)
        assert score == 0.0

    def test_keyword_score_empty_query(self):
        meta = {"tags": "fastapi", "category": "AI", "summary": "test"}
        score = ChromaRepository._keyword_score("", meta)
        assert score == 0.0


# ------------------------------------------------------------------
# 검색 API 라우터 통합 테스트
# ------------------------------------------------------------------

class TestSearchRouter:

    @pytest.fixture()
    def app_client(self, tmp_path: Path):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from backend.routers.search import router

        mock_ef = _MockEF()
        chroma_client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))

        repo = ChromaRepository.__new__(ChromaRepository)
        repo._client = chroma_client
        repo._ef = mock_ef
        repo._collection = chroma_client.get_or_create_collection(
            name=ChromaRepository.COLLECTION_NAME,
            embedding_function=mock_ef,
            metadata={"hnsw:space": "cosine"},
        )

        async def _search(q, limit=5):
            return await repo.search_hybrid(q, limit=limit)

        async def _list_documents(category=None, tag=None, series=None, document_type=None):
            return await repo.list_documents(category=category, tag=tag, series=series, document_type=document_type)

        async def _get_stats():
            return await repo.get_stats()

        composite = MagicMock()
        composite._chroma = repo
        composite.search = AsyncMock(side_effect=_search)
        composite.list_documents = AsyncMock(side_effect=_list_documents)
        composite.get_stats = AsyncMock(side_effect=_get_stats)
        composite.get = AsyncMock(return_value=None)

        with patch("backend.storage.chroma.settings") as s:
            s.HYBRID_VECTOR_WEIGHT = 0.7

            app = FastAPI()
            app.include_router(router, prefix="/api/v1")
            app.state.composite_repo = composite
            yield TestClient(app)

    def test_search_no_params_returns_400(self, app_client):
        resp = app_client.get("/api/v1/search")
        assert resp.status_code == 400

    def test_search_empty_collection(self, app_client):
        resp = app_client.get("/api/v1/search?q=fastapi")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_documents_empty_collection(self, app_client):
        resp = app_client.get("/api/v1/documents")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_document_not_found(self, app_client):
        resp = app_client.get("/api/v1/document/없는문서")
        assert resp.status_code == 404

    def test_stats_empty(self, app_client):
        resp = app_client.get("/api/v1/search/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_documents"] == 0
        assert data["categories"] == {}
        assert data["total_tags"] == 0

    def test_search_series_only_returns_200(self, app_client):
        resp = app_client.get("/api/v1/search?series=wikidocs-300272")
        assert resp.status_code == 200

    def test_documents_series_filter_passes_param(self, app_client):
        resp = app_client.get("/api/v1/documents?series=wikidocs-300272")
        assert resp.status_code == 200
