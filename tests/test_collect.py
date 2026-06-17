"""
tests/test_collect.py -- POST /api/v1/collect 엔드포인트 단위 테스트

실행: pytest tests/test_collect.py -v
"""
import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.schemas.document import CollectRequest


# ---------------------------------------------------------------------------
# 공통 fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_payload():
    return {
        "url": "https://example.com/article",
        "title": "FastAPI 비동기 처리 완전 이해",
        "content": "FastAPI는 Starlette 기반의 비동기 웹 프레임워크다. " * 20,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture()
def mock_app_state():
    """lifespan 없이 app.state를 직접 주입하는 mock."""
    state = SimpleNamespace(
        ingestion_queue=asyncio.Queue(),
        analysis_queue=asyncio.Queue(),
        composite_repo=AsyncMock(),
    )
    state.composite_repo.exists_by_url = AsyncMock(return_value=False)
    return state


@pytest.fixture()
def client_with_state(mock_app_state):
    """lifespan을 건너뛰고 mock state를 주입한 테스트 클라이언트."""
    app.state.ingestion_queue = mock_app_state.ingestion_queue
    app.state.analysis_queue = mock_app_state.analysis_queue
    app.state.composite_repo = mock_app_state.composite_repo
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# 1. 정상 수집 -- queued 응답
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_queued(client_with_state, sample_payload, mock_app_state):
    async with client_with_state as client:
        resp = await client.post("/api/v1/collect", json=sample_payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "queued"
    assert uuid.UUID(body["id"])  # 유효한 UUID
    assert mock_app_state.ingestion_queue.qsize() == 1


# ---------------------------------------------------------------------------
# 2. 블랙리스트 도메인 -- blacklisted 응답
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("url", [
    "https://www.google.com/search?q=test",
    "https://youtube.com/watch?v=abc",
    "https://naver.com/main",
    "https://x.com/user/status/123",
    "http://localhost:3000/page",
])
async def test_collect_blacklisted(client_with_state, url, mock_app_state):
    payload = {
        "url": url,
        "title": "블랙리스트 페이지",
        "content": "내용 없음",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    async with client_with_state as client:
        resp = await client.post("/api/v1/collect", json=payload)

    assert resp.status_code == 200
    assert resp.json()["status"] == "blacklisted"
    assert mock_app_state.ingestion_queue.qsize() == 0


# ---------------------------------------------------------------------------
# 3. 중복 URL -- duplicate 응답
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_duplicate(client_with_state, sample_payload, mock_app_state):
    mock_app_state.composite_repo.exists_by_url = AsyncMock(return_value=True)

    async with client_with_state as client:
        resp = await client.post("/api/v1/collect", json=sample_payload)

    assert resp.status_code == 200
    assert resp.json()["status"] == "duplicate"
    assert mock_app_state.ingestion_queue.qsize() == 0


# ---------------------------------------------------------------------------
# 4. 요청 스키마 검증 -- 필수 필드 누락
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_missing_field(client_with_state):
    incomplete = {"url": "https://example.com/article"}
    async with client_with_state as client:
        resp = await client.post("/api/v1/collect", json=incomplete)

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 5. 요청 스키마 검증 -- timestamp 형식 오류
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_collect_invalid_timestamp(client_with_state):
    payload = {
        "url": "https://example.com/article",
        "title": "테스트",
        "content": "내용",
        "timestamp": "not-a-date",
    }
    async with client_with_state as client:
        resp = await client.post("/api/v1/collect", json=payload)

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 6. 헬스체크
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health(client_with_state):
    async with client_with_state as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# 7. domain extractor 유닛 테스트
# ---------------------------------------------------------------------------

def test_extract_domain_strips_www():
    from backend.routers.collect import _extract_domain
    assert _extract_domain("https://www.example.com/page") == "example.com"
    assert _extract_domain("https://example.com/page") == "example.com"
    assert _extract_domain("https://sub.example.com/page") == "sub.example.com"
    assert _extract_domain("not-a-url") == ""


# ---------------------------------------------------------------------------
# 8. CollectRequest 스키마 단위 테스트
# ---------------------------------------------------------------------------

def test_collect_request_schema():
    req = CollectRequest(
        url="https://example.com",
        title="테스트",
        content="본문 내용",
        timestamp=datetime.now(timezone.utc),
    )
    assert req.url == "https://example.com"
    assert isinstance(req.timestamp, datetime)


# ---------------------------------------------------------------------------
# 9. worker_1_loop -- OllamaUnavailableError 시 영속화
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_worker1_saves_on_ollama_unavailable():
    from backend.exceptions import OllamaUnavailableError
    from backend.workers.queue_manager import worker_1_loop

    state = SimpleNamespace(
        ingestion_queue=asyncio.Queue(),
        analysis_queue=asyncio.Queue(),
    )
    request = CollectRequest(
        url="https://example.com",
        title="Test",
        content="content",
        timestamp=datetime.now(timezone.utc),
    )
    await state.ingestion_queue.put(request)

    import sys
    mock_classifier_mod = MagicMock()
    mock_classifier_mod.classify = AsyncMock(side_effect=OllamaUnavailableError)
    with patch("backend.workers.queue_manager.save_failed", new_callable=AsyncMock) as mock_save, \
         patch.dict(sys.modules, {"backend.workers.classifier": mock_classifier_mod}):
        task = asyncio.create_task(worker_1_loop(state))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    mock_save.assert_called_once()


# ---------------------------------------------------------------------------
# 10. check_ollama_connection 단위 테스트
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_ollama_connection_ok():
    from backend.workers.queue_manager import check_ollama_connection

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.get = AsyncMock(return_value=mock_resp)
        result = await check_ollama_connection()

    assert result is True


@pytest.mark.asyncio
async def test_check_ollama_connection_fail():
    from backend.workers.queue_manager import check_ollama_connection

    with patch("httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.get = AsyncMock(side_effect=Exception("connection refused"))
        result = await check_ollama_connection()

    assert result is False
