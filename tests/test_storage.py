"""
tests/test_storage.py — 코더 B 담당 모듈 단위 테스트

대상:
    backend/storage/repository.py  (BaseRepository ABC)
    backend/storage/obsidian.py    (ObsidianRepository)
    backend/storage/composite.py   (CompositeRepository)
    backend/temp/queue_db.py       (SQLite 영속 큐)

규칙:
    - ChromaRepository는 unittest.mock으로 모킹
    - ChromaDB 실제 접속 불필요
    - queue_db는 tmp_path 기반 임시 DB 사용
"""

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.schemas.document import CollectRequest, DocumentRecord, RelatedDoc
from backend.storage.obsidian import ObsidianRepository, _sanitize_filename
from backend.storage.composite import CompositeRepository
from backend.temp import queue_db


# --- Fixtures ----------------------------------------------------------------

@pytest.fixture
def sample_doc() -> DocumentRecord:
    return DocumentRecord(
        url="https://example.com/article",
        title="FastAPI 비동기 아키텍처 설계",
        source_title="FastAPI Async Architecture",
        refined_content="FastAPI를 이용한 비동기 서버 구현 방법을 설명한다.",
        summary="FastAPI 비동기 아키텍처 설계 방법을 다룬 기술 블로그",
        tags=["fastapi", "async", "python"],
        category="AI/Software Engineering",
        related_docs=[
            RelatedDoc(
                title="Python 비동기 프로그래밍",
                reason="asyncio 기반 비동기 처리 공유",
            )
        ],
        collected_at=datetime(2026, 6, 11, 17, 0, 0),
        updated_at=datetime(2026, 6, 11, 17, 0, 0),
    )


@pytest.fixture
def obsidian_repo(tmp_path: Path) -> ObsidianRepository:
    return ObsidianRepository(vault_path=str(tmp_path))


@pytest.fixture
def mock_chroma() -> MagicMock:
    chroma = MagicMock()
    chroma.index = AsyncMock(return_value=None)
    chroma.exists_by_url = AsyncMock(return_value=False)
    chroma.search_hybrid = AsyncMock(return_value=[])
    chroma.get_metadata_by_title = AsyncMock(return_value=None)
    return chroma


@pytest.fixture
def composite_repo(tmp_path: Path, mock_chroma: MagicMock) -> CompositeRepository:
    obsidian = ObsidianRepository(vault_path=str(tmp_path))
    return CompositeRepository(obsidian=obsidian, chroma=mock_chroma)


# --- _sanitize_filename ------------------------------------------------------

def test_sanitize_removes_forbidden_chars():
    assert _sanitize_filename('A/B:C*D?E"F<G>H|I') == "ABCDEFGHI.md"


def test_sanitize_replaces_spaces_with_underscore():
    assert _sanitize_filename("Hello World") == "Hello_World.md"


def test_sanitize_appends_suffix():
    assert _sanitize_filename("Title", suffix="_20260611") == "Title_20260611.md"


def test_sanitize_truncates_at_200_chars():
    result = _sanitize_filename("A" * 300)
    assert result == "A" * 200 + ".md"


def test_sanitize_preserves_korean():
    result = _sanitize_filename("파이썬 가이드")
    assert result == "파이썬_가이드.md"


# --- ObsidianRepository.save() -----------------------------------------------

@pytest.mark.asyncio
async def test_save_creates_markdown_file(obsidian_repo, sample_doc, tmp_path):
    rel_path = await obsidian_repo.save(sample_doc)
    assert (tmp_path / rel_path).exists()


@pytest.mark.asyncio
async def test_save_returns_relative_path(obsidian_repo, sample_doc):
    rel_path = await obsidian_repo.save(sample_doc)
    assert not Path(rel_path).is_absolute()
    assert rel_path.endswith(".md")


@pytest.mark.asyncio
async def test_save_yaml_frontmatter_contains_required_fields(obsidian_repo, sample_doc, tmp_path):
    rel_path = await obsidian_repo.save(sample_doc)
    content = (tmp_path / rel_path).read_text(encoding="utf-8")

    assert 'url: "https://example.com/article"' in content
    assert 'category: "AI/Software Engineering"' in content
    assert "tags: [fastapi, async, python]" in content
    assert "summary:" in content
    assert "source_title:" in content
    assert "collected_at:" in content
    assert "updated_at:" in content


@pytest.mark.asyncio
async def test_save_h1_heading_is_doc_title(obsidian_repo, sample_doc, tmp_path):
    rel_path = await obsidian_repo.save(sample_doc)
    content = (tmp_path / rel_path).read_text(encoding="utf-8")
    assert "# FastAPI 비동기 아키텍처 설계" in content


