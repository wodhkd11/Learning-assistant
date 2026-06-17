# 모듈 G — MCP 서버 (Claude Desktop 연동)

**담당 코더:** 코더 D
**브랜치:** `feat/module-F-G`
**담당 파일:** `mcp_server/server.py`

---

## 목표

Claude Desktop이 Obsidian 볼트를 자율적으로 검색·조회할 수 있도록 MCP(Model Context Protocol) 서버를 구현하여 자연어 기반 지식 대화를 가능하게 한다.

---

## 세부 요구사항

- Python `mcp` SDK (`pip install mcp`) 사용하여 **stdio transport** 방식 MCP 서버 구현
- FastAPI 백엔드 HTTP 엔드포인트를 내부 `httpx` 호출로 위임 (검색 로직 재사용)
- Claude Desktop `claude_desktop_config.json`에 등록하여 앱 실행 시 자동 로드
- 모든 Tool의 파라미터는 **JSON Schema로 명시** (Claude Desktop 인식 필수)
- FastAPI 백엔드(포트 8000)가 먼저 실행되어 있어야 정상 동작
- 백엔드 미가동 시 명확한 오류 메시지 반환

---

## MCP Tool 인터페이스

`docs/interfaces.md` 섹션 5 참고.

| Tool 이름 | 파라미터 | 설명 |
|-----------|---------|------|
| `search_vault` | `query: str`, `limit: int = 5` | 자연어/키워드 검색 |
| `get_document` | `title: str` | 특정 문서 전문 조회 |
| `list_documents` | `category?: str`, `tag?: str` | 전체 문서 목록 |
| `get_related` | `title: str` | 연관 문서([[링크]]) 목록 |
| `get_stats` | 없음 | 볼트 통계 |

---

## Claude Desktop 설정 예시

```json
// macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
// Windows: %APPDATA%\Claude\claude_desktop_config.json
{
  "mcpServers": {
    "kalf": {
      "command": "python",
      "args": ["/절대경로/kalf/mcp_server/server.py"],
      "env": {
        "KALF_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

---

## 구현 스켈레톤

```python
# mcp_server/server.py
import asyncio
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

KALF_API_URL = os.environ.get("KALF_API_URL", "http://localhost:8000")

server = Server("kalf")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_vault",
            description="볼트 내 문서를 자연어 또는 키워드로 검색합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색 질의"},
                    "limit": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        ),
        # ... 나머지 Tool 정의
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    async with httpx.AsyncClient() as client:
        if name == "search_vault":
            resp = await client.get(
                f"{KALF_API_URL}/api/v1/search",
                params={"q": arguments["query"], "limit": arguments.get("limit", 5)}
            )
            return [types.TextContent(type="text", text=resp.text)]
        # ... 나머지 Tool 구현

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 주의사항

- `stdio transport`는 Claude Desktop이 subprocess로 직접 실행. **별도로 서버를 실행하지 않는다.**
- MCP 서버 프로세스와 FastAPI 서버는 완전히 별개의 프로세스다.
- FastAPI가 먼저 `uvicorn backend.main:app` 으로 실행되어 있어야 MCP Tool이 정상 동작한다.
- 에러 응답도 `types.TextContent`로 래핑하여 Claude Desktop이 읽을 수 있게 반환한다.
