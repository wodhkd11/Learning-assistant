import asyncio
import uuid
from typing import TYPE_CHECKING

import structlog

from backend.config import settings
from backend.exceptions import OllamaUnavailableError
from backend.schemas.document import CollectRequest
from backend.temp.queue_db import increment_retry, save_failed, update_status

if TYPE_CHECKING:
    from starlette.datastructures import State

log = structlog.get_logger()

MAX_RETRY_COUNT = 3


async def worker_1_loop(app_state: "State") -> None:
    """
    ingestion_queue에서 CollectRequest를 꺼내 classifier.classify()를 호출한다.
    True 판정 시 analysis_queue에 적재.
    Ollama 장애 시 queue_db.save_failed()로 영속화.
    """
    from backend.workers.classifier import classify  # 코더 C가 구현

    log.info("worker_1_loop.started")
    while True:
        request: CollectRequest = await app_state.ingestion_queue.get()
        request_id = str(uuid.uuid4())
        try:
            result = await classify(request)
            if result.is_knowledge:
                await app_state.analysis_queue.put(request)
                log.info(
                    "worker_1.classified_knowledge",
                    request_id=request_id,
                    url=request.url,
                    confidence=result.confidence,
                )
            else:
                log.info(
                    "worker_1.discarded",
                    request_id=request_id,
                    url=request.url,
                    reason=result.reason,
                )
        except OllamaUnavailableError:
            log.warning("worker_1.ollama_unavailable", request_id=request_id, url=request.url)
            await save_failed(request_id, request)
        except Exception:
            log.exception("worker_1.unexpected_error", request_id=request_id, url=request.url)
        finally:
            app_state.ingestion_queue.task_done()


async def worker_2_loop(app_state: "State") -> None:
    """
    analysis_queue에서 CollectRequest를 꺼내 analyzer.analyze()를 호출한다.
    결과를 CompositeRepository.save()에 전달.
    """
    from backend.workers.analyzer import analyze  # 코더 D가 구현

    log.info("worker_2_loop.started")
    while True:
        request: CollectRequest = await app_state.analysis_queue.get()
        request_id = str(uuid.uuid4())
        try:
            doc = await analyze(request, app_state.composite_repo)
            file_path = await app_state.composite_repo.save(doc)
            log.info(
                "worker_2.saved",
                request_id=request_id,
                url=request.url,
                file_path=file_path,
            )
        except Exception:
            log.exception("worker_2.unexpected_error", request_id=request_id, url=request.url)
        finally:
            app_state.analysis_queue.task_done()


async def check_ollama_connection() -> bool:
    """Ollama 연결 상태 확인. 실패해도 서버 기동을 막지 않는다."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                log.info("ollama.connection_ok", base_url=settings.OLLAMA_BASE_URL)
                return True
            log.warning("ollama.unexpected_status", status_code=resp.status_code)
            return False
    except Exception as exc:
        log.warning("ollama.connection_failed", error=str(exc))
        return False
