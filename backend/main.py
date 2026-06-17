import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI

from backend.config import settings
from backend.storage.chroma import init_chroma
from backend.storage.composite import CompositeRepository
from backend.storage.obsidian import ObsidianRepository
from backend.temp.queue_db import init_queue_db, reload_failed_tasks
from backend.workers.queue_manager import (
    check_ollama_connection,
    worker_1_loop,
    worker_2_loop,
)

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    ),
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
)

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. .temp/ 디렉토리 초기화
    Path(settings.TEMP_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.TEMP_DIR + "/raw_cache").mkdir(exist_ok=True)
    log.info("lifespan.temp_dir_ready", path=settings.TEMP_DIR)

    # 2. SQLite failed_tasks.db 초기화 (테이블 생성)
    await init_queue_db()
    log.info("lifespan.queue_db_ready")

    # 3. ChromaDB PersistentClient 초기화 + 컬렉션 생성
    chroma_repo = init_chroma()
    log.info("lifespan.chroma_ready", path=settings.CHROMA_DB_PATH)

    # 4. Obsidian 볼트 경로 확인/생성
    Path(settings.VAULT_PATH).mkdir(parents=True, exist_ok=True)
    log.info("lifespan.vault_ready", path=settings.VAULT_PATH)

    # 5. asyncio.Queue 생성 및 Worker-1, Worker-2 태스크 시작
    app.state.ingestion_queue = asyncio.Queue()
    app.state.analysis_queue = asyncio.Queue()
    app.state.composite_repo = CompositeRepository(
        obsidian=ObsidianRepository(vault_path=settings.VAULT_PATH),
        chroma=chroma_repo,
    )
    w1 = asyncio.create_task(worker_1_loop(app.state), name="worker-1")
    w2 = asyncio.create_task(worker_2_loop(app.state), name="worker-2")
    log.info("lifespan.workers_started")

    # 6. failed_tasks.db에서 pending 항목 자동 재적재
    await reload_failed_tasks(app.state.ingestion_queue)
    log.info("lifespan.failed_tasks_reloaded")

    # 7. Ollama 연결 상태 확인 (실패해도 서버는 기동)
    await check_ollama_connection()

    yield

    # shutdown: 워커 태스크 정리
    w1.cancel()
    w2.cancel()
    await asyncio.gather(w1, w2, return_exceptions=True)
    log.info("lifespan.workers_stopped")


app = FastAPI(
    title="KALF API",
    version="1.0.0",
    description="Knowledge-Agent-Local-First — 개인 지식 수집·검색 에이전트",
    lifespan=lifespan,
)

from backend.routers.collect import router as collect_router  # noqa: E402
from backend.routers.search import router as search_router  # noqa: E402

app.include_router(collect_router, prefix="/api/v1", tags=["collect"])
app.include_router(search_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
