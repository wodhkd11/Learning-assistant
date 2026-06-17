# CLAUDE.md — KALF 프로젝트 Claude Code 작업 규칙

> 이 파일은 모든 Claude Code 인스턴스가 작업 시작 전 **반드시** 읽어야 하는 규칙서다.
> 규칙을 어기면 다른 코더의 작업과 충돌이 발생한다.

---

## 필독 순서

작업 시작 전 아래 순서대로 반드시 읽는다.

1. `SPEC.md` — 전체 시스템 개요 및 플로우
2. `docs/interfaces.md` — 모듈 간 인터페이스 계약 (**절대 어기지 말 것**)
3. `docs/schemas.md` — 전체 Pydantic 스키마 정의
4. 담당 `docs/module_*.md` — 자신이 담당하는 모듈 세부 요구사항

---

## 절대 규칙 (위반 시 PR 반려)

### 비동기 처리
- `FastAPI BackgroundTasks` **사용 금지**. `asyncio.Queue`만 사용한다.
- 라우터에서 `await ingestion_queue.put(request)` 호출 후 즉시 200 OK 반환.
- Ollama/외부 API 호출은 반드시 `async httpx.AsyncClient` 사용 (`requests` 라이브러리 금지).

### 저장소 계층
- 문서 저장은 반드시 `CompositeRepository.save()`만 호출한다.
- `ObsidianRepository`, `ChromaRepository`를 직접 호출하는 코드를 상위 레이어(라우터, 워커)에 작성하지 않는다.
- 파일 시스템 직접 파싱으로 문서 목록/메타데이터를 조회하는 코드 **작성 금지**.
- 중복 URL 확인은 `ChromaRepository.exists_by_url()` 사용. 파일 파싱으로 확인하는 코드 금지.

### ChromaDB
- `chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)` 사용. 인메모리 클라이언트 금지.
- 컬렉션 생성은 `get_or_create_collection()` 사용.
- `metadata`의 `tags` 필드는 **콤마 구분 문자열**로 저장. `list` 타입은 ChromaDB가 거부함.
  - 저장: `",".join(tags)` → `"fastapi,async,python"`
  - 조회: `.split(",")` → `["fastapi", "async", "python"]`
- 모든 파일 경로 조회는 ChromaDB metadata에서 가져올 것.

### 파일 시스템
- 모든 파일 경로는 `pathlib.Path` 사용 (`os.path` 대체).
- 파일명 특수문자 `/ \ : * ? " < > |` 제거 로직 필수.
- 파일 저장 시 `asyncio.Lock` 적용 (CompositeRepository 내부에서 처리).

### 인터페이스
- `docs/interfaces.md`에 정의된 함수 시그니처·스키마를 **임의로 변경하지 않는다**.
- 변경이 필요한 경우: 오케스트레이터에게 먼저 요청 → 승인 후 `docs/interfaces.md` 업데이트 → 구현.
- 다른 코더 담당 파일을 직접 수정하지 않는다.

---

## 코딩 스타일

```python
# 타입 힌트 필수
async def analyze(self, content: str, vault_context: list[dict]) -> AnalysisResult:
    ...

# 환경변수는 반드시 config.py의 settings 객체를 통해 접근
from backend.config import settings
path = Path(settings.VAULT_PATH)

# 로깅은 structlog 사용
import structlog
log = structlog.get_logger()
log.info("event_name", request_id=request_id, url=url, latency_ms=elapsed)
```

---

## 테스트 규칙

- 담당 모듈의 단위 테스트를 `tests/test_{module_name}.py`에 작성한다.
- 외부 API(Ollama, Claude, Gemini)는 `unittest.mock`으로 모킹한다.
- ChromaDB는 테스트 시 임시 경로의 PersistentClient 사용 (`tmp_path` fixture 활용).
- 테스트 실행: `pytest tests/ -v`

---

## Git 브랜치 규칙

| 코더 | 브랜치명 |
|------|---------|
| 코더 A | `feat/module-A-B` |
| 코더 B | `feat/module-E-X-storage` |
| 코더 C | `feat/module-C-D-llm` |
| 코더 D | `feat/module-F-G` |

- 커밋 메시지: `feat(module-X): 설명` / `fix(module-X): 설명` / `test(module-X): 설명`
- PR 전 `pytest tests/` 통과 필수.

---

## 의존성 순서 (작업 시작 가능 시점)

```
코더 A  ─────────────────────────────────────────── 즉시 시작
코더 B  ── (코더 A의 config.py 머지 후) ────────── 시작
코더 C  ── (docs/interfaces.md 확정 후) ─────────── 시작
코더 D  ── (코더 B의 chroma.py 인터페이스 머지 후) ─ 시작
```

---

## .temp/ 디렉토리 규칙

- `.temp/`는 `.gitignore`에 반드시 포함되어 있다. 커밋하지 않는다.
- `failed_tasks.db` 스키마는 `docs/temp_dir.md` 참고.
- SQLite 접근은 `aiosqlite` 비동기 라이브러리 사용.

---

## 백엔드 Startup 순서 (lifespan)

`backend/main.py`의 `lifespan` 이벤트에서 **반드시 아래 순서를 준수**한다.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. .temp/ 디렉토리 초기화
    # 2. SQLite failed_tasks.db 초기화
    # 3. ChromaDB PersistentClient 초기화
    # 4. Obsidian 볼트 경로 확인/생성
    # 5. asyncio.Queue 생성 및 Worker-1, Worker-2 태스크 시작
    # 6. failed_tasks.db에서 pending 항목 자동 재적재
    # 7. Ollama 연결 상태 확인 (실패해도 서버는 기동)
    yield
    # shutdown: 워커 태스크 정리
```

---

## 모르는 것이 있을 때

1. 먼저 `docs/interfaces.md`에 정의가 있는지 확인한다.
2. 없으면 `TODO.md`에 `[BLOCKER] 코더X: 질문 내용`을 추가한다.
3. 오케스트레이터가 확인 후 답변 및 인터페이스 업데이트를 처리한다.
