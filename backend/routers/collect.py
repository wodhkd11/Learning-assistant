import uuid
from urllib.parse import urlparse

import structlog
from fastapi import APIRouter, Depends, Request

from backend.schemas.document import CollectRequest, CollectResponse

log = structlog.get_logger()

router = APIRouter()

BLACKLIST_DOMAINS: set[str] = {
    "localhost",
    "127.0.0.1",
    "naver.com",
    "daum.net",
    "google.com",
    "youtube.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "facebook.com",
}


def _extract_domain(url: str) -> str:
    try:
        hostname = urlparse(url).hostname or ""
        # www. 제거 후 반환
        return hostname.removeprefix("www.")
    except Exception:
        return ""


def get_app_state(request: Request):
    return request.app.state


@router.post("/collect", response_model=CollectResponse)
async def collect(
    request: CollectRequest,
    app_state=Depends(get_app_state),
):
    domain = _extract_domain(request.url)
    request_id = uuid.uuid4()

    # 1. 블랙리스트 확인
    if domain in BLACKLIST_DOMAINS:
        log.info("collect.blacklisted", url=request.url, domain=domain)
        return CollectResponse(status="blacklisted", id=request_id)

    # 2. 중복 URL 확인 (ChromaDB 기반, 파일 파싱 없음)
    try:
        if await app_state.composite_repo.exists_by_url(request.url):
            log.info("collect.duplicate", url=request.url)
            return CollectResponse(status="duplicate", id=request_id)
    except NotImplementedError:
        # composite_repo 스텁 단계에서는 중복 체크 생략
        pass

    # 3. 비동기 큐에 적재 후 즉시 반환 (BackgroundTasks 미사용)
    await app_state.ingestion_queue.put(request)
    log.info("collect.queued", request_id=str(request_id), url=request.url)

    # 4. 즉시 200 OK 반환
    return CollectResponse(status="queued", id=request_id)
