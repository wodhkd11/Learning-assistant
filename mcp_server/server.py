"""MCP 서버 — Claude Desktop과 KALF 볼트를 연결한다.

stdio transport로 실행: Claude Desktop이 subprocess로 직접 기동.
FastAPI 백엔드(포트 8000)가 먼저 실행되어 있어야 정상 동작한다.
"""

import asyncio
import json
import os
from typing import Any

import httpx
import structlog
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

log = structlog.get_logger()

KALF_API_URL = os.environ.get("KALF_API_URL", "http://localhost:8000")

server = Server("kalf")


# ------------------------------------------------------------------
# HTTP 위임 헬퍼
# ------------------------------------------------------------------

async def _api_get(path: str, params: dict | None = None) -> Any:
    """FastAPI 엔드포인트에 GET 요청을 보내고 JSON을 반환한다."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{KALF_API_URL}{path}", params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.ConnectError:
            return {
                "error": (
                    f"FastAPI 백엔드({KALF_API_URL})에 연결할 수 없습니다. "
                    "uvicorn backend.main:app 으로 서버를 먼저 실행하세요."
                )
            }
        except httpx.HTTPStatusError as exc:
            return {"error": f"HTTP {exc.response.status_code}: {exc.response.text}"}
        except Exception as exc:
            return {"error": str(exc)}


def _safe_json(data: Any) -> str:
    def _default(obj: Any) -> Any:
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        return str(obj)
    return json.dumps(data, ensure_ascii=False, indent=2, default=_default)


def _json_text(data: Any) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=_safe_json(data))]


# ------------------------------------------------------------------
# Tool 로직 (테스트 가능하도록 분리)
# ------------------------------------------------------------------

async def _dispatch(name: str, arguments: dict) -> Any:
    if name == "search_vault":
        params: dict = {"q": arguments["query"], "limit": arguments.get("limit", 5)}
        if "series" in arguments:
            params["series"] = arguments["series"]
        if "document_type" in arguments:
            params["type"] = arguments["document_type"]
        return await _api_get("/api/v1/search", params=params)

    if name == "get_document":
        return await _api_get(f"/api/v1/document/{arguments['title']}")

    if name == "list_documents":
        params = {}
        if "category" in arguments:
            params["category"] = arguments["category"]
        if "tag" in arguments:
            params["tag"] = arguments["tag"]
        if "series" in arguments:
            params["series"] = arguments["series"]
        if "document_type" in arguments:
            params["document_type"] = arguments["document_type"]
        return await _api_get("/api/v1/documents", params=params or None)

    if name == "get_related":
        doc = await _api_get(f"/api/v1/document/{arguments['title']}")
        if isinstance(doc, dict) and "error" in doc:
            return doc
        if isinstance(doc, dict):
            return doc.get("related_docs", [])
        return []

    if name == "get_stats":
        return await _api_get("/api/v1/search/stats")

    return {"error": f"알 수 없는 도구: {name}"}


# ------------------------------------------------------------------
# MCP Tool 등록
# ------------------------------------------------------------------

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_vault",
            description="볼트 내 문서를 자연어 또는 키워드로 검색합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색 질의 (자연어 또는 키워드)"},
                    "limit": {"type": "integer", "default": 5, "description": "최대 결과 수"},
                    "series": {"type": "string", "description": "시리즈 ID로 범위 제한 (예: wikidocs-300272)"},
                    "document_type": {"type": "string", "description": "문서 유형 필터 (paper/tutorial/blog/wiki/docs/news/other)"},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_document",
            description="제목으로 특정 문서의 전문을 조회합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "문서 제목"},
                },
                "required": ["title"],
            },
        ),
        types.Tool(
            name="list_documents",
            description="카테고리, 태그 또는 시리즈 기반으로 문서 목록을 조회합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "필터할 카테고리"},
                    "tag": {"type": "string", "description": "필터할 태그"},
                    "series": {"type": "string", "description": "시리즈 ID로 필터 (예: wikidocs-300272)"},
                    "document_type": {"type": "string", "description": "문서 유형 필터 (paper/tutorial/blog/wiki/docs/news/other)"},
                },
            },
        ),
        types.Tool(
            name="get_related",
            description="특정 문서의 연관 문서([[링크]]) 목록을 반환합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "문서 제목"},
                },
                "required": ["title"],
            },
        ),
        types.Tool(
            name="get_stats",
            description="볼트 전체 통계(총 문서 수, 카테고리별 분포, 태그 수)를 반환합니다.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    log.info("mcp.tool_called", tool=name)
    data = await _dispatch(name, arguments)
    return _json_text(data)


# ------------------------------------------------------------------
# 진입점
# ------------------------------------------------------------------

async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
