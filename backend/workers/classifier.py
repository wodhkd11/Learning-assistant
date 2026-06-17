import json
import time

import httpx
import structlog

from backend.config import settings
from backend.exceptions import OllamaUnavailableError
from backend.schemas.document import CollectRequest
from backend.schemas.llm import ClassificationResult

log = structlog.get_logger()

_SYSTEM_PROMPT = "당신은 웹 콘텐츠 분류기입니다. 반드시 JSON만 반환하세요."

_USER_TEMPLATE = """\
다음 웹 페이지가 지식/학습 가치가 있는 문서인지 판단하세요.
제목: {title}
본문 요약 (2000자): {content_preview}
응답 형식: {{"is_knowledge": bool, "confidence": 0.0~1.0, "reason": "한 줄 이유"}}"""


async def classify(request: CollectRequest) -> ClassificationResult:
    """
    Ollama API를 호출하여 문서의 지식 가치를 이진 분류한다.
    반환: ClassificationResult
    예외: OllamaUnavailableError (호출자가 failed_tasks.db에 저장)
    """
    model_id = f"ollama/{settings.OLLAMA_MODEL}"
    user_msg = _USER_TEMPLATE.format(
        title=request.title,
        content_preview=request.content[:2000],
    )
    prompt = f"SYSTEM: {_SYSTEM_PROMPT}\nUSER: {user_msg}"

    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )
            response.raise_for_status()
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        log.warning("ollama_unavailable", url=request.url, error=str(exc))
        raise OllamaUnavailableError(f"Ollama connection failed: {exc}") from exc
    except httpx.HTTPStatusError as exc:
        log.warning("ollama_http_error", status=exc.response.status_code, url=request.url)
        raise OllamaUnavailableError(f"Ollama HTTP error: {exc.response.status_code}") from exc

    latency_ms = int((time.monotonic() - t0) * 1000)

    raw = response.json().get("response", "{}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end])

    is_knowledge: bool = bool(data.get("is_knowledge", False))
    confidence: float = float(data.get("confidence", 0.0))
    reason: str = str(data.get("reason", ""))

    log.info(
        "ollama_classify_done",
        url=request.url,
        is_knowledge=is_knowledge,
        confidence=confidence,
        latency_ms=latency_ms,
    )

    return ClassificationResult(
        is_knowledge=is_knowledge,
        confidence=confidence,
        reason=reason,
        model_used=model_id,
        latency_ms=latency_ms,
    )
