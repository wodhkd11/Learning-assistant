# 모듈 B — 가용성 및 라우팅 계층 (FastAPI Backend Core)

**담당 코더:** 코더 A
**브랜치:** `feat/module-A-B`
**담당 파일:** `backend/main.py`, `backend/config.py`, `backend/routers/collect.py`, `backend/workers/queue_manager.py`

---

## 목표

대량 트래픽 진입 시 가용성을 유지하고 `asyncio.Queue` 기반 비동기 워커 파이프라인을 조율하는 컨트롤 타워 역할.

---

## 세부 요구사항

- FastAPI 라우터에서 요청 수신 즉시 `await ingestion_queue.put(request)` 후 200 OK 반환. **`BackgroundTasks` 미사용.**
- `asyncio.Queue` 단일 진입점으로 Worker-1(로컬 LLM), Worker-2(상용 LLM) 작업 순차 분리
- 요청 수신 즉시 200 OK 반환 (SLA 목표: 응답 latency < 100ms)
- 구조화된 로깅(JSON 포맷, structlog)으로 `request_id`별 전체 파이프라인 추적
- `FastAPI lifespan` 이벤트로 startup 순서 제어 (아래 Startup 순서 참고)
- `pydantic-settings`로 환경변수 관리

---

## Startup 순서 (lifespan 이벤트)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. .temp/ 디렉토리 초기화
    Path(settings.TEMP_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.TEMP_DIR + '/raw_cache').mkdir(exist_ok=True)

    # 2. SQLite failed_tasks.db 초기화 (테이블 생성)
    await init_queue_db()

    # 3. ChromaDB PersistentClient 초기화 + 컬렉션 생성
    init_chroma()

    # 4. Obsidian 볼트 경로 확인/생성
    Path(settings.VAULT_PATH).mkdir(parents=True, exist_ok=True)

    # 5. asyncio.Queue 생성 및 Worker-1, Worker-2 태스크 시작
    app.state.ingestion_queue = asyncio.Queue()
    app.state.analysis_queue = asyncio.Queue()
    app.state.composite_repo = CompositeRepository(...)
    asyncio.create_task(worker_1_loop(app.state))
    asyncio.create_task(worker_2_loop(app.state))

    # 6. failed_tasks.db에서 pending 항목 자동 재적재
    await reload_failed_tasks(app.state.ingestion_queue)

    # 7. Ollama 연결 상태 확인 (실패해도 서버는 기동)
    await check_ollama_connection()

    yield
    # shutdown: 워커 태스크 정리
```

---

## 파일 구조

```
backend/
├── main.py                  # FastAPI 앱 진입점 (lifespan 이벤트 포함)
├── config.py                # pydantic-settings Settings 클래스
├── exceptions.py            # OllamaUnavailableError 등
├── routers/
│   └── collect.py           # POST /api/v1/collect
└── workers/
    └── queue_manager.py     # ingestion_queue, analysis_queue, worker loop
```

---

## collect.py 구현 가이드

```python
@router.post("/collect", response_model=CollectResponse)
async def collect(
    request: CollectRequest,
    app_state = Depends(get_app_state)
):
    # 1. 블랙리스트 확인
    # 2. 중복 URL 확인 (app_state.composite_repo.exists_by_url)
    # 3. await app_state.ingestion_queue.put(request)
    # 4. 즉시 CollectResponse(status="queued", id=uuid4()) 반환
```

---

## 환경변수 명세

`docs/schemas.md`의 Settings 클래스 참고.
