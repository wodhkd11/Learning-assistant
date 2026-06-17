import asyncio
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
import structlog

from backend.config import settings
from backend.schemas.document import CollectRequest

log = structlog.get_logger()

DB_PATH = Path(settings.TEMP_DIR) / "failed_tasks.db"


async def init_queue_db() -> None:
    """테이블 생성. lifespan에서 호출."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
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
    log.info("queue_db_initialized", path=str(DB_PATH))


async def save_failed(request_id: str, request: dict) -> None:
    """실패 작업 저장. 동일 id는 무시 (중복 삽입 방어)."""
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO failed_tasks
                (id, url, title, content, timestamp, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                request['url'],
                request['title'],
                request['content'],
                request['timestamp'],
                now,
            ),
        )
        await db.commit()
    log.info("task_saved_to_queue", request_id=request_id, url=request.get('url'))


async def get_pending(limit: int = 50) -> list[dict]:
    """status='pending' 작업 조회. 생성 순 정렬."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM failed_tasks WHERE status = 'pending' ORDER BY created_at LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def update_status(request_id: str, status: str) -> None:
    """상태 업데이트. last_tried를 현재 시각으로 갱신."""
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE failed_tasks SET status = ?, last_tried = ? WHERE id = ?",
            (status, now, request_id),
        )
        await db.commit()
    log.info("task_status_updated", request_id=request_id, status=status)


async def increment_retry(request_id: str) -> int:
    """retry_count 1 증가 후 갱신된 값을 반환한다."""
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE failed_tasks SET retry_count = retry_count + 1, last_tried = ? WHERE id = ?",
            (now, request_id),
        )
        await db.commit()
        async with db.execute(
            "SELECT retry_count FROM failed_tasks WHERE id = ?",
            (request_id,),
        ) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else 0


async def reload_failed_tasks(queue: asyncio.Queue) -> None:
    """서버 재시작 시 pending 항목을 ingestion_queue에 재적재."""
    pending = await get_pending()
    for task in pending:
        await queue.put(CollectRequest(
            url=task['url'],
            title=task['title'],
            content=task['content'],
            timestamp=task['timestamp'],
        ))
    if pending:
        log.info("failed_tasks_reloaded", count=len(pending))
