# docs/temp_dir.md — .temp/ 임시 디렉토리 구조

---

## 개요

`.temp/` 디렉토리는 프로세스 재시작 시 소실되는 메모리 큐의 한계를 보완하기 위해 도입된 **영속 임시 저장소**다. 영속 큐, 임시 파일, 처리 중 스냅샷 등 휘발성을 허용하지 않아야 하는 모든 중간 데이터를 이 디렉토리에 집중 관리한다.

---

## 디렉토리 구조

```
.temp/
├── failed_tasks.db        # SQLite — Ollama 실패 작업 영속 큐 (모듈 C)
├── pending_analysis.db    # SQLite — Worker-2 처리 대기 (선택적 영속화)
└── raw_cache/             # 원시 본문 임시 파일 (처리 완료 후 자동 삭제)
    └── {request_id}.json
```

---

## failed_tasks.db 스키마

```sql
CREATE TABLE IF NOT EXISTS failed_tasks (
    id          TEXT PRIMARY KEY,   -- request_id (UUID)
    url         TEXT NOT NULL,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'pending',  -- pending | retrying | escalated
    created_at  TEXT NOT NULL,
    last_tried  TEXT
);
```

---

## 상태 전이

```
pending → retrying (재시도 중)
retrying → pending (재시도 간격 대기)
retrying → escalated (3회 초과 → 상용 LLM에 위임)
```

---

## 구현 위치

```
backend/temp/
└── queue_db.py    # aiosqlite 기반 CRUD
```

```python
# backend/temp/queue_db.py

import aiosqlite
from pathlib import Path
from backend.config import settings

DB_PATH = Path(settings.TEMP_DIR) / "failed_tasks.db"

async def init_queue_db() -> None:
    """테이블 생성. lifespan에서 호출."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS failed_tasks (
                id          TEXT PRIMARY KEY,
                url         TEXT NOT NULL,
                title       TEXT NOT NULL,
                content     TEXT NOT NULL,
                timestamp   TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                status      TEXT DEFAULT 'pending',
                created_at  TEXT NOT NULL,
                last_tried  TEXT
            )
        """)
        await db.commit()

async def save_failed(request_id: str, request: dict) -> None:
    """실패 작업 저장."""
    ...

async def get_pending(limit: int = 50) -> list[dict]:
    """status='pending' 작업 조회."""
    ...

async def update_status(request_id: str, status: str) -> None:
    """상태 업데이트."""
    ...

async def increment_retry(request_id: str) -> int:
    """retry_count 증가 후 반환."""
    ...

async def reload_failed_tasks(queue: asyncio.Queue) -> None:
    """서버 재시작 시 pending 항목을 ingestion_queue에 재적재."""
    pending = await get_pending()
    for task in pending:
        await queue.put(CollectRequest(**task))
```

---

## 운영 규칙

- `.temp/`는 `.gitignore`에 반드시 포함. 버전 관리 제외.
- 백엔드 startup 시 자동 생성 (존재하지 않을 경우).
- `status='escalated'` 항목은 7일 후 자동 정리 (선택적 cron).
- `raw_cache/`는 Worker-2 처리 완료 후 즉시 삭제. 최대 보존: 24시간.
