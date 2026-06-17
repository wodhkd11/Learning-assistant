# 모듈 E — Local-First 저장소 계층 (Obsidian Vault I/O)

**담당 코더:** 코더 B
**브랜치:** `feat/module-E-X-storage`
**담당 파일:** `backend/storage/obsidian.py`

---

## 목표

파일 시스템을 영속성 계층으로 활용해 Obsidian Graph View에서 즉시 시각화 가능한 마크다운 파일을 생성한다.

---

## 세부 요구사항

- 저장 경로: `VAULT_PATH` 환경변수 우선. 미설정 시 프로젝트 루트의 `obsidian_vault/` 사용
- **파일명 규칙**: 페이지 타이틀에서 특수문자 `/ \ : * ? " < > |` 제거. 중복 시 언더스코어 + 타임스탬프 서픽스 (예: `FastAPI_가이드_20260611.md`)
- YAML Front-matter 자동 생성: `url`, `collected_at`, `updated_at`, `tags`, `category`, `summary`, `source_title` 필드 필수 포함
- 연관 관계는 마크다운 하단 `[[문서 제목]]` 문법으로 기록 → Obsidian Graph View 자동 시각화
- **중복 URL 감지**: `ChromaRepository.exists_by_url()`으로 확인 (파일 파싱 없음). 중복 시 `updated_at` 갱신
- 동시 쓰기 보호: `asyncio.Lock` 적용
- 파일 경로에 한글 포함 가능. `pathlib.Path` 사용 (`os.path` 대체)

---

## 마크다운 파일 템플릿

```markdown
---
url: "https://example.com/article"
collected_at: "2026-06-11 17:00:00"
updated_at: "2026-06-11 17:00:00"
category: "AI/Software Engineering"
tags: [fastapi, async, python]
summary: "FastAPI 비동기 아키텍처 설계 방법을 다룬 기술 블로그"
source_title: "원본 페이지 제목"
---

# FastAPI 비동기 아키텍처 설계

[LLM이 정제·요약한 본문 내용]

### 🔗 연결된 지식 네트워크
- [[관련 문서 제목]]: 연관 이유 서술
```

---

## 파일명 정제 함수 예시

```python
import re
from pathlib import Path

def sanitize_filename(title: str, suffix: str = "") -> str:
    # 특수문자 제거
    clean = re.sub(r'[/\\:*?"<>|]', '', title)
    # 공백 → 언더스코어
    clean = clean.replace(' ', '_')
    # 길이 제한 (255자)
    clean = clean[:200]
    filename = f"{clean}{suffix}.md" if suffix else f"{clean}.md"
    return filename
```

---

## 구현 인터페이스

`docs/interfaces.md` 섹션 1의 `BaseRepository` 구현체.

```python
class ObsidianRepository(BaseRepository):
    _lock = asyncio.Lock()

    async def save(self, doc: DocumentRecord) -> str:
        """마크다운 파일 생성. 중복 시 파일명에 타임스탬프 추가. file_path 반환."""
        async with self._lock:
            ...

    async def get(self, title: str) -> DocumentRecord | None:
        """파일 읽기. YAML 파싱하여 DocumentRecord 반환."""
        ...

    async def exists_by_url(self, url: str) -> bool:
        """사용하지 않음. CompositeRepository가 chroma에 위임."""
        raise NotImplementedError
```
