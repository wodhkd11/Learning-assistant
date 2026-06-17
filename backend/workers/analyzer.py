from datetime import datetime, timezone

import structlog

from backend.exceptions import LLMAllProvidersFailedError, LLMRateLimitError
from backend.llm.factory import LLMFactory
from backend.schemas.document import CollectRequest, DocumentRecord
from backend.schemas.llm import AnalysisResult
from backend.storage.repository import BaseRepository
from backend.utils.paper_detector import detect_paper_site
from backend.utils.series_detector import extract_book_title, make_series_slug

log = structlog.get_logger()


def _build_content_with_hint(request: CollectRequest) -> str:
    """
    1. document_title에서 책 제목 추출 성공 시 series 고정 지침 삽입.
    2. 논문 사이트 감지 시 document_type='paper' 고정 지침 삽입.
    힌트 없으면 원본 content 그대로 반환.
    """
    hints: list[str] = []

    book_title = extract_book_title(request.document_title)
    if book_title:
        slug = make_series_slug(book_title, request.url)
        log.info(
            "series_hint_from_document_title",
            document_title=request.document_title,
            book_title=book_title,
            slug=slug,
            url=request.url,
        )
        hints.append(
            f"[시리즈 지침]\n"
            f"document_title에서 추출된 책 제목: {book_title}\n"
            f"series는 반드시 '{slug}'로 고정해라.\n"
            f"series_title은 '{book_title}'로 고정해라."
        )

    is_paper = detect_paper_site(request.url)
    if is_paper:
        log.info("paper_site_detected", url=request.url)
        hints.append(
            "[논문 지침]\n"
            "이 URL은 학술 논문 사이트입니다. document_type은 반드시 'paper'로 설정하세요.\n"
            "이 문서는 학술 논문입니다. 본문이 잘려있을 수 있으나 "
            "Abstract와 Introduction을 중심으로 요약해라."
        )

    content = request.content[:15000] if is_paper else request.content

    if not hints:
        return content

    return "\n---\n".join(hints) + "\n---\n" + content


async def analyze(request: CollectRequest, repo: BaseRepository) -> DocumentRecord:
    """
    1. repo.search()로 연관 후보 추출 (ChromaDB 쿼리)
    2. 힌트 생성 (series, paper site)
    3. LLMFactory.get_priority_list()로 프로바이더 순서 결정
    4. 각 프로바이더를 순서대로 시도; LLMRateLimitError 시 다음으로 전환
    5. DocumentRecord 조립 후 반환
    저장은 호출자(worker_2_loop)가 repo.save()로 처리.
    """
    vault_context: list[dict] = await repo.search(request.title, limit=5)
    effective_content = _build_content_with_hint(request)

    priority = LLMFactory.get_priority_list()
    last_exc: Exception | None = None
    result: AnalysisResult | None = None

    for provider in priority:
        try:
            client = LLMFactory.create(provider)
            result = await client.analyze(
                content=effective_content,
                title=request.title,
                vault_context=vault_context,
                url=request.url,
            )
            break
        except LLMRateLimitError as exc:
            log.warning(
                "analyzer_rate_limit_switch",
                provider=provider,
                url=request.url,
            )
            last_exc = exc
        except Exception as exc:
            log.error(
                "analyzer_unexpected_error",
                provider=provider,
                error=str(exc),
                url=request.url,
            )
            last_exc = exc

    if result is None:
        raise LLMAllProvidersFailedError(
            f"All LLM providers failed for {request.url}"
        ) from last_exc

    now = datetime.now(timezone.utc)
    return DocumentRecord(
        url=request.url,
        title=result.summary[:80] if not request.title else request.title,
        source_title=request.title,
        refined_content=result.refined_content,
        summary=result.summary,
        tags=result.tags,
        category=result.category,
        related_docs=result.related_docs,
        collected_at=request.timestamp,
        updated_at=now,
        series=result.series,
        series_title=result.series_title,
        series_order=result.series_order,
        document_type=result.document_type,
        paper_meta=result.paper_meta,
    )
