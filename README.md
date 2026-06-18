# Learning Assistant System

> 웹 서핑 중 지나친 페이지까지 자동 수집·분석하여 로컬 지식 그래프를 구축하고,  
> Claude Desktop에서 자연어로 "저번에 이거 본 적 있어?" 라고 물어볼 수 있는 개인 지식 에이전트 및 문서간 하이퍼링크를 통한 llm wiki

**🎬 [Demo Video](https://www.youtube.com/watch?v=HGjfcvkgZx0)** · **📄 [Architecture Spec](./SPEC.md)**

---

## Highlights

| 항목 | 내용 |
|------|------|
|  Hybrid AI | 로컬 LLM(Ollama) 1차 필터링 → 상용 API 호출 비용 절감 |
|  Multi-Provider Fallback | xAI → Groq → Gemini → Claude 자동 전환, 429 즉시 Fallback |
|  MCP Integration | Claude Desktop에서 자연어로 수집된 문서 검색·대화 |
| ️ Local-First | 원시 데이터·지식 그래프 모두 로컬 저장. 외부 서버 전송 없음 |
|  Test Coverage | 124 passed, 0 failed (pytest) |
|  SLA | 수집 API P99 \<100ms · MCP 검색 \<2s · 성공률 \>95% |

---

## Architecture
다크모드 사용 시 흐릿하게 보일 수 있음
![Architecture](https://github.com/user-attachments/assets/43da1a74-bdfa-4a02-9f72-addbcd0d7291)

---

## System Flow

```
[Browser]  →  POST /api/v1/collect
               ↓ asyncio.Queue (즉시 200 OK 반환)
[Worker-1] →  Ollama llama3:8b  →  이진 분류 (지식 문서 여부)
               ↓ True만 통과 / 실패 시 SQLite(.temp/) 영속화
[Worker-2] →  LLM Orchestrator  →  요약·태깅·연관 분석
               ↓
[CompositeRepository]  →  Obsidian .md 저장 + ChromaDB 색인

[Claude Desktop]  →  MCP Tool 호출
                      ↓ search_vault / get_document / get_stats
[FastAPI Search]  →  Hybrid Search (Vector×0.7 + Keyword×0.3)
                      ↓
[Claude Desktop]  →  수집 문서 기반 답변 생성
```

---

## Tech Stack

| Layer | Stack |
|-------|-------|
| Backend | Python 3.11 · FastAPI · uvicorn · asyncio · pydantic-settings |
| Local LLM | Ollama · llama3:8b / phi3:mini |
| Cloud LLM | xAI Grok-3 · Groq Llama-3.3 · Gemini 2.0 Flash · Claude 3.5 Sonnet |
| Vector DB | ChromaDB (Persistent) · all-MiniLM-L6-v2 (로컬 임베딩) |
| Storage | Obsidian Vault (.md) · SQLite (aiosqlite) |
| Extension | Chrome MV3 · Readability.js |
| MCP | Python mcp SDK · stdio transport |
| Dev | pytest · pytest-asyncio · PyInstaller (System Tray) |

---

## Quick Start

```bash
# 1. Ollama 설치
# https://ollama.com/download

# 2. 환경 초기화 (패키지 설치 + 모델 다운로드 + .env 생성)
python scripts/setup.py

# 3. API 키 입력
# .env 파일에서 사용할 LLM 키 설정
LLM_PRIORITY=xai,gemini,groq,claude

# 4. 서버 실행
uvicorn backend.main:app --reload
# 또는 dist/Learning.exe → 트레이 우클릭 → 서버 시작

# 5. Chrome Extension
# chrome://extensions/ → 개발자 모드 ON → extension/ 폴더 로드
```

### API Keys (.env)

```env
ANTHROPIC_API_KEY=sk-ant-...
XAI_API_KEY=xai-...
GEMINI_API_KEY=AIza...
GROQ_API_KEY=gsk_...
LLM_PRIORITY=xai,gemini,groq,claude
```

### Claude Desktop MCP 연결

```json
// ~/AppData/Local/Packages/Claude_.../LocalCache/Roaming/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "Learning": {
      "command": "C:\\...\\python.exe",
      "args": ["C:\\...\\Learning-assistant\\mcp_server\\server.py"],
      "env": { "KALF_API_URL": "http://localhost:8000" }
    }
  }
}
```

---

## Project Structure

```
root/
├── backend/
│   ├── llm/          # LLM Factory (xAI / Groq / Gemini / Claude)
│   ├── routers/      # collect · search API
│   ├── storage/      # CompositeRepository · ObsidianRepo · ChromaRepo
│   ├── temp/         # SQLite 영속 큐 (failed_tasks.db)
│   ├── utils/        # series_detector · paper_detector
│   └── workers/      # classifier (Ollama) · analyzer (LLM)
├── extension/        # Chrome Extension MV3
├── mcp_server/       # Claude Desktop MCP 서버
├── scripts/
│   ├── setup.py          # 초기화
│   ├── index_vault.py    # 기존 볼트 일괄 색인
│   └── migrate_series.py # 시리즈별 디렉토리 재구성
├── tests/            # 124 passed
├── tray/             # Windows System Tray App
└── obsidian_vault/   # 수집된 Markdown 파일
```

---

## Scripts

```bash
# 기존 볼트 ChromaDB 색인
python scripts/index_vault.py

# 시리즈별 디렉토리 재구성
python scripts/migrate_series.py

# 테스트
pytest tests/ -v

# 트레이 앱 빌드
tray\build.bat   # → dist\Learning.exe
```
