from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class CollectRequest(BaseModel):
    url: str
    title: str
    content: str
    timestamp: datetime
    document_title: str | None = None


class CollectResponse(BaseModel):
    status: Literal["queued", "duplicate", "blacklisted"]
    id: UUID


class RelatedDoc(BaseModel):
    title: str
    reason: str


class DocumentRecord(BaseModel):
    url: str
    title: str
    source_title: str
    refined_content: str
    summary: str
    tags: list[str]
    category: str
    related_docs: list[RelatedDoc]
    collected_at: datetime
    updated_at: datetime
    series: str | None = None          # 시리즈 고유 ID (예: "wikidocs-300272")
    series_title: str | None = None    # 사람이 읽을 수 있는 시리즈 제목
    series_order: int | None = None    # 챕터/페이지 순서
    document_type: str | None = None   # paper | tutorial | blog | wiki | docs | news | other
    paper_meta: dict | None = None     # 논문 전용: {authors, doi, published_year, venue}
