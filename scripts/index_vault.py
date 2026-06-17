#!/usr/bin/env python3
"""Obsidian 볼트 내 .md 파일을 ChromaDB에 일괄 색인하는 CLI.

사용법:
    python scripts/index_vault.py

동작:
    1. obsidian_vault/ 내 모든 .md 파일 탐색
    2. YAML Front-matter 파싱
    3. exists_by_url() 확인 후 미색인 파일만 색인
    4. 진행률 출력
"""

import asyncio
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog

# 프로젝트 루트에서 실행 가능하도록 sys.path 보정
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.schemas.document import DocumentRecord, RelatedDoc
from backend.storage.chroma import ChromaRepository

log = structlog.get_logger()

_FRONTMATTER_RE = re.compile(r"^---[ \t]*\n(.*?)\n---[ \t]*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """YAML front-matter를 파싱하여 (meta_dict, body)를 반환한다."""
    try:
        import yaml
    except ImportError:
        return {}, text

    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except Exception:
        meta = {}

    return meta, text[match.end():]


def _meta_to_doc(
    meta: dict,
    body: str,
    file_path: Path,
    vault_root: Path,
) -> tuple[DocumentRecord, str] | None:
    """Front-matter + body → (DocumentRecord, rel_path). 필수 필드 없으면 None."""
    url = meta.get("url") or meta.get("source_url")
    title = meta.get("title")
    if not url or not title:
        return None

    # tags: 문자열 또는 리스트 모두 수용
    tags_raw = meta.get("tags", [])
    if isinstance(tags_raw, str):
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    elif isinstance(tags_raw, list):
        tags = [str(t) for t in tags_raw]
    else:
        tags = []

    # collected_at 파싱
    collected_at_raw = meta.get("collected_at") or meta.get("date")
    try:
        collected_at = (
            datetime.fromisoformat(str(collected_at_raw))
            if collected_at_raw
            else datetime.utcnow()
        )
    except ValueError:
        collected_at = datetime.utcnow()

    # related_docs 파싱
    related_docs: list[RelatedDoc] = []
    for r in meta.get("related_docs", []):
        if isinstance(r, dict):
            related_docs.append(RelatedDoc(title=r.get("title", ""), reason=r.get("reason", "")))

    rel_path = str(file_path.relative_to(vault_root))

    doc = DocumentRecord(
        url=url,
        title=str(title),
        source_title=meta.get("source_title", str(title)),
        refined_content=body.strip(),
        summary=meta.get("summary", ""),
        tags=tags,
        category=meta.get("category", ""),
        related_docs=related_docs,
        collected_at=collected_at,
        updated_at=collected_at,
    )
    return doc, rel_path


async def run_index_vault(repo: Optional[ChromaRepository] = None) -> None:
    """볼트 전체를 스캔하여 미색인 .md 파일을 ChromaDB에 색인한다."""
    if repo is None:
        repo = ChromaRepository()

    vault_root = Path(settings.VAULT_PATH)
    if not vault_root.exists():
        log.warning("index_vault.vault_not_found", path=str(vault_root))
        print(f"볼트 경로가 존재하지 않습니다: {vault_root}")
        return

    md_files = list(vault_root.rglob("*.md"))
    total = len(md_files)
    log.info("index_vault.start", total_files=total)
    print(f"총 {total}개 .md 파일 발견. 색인 시작...")

    indexed = skipped = errors = 0

    for i, file_path in enumerate(md_files, 1):
        try:
            text = file_path.read_text(encoding="utf-8")
            meta, body = _parse_frontmatter(text)

            result = _meta_to_doc(meta, body, file_path, vault_root)
            if result is None:
                skipped += 1
                continue

            doc, rel_path = result

            if await repo.exists_by_url(doc.url):
                skipped += 1
                continue

            await repo.index(doc, rel_path)
            indexed += 1

            # 진행률 표시 (10개마다 또는 마지막)
            if i % 10 == 0 or i == total:
                print(f"  [{i}/{total}] 색인: {file_path.name}")

        except Exception as exc:
            errors += 1
            log.error("index_vault.error", file=str(file_path), error=str(exc))

    log.info("index_vault.done", indexed=indexed, skipped=skipped, errors=errors)
    print(f"\n색인 완료 — 신규: {indexed}개, 건너뜀: {skipped}개, 오류: {errors}개")


if __name__ == "__main__":
    asyncio.run(run_index_vault())
