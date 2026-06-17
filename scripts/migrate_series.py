#!/usr/bin/env python3
"""obsidian_vault 소급 마이그레이션 스크립트.

Phase 1 — LLM 기반 series 판단:
    볼트 전체 .md 파일을 그룹핑하여 LLM으로 series 메타데이터를 결정하고
    YAML front-matter와 ChromaDB를 업데이트한다.

Phase 2 — 파일 재조직:
    볼트 루트에 있는 .md 파일들을 YAML series 필드에 따라
    {series}/ 또는 unsorted/ 하위 디렉토리로 이동하고
    ChromaDB file_path도 업데이트한다.

사용법:
    python scripts/migrate_series.py          # Phase 1 + Phase 2
    python scripts/migrate_series.py --phase1 # LLM 판단만
    python scripts/migrate_series.py --phase2 # 파일 이동만
"""

import asyncio
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import structlog
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.exceptions import LLMRateLimitError
from backend.llm.factory import LLMFactory
from backend.storage.chroma import ChromaRepository

log = structlog.get_logger()

_FRONTMATTER_RE = re.compile(r"^---[ \t]*\n(.*?)\n---[ \t]*\n", re.DOTALL)
_SERIES_KEYS = re.compile(r"^(series|series_title|series_order):.*\n?", re.MULTILINE)


# ------------------------------------------------------------------
# 공통 유틸
# ------------------------------------------------------------------

def _group_key(url: str) -> str:
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        segments = [s for s in parsed.path.strip("/").split("/") if s]
        first_seg = segments[0] if segments else ""
        return f"{host}/{first_seg}"
    except Exception:
        return url


def _parse_file(file_path: Path) -> tuple[dict, str] | None:
    try:
        text = file_path.read_text(encoding="utf-8")
    except Exception:
        return None
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None
    try:
        fm = yaml.safe_load(match.group(1)) or {}
    except Exception:
        return None
    return fm, text[match.end():]


def _update_yaml_series(
    file_path: Path,
    series: str,
    series_title: str | None,
    series_order: int | None,
) -> None:
    text = file_path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return

    fm_text = _SERIES_KEYS.sub("", match.group(1)).rstrip("\n")
    rest = text[match.end():]

    fm_text += f'\nseries: "{series}"'
    if series_title:
        st = series_title.replace('"', '\\"')
        fm_text += f'\nseries_title: "{st}"'
    if series_order is not None:
        fm_text += f"\nseries_order: {series_order}"

    file_path.write_text(f"---\n{fm_text}\n---\n{rest}", encoding="utf-8")


async def _update_chroma_series(
    repo: ChromaRepository,
    url: str,
    series: str,
    series_title: str | None,
    series_order: int | None,
) -> None:
    doc_id = ChromaRepository._url_to_id(url)
    existing = await asyncio.to_thread(
        repo._collection.get, ids=[doc_id], include=["metadatas", "documents"]
    )
    if not existing["ids"]:
        return

    meta = existing["metadatas"][0].copy()
    meta["series"] = series
    if series_title:
        meta["series_title"] = series_title
    elif "series_title" in meta:
        del meta["series_title"]
    if series_order is not None:
        meta["series_order"] = series_order
    elif "series_order" in meta:
        del meta["series_order"]

    document_text = existing["documents"][0] if existing.get("documents") else ""
    await asyncio.to_thread(
        repo._collection.upsert,
        ids=[doc_id],
        documents=[document_text],
        metadatas=[meta],
    )


async def _update_chroma_file_path(
    repo: ChromaRepository,
    url: str,
    new_file_path: str,
) -> None:
    doc_id = ChromaRepository._url_to_id(url)
    existing = await asyncio.to_thread(
        repo._collection.get, ids=[doc_id], include=["metadatas", "documents"]
    )
    if not existing["ids"]:
        return

    meta = existing["metadatas"][0].copy()
    meta["file_path"] = new_file_path
    document_text = existing["documents"][0] if existing.get("documents") else ""
    await asyncio.to_thread(
        repo._collection.upsert,
        ids=[doc_id],
        documents=[document_text],
        metadatas=[meta],
    )


async def _call_llm(
    title: str, content: str, url: str
) -> tuple[str | None, str | None, int | None]:
    priority = LLMFactory.get_priority_list()
    for provider in priority:
        try:
            client = LLMFactory.create(provider)
            result = await client.analyze(
                content=content,
                title=title,
                vault_context=[],
                url=url,
            )
            return result.series, result.series_title, result.series_order
        except LLMRateLimitError:
            log.warning("migrate.rate_limit", provider=provider)
            continue
        except Exception as exc:
            log.error("migrate.llm_error", provider=provider, error=str(exc))
            continue
    return None, None, None


# ------------------------------------------------------------------
# Phase 1 — LLM 기반 series 판단
# ------------------------------------------------------------------

