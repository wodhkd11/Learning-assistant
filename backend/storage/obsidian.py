import asyncio
import re
from datetime import datetime
from pathlib import Path

import structlog
import yaml

from backend.config import settings
from backend.schemas.document import DocumentRecord, RelatedDoc
from backend.storage.repository import BaseRepository

log = structlog.get_logger()

_SPECIAL_CHARS = re.compile(r'[/\\:*?"<>|]')
_RELATED_LINE = re.compile(r'^- \[\[(.+?)\]\]: (.+)$')


def _sanitize_filename(title: str, suffix: str = "") -> str:
    clean = _SPECIAL_CHARS.sub('', title)
    clean = clean.replace(' ', '_')
    clean = clean[:200]
    return f"{clean}{suffix}.md" if suffix else f"{clean}.md"


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _read_file(path: Path) -> str:
    return path.read_text(encoding='utf-8')


class ObsidianRepository(BaseRepository):
    def __init__(self, vault_path: str | None = None) -> None:
        self._vault_path = Path(vault_path or settings.VAULT_PATH)
        # 인스턴스 수준 Lock — 테스트 격리 및 이벤트 루프 호환성 보장
        self._lock = asyncio.Lock()

    def _render_markdown(self, doc: DocumentRecord) -> str:
        tags_yaml = '[' + ', '.join(doc.tags) + ']'
        collected_str = doc.collected_at.strftime('%Y-%m-%d %H:%M:%S')
        updated_str = doc.updated_at.strftime('%Y-%m-%d %H:%M:%S')

        related_lines = '\n'.join(
            f'- [[{r.title}]]: {r.reason}' for r in doc.related_docs
        )
        related_section = (
            f'\n### 🔗 연결된 지식 네트워크\n{related_lines}'
            if related_lines else ''
        )

        # summary/source_title 내 큰따옴표 이스케이프
        summary = doc.summary.replace('"', '\\"')
        source_title = doc.source_title.replace('"', '\\"')

        series_lines = ''
        if doc.series is not None:
            series_lines += f'series: "{doc.series}"\n'
        if doc.series_title is not None:
            series_lines += f'series_title: "{doc.series_title}"\n'
        if doc.series_order is not None:
            series_lines += f'series_order: {doc.series_order}\n'

        doc_type_lines = ''
        if doc.document_type:
            doc_type_lines += f'document_type: "{doc.document_type}"\n'
        if doc.paper_meta:
            pm = doc.paper_meta
            authors = pm.get("authors") or []
            if authors:
                authors_yaml = '[' + ', '.join(f'"{a}"' for a in authors) + ']'
                doc_type_lines += f'authors: {authors_yaml}\n'
            if pm.get("doi"):
                doc_type_lines += f'doi: "{pm["doi"]}"\n'
            if pm.get("published_year") is not None:
                doc_type_lines += f'published_year: {pm["published_year"]}\n'
            if pm.get("venue"):
                doc_type_lines += f'venue: "{pm["venue"]}"\n'

        return (
            f'---\n'
            f'url: "{doc.url}"\n'
            f'collected_at: "{collected_str}"\n'
            f'updated_at: "{updated_str}"\n'
            f'category: "{doc.category}"\n'
            f'tags: {tags_yaml}\n'
            f'summary: "{summary}"\n'
            f'source_title: "{source_title}"\n'
            f'{series_lines}'
            f'{doc_type_lines}'
            f'---\n\n'
            f'# {doc.title}\n\n'
            f'{doc.refined_content}'
            f'{related_section}\n'
        )

    def _parse_markdown(self, content: str) -> DocumentRecord | None:
        parts = content.split('---', 2)
        if len(parts) < 3:
            return None

        try:
            fm: dict = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            return None

        body = parts[2].strip()

        # # 제목 추출
        title = ''
        body_start = 0
        for i, line in enumerate(body.split('\n')):
            if line.startswith('# '):
                title = line[2:].strip()
                body_start = i + 1
                break
        body_text = '\n'.join(body.split('\n')[body_start:]).strip()

        # 연관 문서 섹션 파싱
        related_docs: list[RelatedDoc] = []
        if '### 🔗 연결된 지식 네트워크' in body_text:
            main, related_raw = body_text.split('### 🔗 연결된 지식 네트워크', 1)
            refined_content = main.strip()
            for line in related_raw.strip().split('\n'):
                m = _RELATED_LINE.match(line.strip())
                if m:
                    related_docs.append(RelatedDoc(title=m.group(1), reason=m.group(2)))
        else:
            refined_content = body_text

        # tags: YAML list 또는 콤마 문자열 모두 허용
        tags = fm.get('tags', [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',') if t.strip()]

        def _parse_dt(val: object) -> datetime:
            if isinstance(val, datetime):
                return val
            return datetime.strptime(str(val), '%Y-%m-%d %H:%M:%S')

        # paper_meta 복원
        paper_meta: dict | None = None
        if fm.get('document_type') == 'paper' or fm.get('authors') or fm.get('doi'):
            authors_raw = fm.get('authors') or []
            doi = fm.get('doi') or None
            year = fm.get('published_year') or None
            venue = fm.get('venue') or None
            if authors_raw or doi or year or venue:
                paper_meta = {
                    'authors': list(authors_raw) if authors_raw else [],
                    'doi': doi,
                    'published_year': year,
                    'venue': venue,
                }

        return DocumentRecord(
            url=fm.get('url', ''),
            title=title,
            source_title=fm.get('source_title', ''),
            refined_content=refined_content,
            summary=fm.get('summary', ''),
            tags=tags,
            category=fm.get('category', ''),
            related_docs=related_docs,
            collected_at=_parse_dt(fm['collected_at']),
            updated_at=_parse_dt(fm['updated_at']),
            series=fm.get('series') or None,
            series_title=fm.get('series_title') or None,
            series_order=fm.get('series_order'),
            document_type=fm.get('document_type') or None,
            paper_meta=paper_meta,
        )

    def _find_file(self, title: str) -> Path | None:
        """볼트 전체를 재귀 탐색하여 제목에 해당하는 파일을 반환한다."""
        filename = _sanitize_filename(title)
        matches = list(self._vault_path.rglob(filename))
        if matches:
            return matches[0]

        base = filename.removesuffix('.md')
        suffix_matches = sorted(self._vault_path.rglob(f'{base}_*.md'))
        return suffix_matches[0] if suffix_matches else None

    async def add_backlink(self, target_title: str, new_title: str, reason: str) -> None:
        """
        target_title 문서에 [[new_title]]: reason backlink를 추가한다.
        파일이 없으면 스킵. 이미 동일 backlink가 있으면 중복 추가하지 않는다.
        """
        async with self._lock:
            file_path = self._find_file(target_title)
            if file_path is None:
                return

            content = await asyncio.to_thread(_read_file, file_path)

            if f'[[{new_title}]]' in content:
                return

            section_header = '### 🔗 연결된 지식 네트워크'
            new_line = f'- [[{new_title}]]: {reason}'

            if section_header in content:
                content = content.rstrip('\n') + f'\n{new_line}\n'
            else:
                content = content.rstrip('\n') + f'\n\n{section_header}\n{new_line}\n'

            await asyncio.to_thread(_write_file, file_path, content)
            log.info("obsidian_backlink_added", target=target_title, source=new_title)

    async def save(self, doc: DocumentRecord) -> str:
        """
        마크다운 파일 생성. series에 따라 하위 디렉토리로 분류한다.
        - series 있음: {vault}/{series}/{file}.md
        - series 없음: {vault}/unsorted/{file}.md
        파일명 충돌 시 타임스탬프 서픽스 추가. 상대 경로 반환.
        """
        async with self._lock:
            series_dir = doc.series if doc.series else "unsorted"
            dir_path = self._vault_path / series_dir
            file_path = dir_path / _sanitize_filename(doc.title)

            if file_path.exists():
                suffix = f'_{doc.collected_at.strftime("%Y%m%d%H%M%S")}'
                file_path = dir_path / _sanitize_filename(doc.title, suffix=suffix)

            content = self._render_markdown(doc)
            await asyncio.to_thread(_write_file, file_path, content)

            relative = file_path.relative_to(self._vault_path).as_posix()
            log.info("obsidian_saved", title=doc.title, file_path=relative)
            return relative

    async def get(self, title: str) -> DocumentRecord | None:
        """파일을 읽어 DocumentRecord로 반환한다."""
        file_path = self._find_file(title)
        if file_path is None:
            return None

        content = await asyncio.to_thread(_read_file, file_path)
        return self._parse_markdown(content)

    async def exists_by_url(self, url: str) -> bool:
        raise NotImplementedError(
            'exists_by_url은 CompositeRepository를 통해 ChromaRepository에 위임한다.'
        )

    async def search(self, query: str, limit: int = 5) -> list[dict]:
        raise NotImplementedError(
            'search는 CompositeRepository를 통해 ChromaRepository에 위임한다.'
        )