@pytest.mark.asyncio
async def test_save_related_docs_rendered(obsidian_repo, sample_doc, tmp_path):
    rel_path = await obsidian_repo.save(sample_doc)
    content = (tmp_path / rel_path).read_text(encoding="utf-8")

    assert "### 🔗 연결된 지식 네트워크" in content
    assert "[[Python 비동기 프로그래밍]]" in content
    assert "asyncio 기반 비동기 처리 공유" in content


@pytest.mark.asyncio
async def test_save_filename_collision_adds_timestamp(obsidian_repo, sample_doc, tmp_path):
    path1 = await obsidian_repo.save(sample_doc)
    path2 = await obsidian_repo.save(sample_doc)

    assert path1 != path2
    assert (tmp_path / path1).exists()
    assert (tmp_path / path2).exists()


@pytest.mark.asyncio
async def test_save_sanitizes_special_chars_in_title(obsidian_repo, tmp_path):
    doc = DocumentRecord(
        url="https://example.com",
        title='파일: 이름/테스트 "인용"',
        source_title="Test",
        refined_content="content",
        summary="summary",
        tags=[],
        category="Test",
        related_docs=[],
        collected_at=datetime(2026, 6, 11, 17, 0, 0),
        updated_at=datetime(2026, 6, 11, 17, 0, 0),
    )
    rel_path = await obsidian_repo.save(doc)
    # 디렉토리 구분자(/)는 series 디렉토리 때문에 존재하므로 파일명만 검사
    filename = Path(rel_path).name
    assert ":" not in filename
    assert '"' not in filename


@pytest.mark.asyncio
async def test_save_no_related_docs_omits_section(obsidian_repo, tmp_path):
    doc = DocumentRecord(
        url="https://example.com/no-related",
        title="관련없는문서",
        source_title="Source",
        refined_content="본문",
        summary="요약",
        tags=["test"],
        category="Test",
        related_docs=[],
        collected_at=datetime(2026, 6, 11, 17, 0, 0),
        updated_at=datetime(2026, 6, 11, 17, 0, 0),
    )
    rel_path = await obsidian_repo.save(doc)
    content = (tmp_path / rel_path).read_text(encoding="utf-8")
    assert "### 🔗 연결된 지식 네트워크" not in content


@pytest.mark.asyncio
async def test_save_with_series_saves_to_series_subdir(obsidian_repo, tmp_path):
    """series가 있으면 {vault}/{series}/ 하위에 저장되어야 한다."""
    doc = DocumentRecord(
        url="https://wikidocs.net/100/1",
        title="C++ 입문 1챕터",
        source_title="Chapter 1",
        refined_content="본문",
        summary="요약",
        tags=["cpp"],
        category="Dev",
        related_docs=[],
        collected_at=datetime(2026, 6, 11, 17, 0, 0),
        updated_at=datetime(2026, 6, 11, 17, 0, 0),
        series="cpp-beginner-wikidocs",
    )
    rel_path = await obsidian_repo.save(doc)
    assert rel_path.startswith("cpp-beginner-wikidocs/")
    assert (tmp_path / rel_path).exists()


@pytest.mark.asyncio
async def test_save_without_series_saves_to_unsorted(obsidian_repo, sample_doc, tmp_path):
    """series가 None이면 {vault}/unsorted/ 하위에 저장되어야 한다."""
    assert sample_doc.series is None
    rel_path = await obsidian_repo.save(sample_doc)
    assert rel_path.startswith("unsorted/")
    assert (tmp_path / rel_path).exists()


@pytest.mark.asyncio
async def test_find_file_searches_subdirectories(obsidian_repo, tmp_path):
    """_find_file은 하위 디렉토리에 있는 파일도 찾아야 한다."""
    doc = DocumentRecord(
        url="https://example.com/deep",
        title="하위디렉토리문서",
        source_title="Deep",
        refined_content="본문",
        summary="요약",
        tags=[],
        category="Test",
        related_docs=[],
        collected_at=datetime(2026, 6, 11, 17, 0, 0),
        updated_at=datetime(2026, 6, 11, 17, 0, 0),
        series="my-series",
    )
    await obsidian_repo.save(doc)
    found = obsidian_repo._find_file("하위디렉토리문서")
    assert found is not None
    assert found.exists()


# --- ObsidianRepository.get() ------------------------------------------------

