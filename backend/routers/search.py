import asyncio
import time
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Request

from backend.schemas.search import SearchResult, VaultStats

log = structlog.get_logger()

router = APIRouter(tags=["search"])


def _to_search_result(r: dict) -> SearchResult:
    collected_at_raw = r.get("collected_at", "")
    try:
        collected_at = datetime.fromisoformat(collected_at_raw) if collected_at_raw else datetime.utcnow()
    except ValueError:
        collected_at = datetime.utcnow()

    return SearchResult(
        title=r["title"],
        url=r["url"],
        summary=r["summary"],
        category=r["category"],
        tags=r["tags"],
        collected_at=collected_at,
        score=r["score"],
        file_path=r["file_path"],
        snippet=None,
        series=r.get("series"),
        series_title=r.get("series_title"),
        series_order=r.get("series_order"),
        document_type=r.get("document_type"),
    )


@router.get("/search", response_model=list[SearchResult])
async def search(
    request: Request,
    q: Optional[str] = None,
    tag: Optional[str] = None,
    series: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 5,
) -> list[SearchResult]:
    if not q and not tag and not series and not type:
        raise HTTPException(
            status_code=400,
            detail="q, tag, series, 또는 type 파라미터가 필요합니다.",
        )

    composite = request.app.state.composite_repo
    start = time.monotonic()

    if q:
        fetch_limit = limit * 3 if (tag or series or type) else limit
        results = await composite.search(q, limit=fetch_limit)
        if tag:
            results = [r for r in results if tag in r["tags"]]
        if series:
            results = [r for r in results if r.get("series") == series]
        if type:
            results = [r for r in results if r.get("document_type") == type]
        results = results[:limit]
    else:
        results = await composite.list_documents(tag=tag, series=series, document_type=type)
        results = results[:limit]

    elapsed = int((time.monotonic() - start) * 1000)
    log.info("search.complete", q=q, tag=tag, series=series, type=type, count=len(results), latency_ms=elapsed)

    return [_to_search_result(r) for r in results]


@router.get("/document/{title}")
async def get_document(title: str, request: Request):
    doc = await request.app.state.composite_repo.get(title)
    if not doc:
        raise HTTPException(status_code=404, detail=f"문서를 찾을 수 없습니다: {title}")
    return doc


@router.get("/documents", response_model=list[SearchResult])
async def list_documents(
    request: Request,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    series: Optional[str] = None,
    document_type: Optional[str] = None,
) -> list[SearchResult]:
    results = await request.app.state.composite_repo.list_documents(
        category=category, tag=tag, series=series, document_type=document_type
    )
    return [_to_search_result(r) for r in results]


@router.get("/search/stats", response_model=VaultStats)
async def get_stats(request: Request) -> VaultStats:
    raw = await request.app.state.composite_repo.get_stats()

    latest = None
    if raw["latest_collected_at"]:
        try:
            latest = datetime.fromisoformat(raw["latest_collected_at"])
        except ValueError:
            pass

    return VaultStats(
        total_documents=raw["total_documents"],
        categories=raw["categories"],
        latest_collected_at=latest,
        total_tags=raw["total_tags"],
    )


@router.post("/index/rebuild")
async def rebuild_index(request: Request) -> dict:
    from scripts.index_vault import run_index_vault

    asyncio.create_task(run_index_vault(request.app.state.composite_repo._chroma))
    log.info("index.rebuild.started")
    return {"status": "started"}
