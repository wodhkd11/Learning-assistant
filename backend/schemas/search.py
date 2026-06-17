from datetime import datetime

from pydantic import BaseModel


class SearchResult(BaseModel):
    title: str
    url: str
    summary: str
    category: str
    tags: list[str]
    collected_at: datetime
    score: float
    file_path: str
    snippet: str | None
    series: str | None = None
    series_title: str | None = None
    series_order: int | None = None
    document_type: str | None = None


class VaultStats(BaseModel):
    total_documents: int
    categories: dict[str, int]
    latest_collected_at: datetime | None
    total_tags: int
