# KALF — Knowledge-Agent-Local-First
## 시스템 아키텍처 및 모듈 요구사항 명세서 (v2.1 Final)

> **모든 Claude Code 인스턴스는 작업 시작 전 반드시 이 파일과 `docs/interfaces.md`, `CLAUDE.md`를 순서대로 읽어야 한다.**

---

## 1. 프로젝트 개요

### 1.1 최종 목표

사용자가 웹 서핑 중 무심코 넘긴 페이지까지 포함해 방문한 모든 지식 콘텐츠를 자동으로 선별·요약하여 로컬 Obsidian 볼트에 저장하고, 이후 Claude Desktop을 통해 "저번에 이거 본 적 있어?" 와 같은 자연어 질의로 과거 수집 자료를 즉시 검색·대화할 수 있는 개인 지식 에이전트를 구축한다.

### 1.2 핵심 설계 원칙

| 원칙 | 설명 |
|------|------|
| **Local-First & Privacy** | 원시 수집 데이터와 최종 지식 그래프는 로컬 머신에만 저장. 문서 요약·관계 분석 단계에서만 상용 LLM API와 암호화 통신 수행. 원문 데이터 자체는 외부로 전송하지 않음. |
| **Hybrid AI Cost Efficiency** | 로컬 LLM(Ollama)으로 1차 필터링 후 가치 있는 문서만 상용 API(Claude/Gemini)로 심층 분석 |
| **Asynchronous & UX-First** | 브라우징 경험 방해 없이 모든 AI 연산을 `asyncio.Queue` 기반 비동기 파이프라인으로 완전 분리 |
| **Retrieval-Augmented Conversation** | 저장된 지식을 MCP 서버를 통해 Claude Desktop에서 자연어로 검색·대화 가능 |
| **단일 책임 저장소 계층** | ChromaDB 색인과 파일 저장은 `CompositeRepository`가 단일하게 책임. 상위 모듈(D)은 분석 결과만 생성 |

---

## 2. 전체 시스템 플로우

### 2.1 수집 파이프라인 (Ingestion Pipeline)

```
[브라우저] chrome.webNavigation.onCompleted
    ↓ POST /api/v1/collect  {url, title, content, timestamp}
[FastAPI Router] 즉시 200 OK 반환
    ↓ await ingestion_queue.put(request)  ← asyncio.Queue 단일 진입점
[Worker-1] Ollama API 호출 → 이진 분류 (지식 문서 여부)
    ↓ False → 폐기 / Ollama 장애 → .temp/failed_tasks.db 저장
    ↓ True 판정 시만
[Worker-2] 상용 LLM API (Claude/Gemini Factory)
    → ChromaDB metadata 쿼리로 연관 후보 추출 (파일 직접 파싱 없음)
    → AnalysisResult 생성 (요약·태깅·연관 관계)
    ↓
[CompositeRepository.save()]
    → ObsidianRepository: .md 파일 저장 → obsidian_vault/
    → ChromaRepository: 임베딩 + metadata 색인 (단일 책임)
```

### 2.2 조회 파이프라인 (Retrieval Pipeline)

```
[Claude Desktop] 자연어 질의
    ↓ MCP Tool 호출 (stdio transport)
[MCP Server] search_vault / get_document / list_documents 등
    ↓ HTTP → FastAPI
[Hybrid Search] ChromaDB vector 유사도 (0.7) + metadata where 절 필터 (0.3)
    ↓ 파일 시스템 직접 파싱 없음 — ChromaDB 단일 쿼리
[FastAPI] SearchResult 반환 → Claude Desktop 컨텍스트 주입
    ↓
[Claude Desktop] 수집 문서 기반 답변 생성
```

---

## 3. 모듈 구성 요약

| 모듈 | 역할 | 담당 파일 |
|------|------|-----------|
| A | Browser Extension (수집기) | `extension/` |
| B | FastAPI Backend Core (라우팅·큐 관리) | `backend/main.py`, `backend/routers/` |
| C | Local LLM Worker (Ollama 분류기) | `backend/workers/classifier.py` |
| D | Advanced LLM Worker (오케스트레이터) | `backend/workers/analyzer.py` |
| E | Obsidian Vault I/O | `backend/storage/obsidian.py` |
| F | Hybrid Search Engine | `backend/storage/chroma.py`, `backend/routers/search.py` |
| G | MCP Server (Claude Desktop 연동) | `mcp_server/server.py` |
| X | CompositeRepository (저장소 단일화) | `backend/storage/composite.py` |

세부 요구사항은 각 `docs/module_*.md` 파일 참고.

---

## 4. 기술 스택

| 레이어 | 기술 |
|--------|------|
| 브라우저 확장 | Chrome Extension MV3, Mozilla Readability.js |
| 백엔드 | Python 3.11+, FastAPI, uvicorn, pydantic-settings |
| 로컬 LLM | Ollama (llama3:8b 권장, phi3:mini fallback) |
| 상용 LLM | Anthropic Claude 3.5 Sonnet, Google Gemini 1.5 Pro |
| 벡터 DB | ChromaDB (persistent mode) |
| 임베딩 | sentence-transformers/all-MiniLM-L6-v2 (로컬) |
| 영속 큐 | SQLite (aiosqlite) — `.temp/failed_tasks.db` |
| MCP | mcp SDK (stdio transport) |
| 저장소 | 로컬 파일 시스템 (`obsidian_vault/`) |
| 로깅 | structlog |
| 설정 | pydantic-settings, python-dotenv |
| 테스트 | pytest, pytest-asyncio, httpx |

---

## 5. SLA 목표

| 지표 | 목표 |
|------|------|
| 수집 API 응답 latency (P99) | < 100ms |
| 로컬 LLM 분류 처리 시간 | < 10초/문서 |
| 상용 LLM 분석 처리 시간 | < 30초/문서 |
| MCP 검색 응답 시간 | < 2초 |
| 수집 파이프라인 성공률 | > 95% (SQLite 영속 큐 포함) |
| ChromaDB 색인 동기화 | 문서 저장과 동시 (CompositeRepository 보장) |

---

## 6. 개발 단계

| Phase | 내용 | 완료 기준 |
|-------|------|-----------|
| 1 (기반) | FastAPI 골격 + 파일 저장 + CompositeRepository | POST /collect → obsidian_vault/ 저장 동작 |
| 2 (영속 큐) | .temp/ + failed_tasks.db SQLite 큐 | 서버 재시작 시 미처리 작업 자동 복구 |
| 3 (수집) | Extension + Ollama 분류기 | 브라우저 방문 시 자동 수집·분류 |
| 4 (분석) | LLM Factory + 연관 분석 | [[링크]] 자동 생성 |
| 5 (검색) | ChromaDB 하이브리드 검색 | /search API 동작 |
| 6 (대화) | MCP 서버 + Claude Desktop 연동 | 자연어 질의 동작 |
| 7 (운영) | Fallback 안정화 + E2E 테스트 | 전체 파이프라인 통합 테스트 통과 |