@pytest.mark.asyncio
async def test_get_returns_document_record(obsidian_repo, sample_doc):
    await obsidian_repo.save(sample_doc)
    result = await obsidian_repo.get(sample_doc.title)

    assert result is not None
    assert result.url == sample_doc.url
    assert result.title == sample_doc.title
    assert result.summary == sample_doc.summary
    assert result.category == sample_doc.category
    assert result.tags == sample_doc.tags


@pytest.mark.asyncio
async def test_get_reconstructs_related_docs(obsidian_repo, sample_doc):
    await obsidian_repo.save(sample_doc)
    result = await obsidian_repo.get(sample_doc.title)

    assert result is not None
    assert len(result.related_docs) == 1
    assert result.related_docs[0].title == "Python 비동기 프로그래밍"
    assert result.related_docs[0].reason == "asyncio 기반 비동기 처리 공유"


@pytest.mark.asyncio
async def test_get_returns_none_for_missing_title(obsidian_repo):
    result = await obsidian_repo.get("존재하지않는문서제목")
    assert result is None


@pytest.mark.asyncio
async def test_get_preserves_refined_content(obsidian_repo, sample_doc):
    await obsidian_repo.save(sample_doc)
    result = await obsidian_repo.get(sample_doc.title)

    assert result is not None
    assert sample_doc.refined_content in result.refined_content


@pytest.mark.asyncio
async def test_get_preserves_timestamps(obsidian_repo, sample_doc):
    await obsidian_repo.save(sample_doc)
    result = await obsidian_repo.get(sample_doc.title)

    assert result is not None
    assert result.collected_at == sample_doc.collected_at
    assert result.updated_at == sample_doc.updated_at


# --- ObsidianRepository.add_backlink() ---------------------------------------

@pytest.mark.asyncio
async def test_add_backlink_creates_section_when_none(obsidian_repo, tmp_path):
    """섹션이 없는 문서에 backlink 추가 시 섹션이 새로 생성된다."""
    doc = DocumentRecord(
        url="https://example.com/existing",
        title="기존문서",
        source_title="기존",
        refined_content="본문",
        summary="요약",
        tags=[],
        category="Test",
        related_docs=[],
        collected_at=datetime(2026, 6, 11, 17, 0, 0),
        updated_at=datetime(2026, 6, 11, 17, 0, 0),
    )
    await obsidian_repo.save(doc)

    await obsidian_repo.add_backlink(
        target_title="기존문서",
        new_title="신규문서",
        reason="연관 이유",
    )

    file_path = obsidian_repo._find_file("기존문서")
    content = file_path.read_text(encoding="utf-8")
    assert "### 🔗 연결된 지식 네트워크" in content
    assert "[[신규문서]]: 연관 이유" in content


@pytest.mark.asyncio
async def test_add_backlink_appends_to_existing_section(obsidian_repo, sample_doc):
    """섹션이 있는 문서에 backlink 추가 시 기존 항목은 유지된다."""
    await obsidian_repo.save(sample_doc)

    await obsidian_repo.add_backlink(
        target_title=sample_doc.title,
        new_title="신규문서",
        reason="연관 이유",
    )

    file_path = obsidian_repo._find_file(sample_doc.title)
    content = file_path.read_text(encoding="utf-8")
    assert "[[신규문서]]: 연관 이유" in content
    assert "[[Python 비동기 프로그래밍]]" in content


@pytest.mark.asyncio
async def test_add_backlink_skips_if_file_not_found(obsidian_repo):
    """대상 파일이 없으면 에러 없이 조용히 스킵한다."""
    await obsidian_repo.add_backlink(
        target_title="존재하지않는문서",
        new_title="신규문서",
        reason="이유",
    )


@pytest.mark.asyncio
async def test_add_backlink_no_duplicate(obsidian_repo, sample_doc):
    """동일 backlink를 두 번 추가해도 중복되지 않는다."""
    await obsidian_repo.save(sample_doc)

    await obsidian_repo.add_backlink(
        target_title=sample_doc.title,
        new_title="신규문서",
        reason="이유",
    )
    await obsidian_repo.add_backlink(
        target_title=sample_doc.title,
        new_title="신규문서",
        reason="이유",
    )

    file_path = obsidian_repo._find_file(sample_doc.title)
    content = file_path.read_text(encoding="utf-8")
    assert content.count("[[신규문서]]") == 1


# --- ObsidianRepository — NotImplementedError 메서드 ------------------------

@pytest.mark.asyncio
async def test_exists_by_url_raises_not_implemented(obsidian_repo):
    with pytest.raises(NotImplementedError):
        await obsidian_repo.exists_by_url("https://example.com")


