from pydantic import BaseModel

from backend.schemas.document import RelatedDoc


class ClassificationResult(BaseModel):
    is_knowledge: bool
    confidence: float
    reason: str
    model_used: str
    latency_ms: int


class AnalysisResult(BaseModel):
    summary: str
    tags: list[str]
    category: str
    related_docs: list[RelatedDoc]
    refined_content: str
    series: str | None = None          # LLM이 판단한 시리즈 슬러그 (영문 소문자, 하이픈 구분)
    series_title: str | None = None    # LLM이 판단한 시리즈 한국어 제목
    series_order: int | None = None    # 시리즈 내 순서 (파악 불가능하면 None)
    document_type: str | None = None   # paper | tutorial | blog | wiki | docs | news | other
    paper_meta: dict | None = None     # 논문 전용 메타데이터
