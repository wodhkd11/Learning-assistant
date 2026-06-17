"""tests/test_mcp.py — MCP 서버 단위 테스트.

_dispatch() 함수를 직접 호출하여 MCP SDK 내부에 의존하지 않고 테스트한다.
httpx 호출은 _api_get mock으로 대체.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ------------------------------------------------------------------
# _dispatch 단위 테스트
# ------------------------------------------------------------------

class TestDispatch:

    @pytest.mark.asyncio
    async def test_search_vault(self):
        expected = [{"title": "FastAPI", "score": 0.9}]
        with patch("mcp_server.server._api_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = expected
            from mcp_server.server import _dispatch

            result = await _dispatch("search_vault", {"query": "fastapi", "limit": 3})

        mock_get.assert_called_once_with(
            "/api/v1/search",
            params={"q": "fastapi", "limit": 3},
        )
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_document(self):
        mock_doc = {"title": "FastAPI", "refined_content": "내용", "tags": ["fastapi"]}
        with patch("mcp_server.server._api_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_doc
            from mcp_server.server import _dispatch

            result = await _dispatch("get_document", {"title": "FastAPI"})

        mock_get.assert_called_once_with("/api/v1/document/FastAPI")
        assert result["title"] == "FastAPI"

    @pytest.mark.asyncio
    async def test_list_documents_with_filters(self):
        with patch("mcp_server.server._api_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            from mcp_server.server import _dispatch

            await _dispatch("list_documents", {"category": "AI", "tag": "python"})

        mock_get.assert_called_once_with(
            "/api/v1/documents",
            params={"category": "AI", "tag": "python"},
        )

    @pytest.mark.asyncio
    async def test_list_documents_no_filters(self):
        with patch("mcp_server.server._api_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            from mcp_server.server import _dispatch

            await _dispatch("list_documents", {})

        mock_get.assert_called_once_with("/api/v1/documents", params=None)

    @pytest.mark.asyncio
    async def test_get_related_success(self):
        mock_doc = {
            "title": "FastAPI",
            "related_docs": [
                {"title": "Starlette", "reason": "기반 프레임워크"},
                {"title": "Uvicorn", "reason": "ASGI 서버"},
            ],
        }
        with patch("mcp_server.server._api_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_doc
            from mcp_server.server import _dispatch

            result = await _dispatch("get_related", {"title": "FastAPI"})

        assert len(result) == 2
        assert result[0]["title"] == "Starlette"

    @pytest.mark.asyncio
    async def test_get_related_api_error(self):
        with patch("mcp_server.server._api_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"error": "404 Not Found"}
            from mcp_server.server import _dispatch

            result = await _dispatch("get_related", {"title": "없는문서"})

        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_related_no_related_docs(self):
        with patch("mcp_server.server._api_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"title": "FastAPI"}
            from mcp_server.server import _dispatch

            result = await _dispatch("get_related", {"title": "FastAPI"})

        assert result == []

    @pytest.mark.asyncio
    async def test_get_stats(self):
        mock_stats = {
            "total_documents": 42,
            "categories": {"AI": 20, "Engineering": 22},
            "latest_collected_at": "2024-06-01T12:00:00",
            "total_tags": 15,
        }
        with patch("mcp_server.server._api_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_stats
            from mcp_server.server import _dispatch

            result = await _dispatch("get_stats", {})

        mock_get.assert_called_once_with("/api/v1/search/stats")
        assert result["total_documents"] == 42

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        from mcp_server.server import _dispatch

        result = await _dispatch("nonexistent_tool", {})
        assert "error" in result
        assert "nonexistent_tool" in result["error"]


# ------------------------------------------------------------------
# call_tool 반환 형식 테스트
# ------------------------------------------------------------------

class TestCallToolOutput:

    @pytest.mark.asyncio
    async def test_output_is_text_content(self):
        with patch("mcp_server.server._api_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"total_documents": 5}
            from mcp_server.server import call_tool

            result = await call_tool("get_stats", {})

        assert len(result) == 1
        assert result[0].type == "text"
        parsed = json.loads(result[0].text)
        assert parsed["total_documents"] == 5

    @pytest.mark.asyncio
    async def test_error_response_is_text_content(self):
        """백엔드 오류도 TextContent로 래핑되어야 한다."""
        with patch("mcp_server.server._api_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"error": "연결 실패"}
            from mcp_server.server import call_tool

            result = await call_tool("get_stats", {})

        assert result[0].type == "text"
        parsed = json.loads(result[0].text)
        assert "error" in parsed


# ------------------------------------------------------------------
# _api_get 연결 오류 처리 테스트
# ------------------------------------------------------------------

class TestApiGet:

    @pytest.mark.asyncio
    async def test_connect_error_returns_error_dict(self):
        import httpx

        with patch("httpx.AsyncClient") as mock_cls:
            mock_instance = mock_cls.return_value.__aenter__.return_value
            mock_instance.get = AsyncMock(side_effect=httpx.ConnectError("refused"))

            from mcp_server.server import _api_get

            result = await _api_get("/api/v1/search/stats")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_http_status_error_returns_error_dict(self):
        import httpx

        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        with patch("httpx.AsyncClient") as mock_cls:
            mock_instance = mock_cls.return_value.__aenter__.return_value
            mock_instance.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "404", request=mock_request, response=mock_response
                )
            )

            from mcp_server.server import _api_get

            result = await _api_get("/api/v1/document/없는문서")

        assert "error" in result