@pytest.mark.asyncio
async def test_search_raises_not_implemented(obsidian_repo):
    with pytest.raises(NotImplementedError):
        await obsidian_repo.search("query")


# --- CompositeRepository -----------------------------------------------------

@pytest.mark.asyncio
async def test_composite_save_calls_obsidian_then_chroma(
    composite_repo, mock_chroma, sample_doc, tmp_path
):
    rel_path = await composite_repo.save(sample_doc)

    assert rel_path.endswith(".md")
    assert (tmp_path / rel_path).exists()
    mock_chroma.index.assert_called_once_with(sample_doc, rel_path)


@pytest.mark.asyncio
async def test_composite_save_does_not_index_when_obsidian_fails(mock_chroma, tmp_path):
    obsidian = MagicMock()
    obsidian.save = AsyncMock(side_effect=OSError("disk full"))
    repo = CompositeRepository(obsidian=obsidian, chroma=mock_chroma)

    doc = DocumentRecord(
        url="https://example.com",
        title="Test",
        source_title="T",
        refined_content="c",
        summary="s",
        tags=[],
        category="T",
        related_docs=[],
        collected_at=datetime(2026, 6, 11, 17, 0, 0),
        updated_at=datetime(2026, 6, 11, 17, 0, 0),
    )
    with pytest.raises(OSError):
        await repo.save(doc)

    mock_chroma.index.assert_not_called()


@pytest.mark.asyncio
async def test_composite_exists_by_url_delegates_to_chroma(composite_repo, mock_chroma):
    mock_chroma.exists_by_url.return_value = True
    result = await composite_repo.exists_by_url("https://example.com")

    assert result is True
    mock_chroma.exists_by_url.assert_called_once_with("https://example.com")


@pytest.mark.asyncio
async def test_composite_exists_by_url_never_parses_files(composite_repo, mock_chroma):
    """ChromaDB 위임 확인 — 파일 파싱 없이 chroma.exists_by_url만 호출."""
    await composite_repo.exists_by_url("https://example.com/test")
    mock_chroma.exists_by_url.assert_called_once()


@pytest.mark.asyncio
async def test_composite_search_delegates_to_chroma(composite_repo, mock_chroma):
    expected = [{"title": "Doc", "url": "https://x.com", "score": 0.9}]
    mock_chroma.search_hybrid.return_value = expected

    result = await composite_repo.search("fastapi", limit=3)

    assert result == expected
    mock_chroma.search_hybrid.assert_called_once_with("fastapi", 3)


@pytest.mark.asyncio
async def test_composite_get_delegates_to_obsidian(composite_repo, sample_doc):
    await composite_repo.save(sample_doc)
    result = await composite_repo.get(sample_doc.title)

    assert result is not None
    assert result.url == sample_doc.url


@pytest.mark.asyncio
async def test_composite_save_adds_backlinks_to_related_docs(
    composite_repo, mock_chroma, tmp_path
):
    """신규 문서 저장 시 연관 문서 파일에 backlink가 추가된다."""
    obsidian = composite_repo._obsidian

    # 연관 대상 문서를 먼저 vault에 저장
    existing_doc = DocumentRecord(
        url="https://example.com/existing",
        title="Python 비동기 프로그래밍",
        source_title="Python Async",
        refined_content="asyncio 설명",
        summary="Python 비동기 가이드",
        tags=["python", "async"],
        category="AI/Software Engineering",
        related_docs=[],
        collected_at=datetime(2026, 6, 11, 17, 0, 0),
        updated_at=datetime(2026, 6, 11, 17, 0, 0),
    )
    await obsidian.save(existing_doc)

    # 신규 문서 저장 (related_docs에 위 문서 포함)
    new_doc = DocumentRecord(
        url="https://example.com/new",
        title="FastAPI 비동기 아키텍처 설계",
        source_title="FastAPI Async",
        refined_content="FastAPI 설명",
        summary="FastAPI 가이드",
        tags=["fastapi"],
        category="AI/Software Engineering",
        related_docs=[
            RelatedDoc(title="Python 비동기 프로그래밍", reason="asyncio 공유")
        ],
        collected_at=datetime(2026, 6, 11, 18, 0, 0),
        updated_at=datetime(2026, 6, 11, 18, 0, 0),
    )
    await composite_repo.save(new_doc)

    # 기존 문서에 신규 문서 backlink가 추가됐는지 확인
    file_path = obsidian._find_file("Python 비동기 프로그래밍")
    content = file_path.read_text(encoding="utf-8")
    assert "[[FastAPI 비동기 아키텍처 설계]]" in content
    assert "asyncio 공유" in content