async def run_phase1_llm(repo: ChromaRepository, vault_root: Path) -> None:
    print("\n[Phase 1] LLM 기반 series 메타데이터 판단 시작...")

    md_files = list(vault_root.rglob("*.md"))
    print(f"  {len(md_files)}개 파일 발견")

    file_data: list[dict] = []
    for file_path in md_files:
        parsed = _parse_file(file_path)
        if parsed is None:
            continue
        fm, body = parsed

        url = fm.get("url") or fm.get("source_url")
        if not url:
            continue

        title = str(fm.get("source_title", ""))
        for line in body.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break

        file_data.append({
            "file_path": file_path,
            "url": str(url),
            "title": title,
            "content": body.strip(),
            "group_key": _group_key(str(url)),
        })

    groups: dict[str, list[dict]] = defaultdict(list)
    for item in file_data:
        groups[item["group_key"]].append(item)

    print(f"  {len(groups)}개 그룹, {len(file_data)}개 문서 처리 중...")

    llm_calls = skipped = copied = errors = 0

    for group_key, items in groups.items():
        first = items[0]
        series, series_title, series_order = await _call_llm(
            title=first["title"], content=first["content"], url=first["url"]
        )
        llm_calls += 1

        if series is None:
            skipped += len(items)
            await asyncio.sleep(1)
            continue

        try:
            _update_yaml_series(first["file_path"], series, series_title, series_order)
            await _update_chroma_series(repo, first["url"], series, series_title, series_order)
        except Exception as exc:
            errors += 1
            log.error("phase1.update_error", file=str(first["file_path"]), error=str(exc))

        for item in items[1:]:
            try:
                _update_yaml_series(item["file_path"], series, series_title, None)
                await _update_chroma_series(repo, item["url"], series, series_title, None)
                copied += 1
            except Exception as exc:
                errors += 1
                log.error("phase1.copy_error", file=str(item["file_path"]), error=str(exc))

        await asyncio.sleep(1)

    print(
        f"  완료 — LLM 호출: {llm_calls}회, 복사: {copied}개, "
        f"독립: {skipped}개, 오류: {errors}개"
    )


# ------------------------------------------------------------------
# Phase 2 — 파일 재조직 (루트 → 하위 디렉토리)
# ------------------------------------------------------------------

async def run_phase2_reorganize(repo: ChromaRepository, vault_root: Path) -> None:
    print("\n[Phase 2] 파일 재조직 시작 (루트 .md → 하위 디렉토리)...")

    # 루트 직속 .md 파일만 대상 (.obsidian 등 숨김 제외)
    root_md_files = [
        f for f in vault_root.glob("*.md")
        if f.is_file()
    ]
    print(f"  루트 파일 {len(root_md_files)}개 발견")

    moved = skipped = errors = 0

    for file_path in root_md_files:
        parsed = _parse_file(file_path)
        if parsed is None:
            skipped += 1
            continue

        fm, _ = parsed
        url = fm.get("url") or fm.get("source_url")
        series = fm.get("series") or None

        target_dir_name = series if series else "unsorted"
        target_dir = vault_root / target_dir_name
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / file_path.name

        # 동일 이름 파일 충돌 방지
        if target_path.exists():
            stem = file_path.stem
            target_path = target_dir / f"{stem}_moved{file_path.suffix}"

        try:
            shutil.move(str(file_path), str(target_path))
            new_rel = target_path.relative_to(vault_root).as_posix()
            log.info("phase2.moved", from_=file_path.name, to=new_rel)

            if url:
                await _update_chroma_file_path(repo, str(url), new_rel)

            moved += 1
            print(f"  {file_path.name} → {new_rel}")
        except Exception as exc:
            errors += 1
            log.error("phase2.move_error", file=str(file_path), error=str(exc))

    print(f"\n  완료 — 이동: {moved}개, 건너뜀: {skipped}개, 오류: {errors}개")


# ------------------------------------------------------------------
# 진입점
# ------------------------------------------------------------------

async def run_migrate(
    repo: ChromaRepository | None = None,
    phase1: bool = True,
    phase2: bool = True,
) -> None:
    if repo is None:
        repo = ChromaRepository()

    vault_root = Path(settings.VAULT_PATH)
    if not vault_root.exists():
        print(f"볼트 경로가 존재하지 않습니다: {vault_root}")
        return

    if phase1:
        await run_phase1_llm(repo, vault_root)
    if phase2:
        await run_phase2_reorganize(repo, vault_root)

    print("\n마이그레이션 완료.")


if __name__ == "__main__":
    args = sys.argv[1:]
    only1 = "--phase1" in args
    only2 = "--phase2" in args

    if only1:
        asyncio.run(run_migrate(phase1=True, phase2=False))
    elif only2:
        asyncio.run(run_migrate(phase1=False, phase2=True))
    else:
        asyncio.run(run_migrate())
