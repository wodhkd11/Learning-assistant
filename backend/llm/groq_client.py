import json
import time

import structlog
from groq import AsyncGroq
from groq import RateLimitError as GroqRateLimitError

from backend.config import settings
from backend.exceptions import LLMRateLimitError
from backend.llm.factory import BaseLLMClient
from backend.schemas.document import RelatedDoc
from backend.schemas.llm import AnalysisResult

log = structlog.get_logger()

_SYSTEM_PROMPT = (
    "당신은 지식 관리 전문가입니다. 다음 웹 문서를 분석하여 JSON으로 반환하세요.\n"
    "본문에 사이드바 목차, 네비게이션, 광고 텍스트가 포함되어 있을 수 있다.\n"
    "이를 무시하고 실제 학습/지식 본문 내용만 추출하여 분석해라.\n"
    "목차 항목 나열은 요약에 포함하지 말고,\n"
    "실제 설명, 개념, 코드, 예제 위주로 요약해라."
)

_USER_TEMPLATE = """\
[신규 문서]
제목: {title}
URL: {url}
본문: {content}

[기존 연관 후보 문서 (최대 5개)]
{vault_context}

응답 형식:
{{
  "summary": "3~5문장 요약",
  "tags": ["태그1", "태그2"],
  "category": "AI/Software Engineering",
  "related_docs": [
    {{"title": "기존 문서 제목", "reason": "연관 이유 서술"}}
  ],
  "refined_content": "정제된 본문 전문",
  "series": "시리즈 고유 슬러그 (영문 소문자, 하이픈 구분). 예: cpp-beginner-wikidocs, fastapi-tutorial-wikidocs. 같은 책/강의/시리즈에 속한 문서는 반드시 동일한 값. 독립 문서면 null.",
  "series_title": "시리즈의 한국어 제목. 예: C++ 입문, FastAPI 튜토리얼. 독립 문서면 null.",
  "series_order": 시리즈 내 순서 숫자 또는 null,
  "document_type": "paper | tutorial | blog | wiki | docs | news | other 중 하나",
  "paper_meta": {{"authors": ["저자1", "저자2"], "doi": "10.xxxx/xxx", "published_year": 2024, "venue": "NeurIPS 2024"}} 또는 null
}}

중요: 같은 책/강의에서 나온 문서들은 반드시 series 값이 동일해야 한다.
제목, 본문 내용, URL 도메인을 종합적으로 판단해라.
관련 없는 문서는 related_docs에 포함하지 마세요.
document_type은 URL과 본문을 보고 판단해라. 학술 논문이면 paper_meta도 최대한 채워라."""


class GroqClient(BaseLLMClient):
    MODEL = "llama-3.3-70b-versatile"

    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def analyze(
        self,
        content: str,
        title: str,
        vault_context: list[dict],
        url: str = "",
    ) -> AnalysisResult:
        vault_str = json.dumps(vault_context, ensure_ascii=False, indent=2)
        user_msg = _USER_TEMPLATE.format(
            title=title,
            url=url,
            content=content,
            vault_context=vault_str,
        )

        t0 = time.monotonic()
        try:
            response = await self._client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                response_format={"type": "json_object"},
                max_tokens=4000,
            )
        except GroqRateLimitError as exc:
            log.warning("groq_rate_limit", error=str(exc))
            raise LLMRateLimitError("Groq 429 rate limit") from exc

        latency_ms = int((time.monotonic() - t0) * 1000)
        raw = response.choices[0].message.content or "{}"

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            data = json.loads(raw[start:end])

        related_docs = [
            RelatedDoc(title=r["title"], reason=r["reason"])
            for r in data.get("related_docs", [])
        ]

        log.info(
            "groq_analyze_done",
            title=title,
            latency_ms=latency_ms,
            tags=data.get("tags", []),
        )

        series_order_raw = data.get("series_order")
        paper_meta = data.get("paper_meta") or None
        if isinstance(paper_meta, dict) and not any(paper_meta.values()):
            paper_meta = None
        return AnalysisResult(
            summary=data["summary"],
            tags=data.get("tags", []),
            category=data.get("category", ""),
            related_docs=related_docs,
            refined_content=data.get("refined_content", content),
            series=data.get("series") or None,
            series_title=data.get("series_title") or None,
            series_order=int(series_order_raw) if series_order_raw is not None else None,
            document_type=data.get("document_type") or None,
            paper_meta=paper_meta,
        )