@pytest.mark.asyncio
async def test_composite_save_skips_missing_related_doc(composite_repo, mock_chroma):
    """연관 문서 파일이 없어도 에러 없이 저장이 완료된다."""
    new_doc = DocumentRecord(
        url="https://example.com/new",
        title="신규문서",
        source_title="New",
        refined_content="내용",
        summary="요약",
        tags=[],
        category="Test",
        related_docs=[RelatedDoc(title="존재하지않는문서", reason="이유")],
        collected_at=datetime(2026, 6, 11, 17, 0, 0),
        updated_at=datetime(2026, 6, 11, 17, 0, 0),
    )
    rel_path = await composite_repo.save(new_doc)
    assert rel_path.endswith(".md")


# --- queue_db ----------------------------------------------------------------

@pytest.fixture
def override_db(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "failed_tasks.db"
    monkeypatch.setattr(queue_db, "DB_PATH", db_path)
    return db_path


@pytest.mark.asyncio
async def test_init_creates_db_file(override_db):
    await queue_db.init_queue_db()
    assert override_db.exists()


@pytest.mark.asyncio
async def test_save_failed_stores_pending_task(override_db):
    await queue_db.init_queue_db()
    request = {
        "url": "https://example.com",
        "title": "Test Article",
        "content": "Article content",
        "timestamp": "2026-06-11T17:00:00",
    }
    await queue_db.save_failed("uuid-001", request)

    pending = await queue_db.get_pending()
    assert len(pending) == 1
    assert pending[0]["id"] == "uuid-001"
    assert pending[0]["status"] == "pending"
    assert pending[0]["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_save_failed_ignores_duplicate_id(override_db):
    await queue_db.init_queue_db()
    request = {
        "url": "https://example.com",
        "title": "T",
        "content": "C",
        "timestamp": "2026-06-11T17:00:00",
    }
    await queue_db.save_failed("uuid-dup", request)
    await queue_db.save_failed("uuid-dup", request)

    pending = await queue_db.get_pending()
    assert len(pending) == 1


@pytest.mark.asyncio
async def test_update_status_removes_from_pending(override_db):
    await queue_db.init_queue_db()
    request = {
        "url": "https://example.com",
        "title": "T",
        "content": "C",
        "timestamp": "2026-06-11T17:00:00",
    }
    await queue_db.save_failed("uuid-002", request)
    await queue_db.update_status("uuid-002", "retrying")

    pending = await queue_db.get_pending()
    assert all(t["id"] != "uuid-002" for t in pending)


@pytest.mark.asyncio
async def test_increment_retry_returns_incremented_count(override_db):
    await queue_db.init_queue_db()
    request = {
        "url": "https://example.com",
        "title": "T",
        "content": "C",
        "timestamp": "2026-06-11T17:00:00",
    }
    await queue_db.save_failed("uuid-003", request)

    count1 = await queue_db.increment_retry("uuid-003")
    count2 = await queue_db.increment_retry("uuid-003")

    assert count1 == 1
    assert count2 == 2


@pytest.mark.asyncio
async def test_get_pending_respects_limit(override_db):
    await queue_db.init_queue_db()
    for i in range(5):
        await queue_db.save_failed(f"uuid-{i:03d}", {
            "url": f"https://example.com/{i}",
            "title": f"Article {i}",
            "content": "Content",
            "timestamp": "2026-06-11T17:00:00",
        })

    result = await queue_db.get_pending(limit=3)
    assert len(result) == 3


@pytest.mark.asyncio
async def test_reload_failed_tasks_enqueues_collect_requests(override_db):
    await queue_db.init_queue_db()
    await queue_db.save_failed("uuid-004", {
        "url": "https://example.com/reload",
        "title": "Reload Test",
        "content": "Content",
        "timestamp": "2026-06-11T17:00:00",
    })

    q: asyncio.Queue = asyncio.Queue()
    await queue_db.reload_failed_tasks(q)

    assert not q.empty()
    item = await q.get()
    assert isinstance(item, CollectRequest)
    assert item.url == "https://example.com/reload"


@pytest.mark.asyncio
async def test_reload_failed_tasks_empty_when_no_pending(override_db):
    await queue_db.init_queue_db()
    q: asyncio.Queue = asyncio.Queue()
    await queue_db.reload_failed_tasks(q)
    assert q.empty()
