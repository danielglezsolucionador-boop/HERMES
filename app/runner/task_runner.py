"""
Runner loop for Hermes.
Architecture: Task -> Runner -> Executor -> PostgreSQL.
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.db.engine import AsyncSessionLocal
from app.models.task import Task
from app.runner.executors import execute_task
from app.schemas.task import TaskStatus
from app.services.runtime_status import runtime_status

logger = logging.getLogger(__name__)

POLL_INTERVAL = 5


def _now():
    return datetime.now(timezone.utc)


async def _claim_next_pending() -> Task | None:
    """Claim the oldest pending task and mark it doing."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(Task)
                .where(Task.status == TaskStatus.pending.value)
                .order_by(Task.created_at.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            task = result.scalar_one_or_none()
            if task is None:
                return None

            task.status = TaskStatus.doing.value
            task.started_at = _now()
            task.completed_at = None
            task.error = None

        await session.refresh(task)
        logger.info("runner: claimed task_id=%s title=%s", task.id, task.title)
        return task


async def _persist_success(task_id, result: dict) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Task)
            .where(Task.id == task_id)
            .values(
                status=TaskStatus.done.value,
                result=result,
                error=None,
                completed_at=_now(),
            )
        )
        await session.commit()
    logger.info("runner: task_id=%s done", task_id)


async def _persist_failure(task: Task, error: str) -> None:
    retry_count = task.retry_count or 0
    max_retries = task.max_retries or 0
    should_retry = retry_count < max_retries

    values = {
        "error": error,
        "completed_at": _now(),
    }
    if should_retry:
        values.update(
            {
                "status": TaskStatus.pending.value,
                "retry_count": retry_count + 1,
                "last_retry_at": _now(),
            }
        )
        log_message = "runner: task_id=%s requeued retry=%s/%s error=%s"
        log_args = (task.id, retry_count + 1, max_retries, error)
    else:
        values["status"] = TaskStatus.failed.value
        log_message = "runner: task_id=%s failed retries=%s/%s error=%s"
        log_args = (task.id, retry_count, max_retries, error)

    async with AsyncSessionLocal() as session:
        await session.execute(update(Task).where(Task.id == task.id).values(**values))
        await session.commit()

    logger.warning(log_message, *log_args)


async def recovery_scan() -> dict:
    """Report tasks left in doing after a restart without mutating them."""
    logger.info("runner: recovery_scan started")
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Task)
                .where(Task.status == TaskStatus.doing.value)
                .order_by(Task.started_at.asc().nullsfirst())
                .limit(100)
            )
            tasks = list(result.scalars().all())
    except Exception as exc:
        logger.error("runner: recovery_scan failed error=%s", exc)
        return {"ok": False, "error": str(exc), "doing": 0}

    if tasks:
        logger.warning("runner: recovery_scan found doing_tasks=%d", len(tasks))
        for task in tasks:
            logger.warning("runner: doing task_id=%s title=%s", task.id, task.title)
    else:
        logger.info("runner: recovery_scan no doing tasks")

    return {"ok": True, "doing": len(tasks)}


async def run_once() -> bool:
    """Process at most one pending task. Returns True when a task was processed."""
    runtime_status.mark_loop()
    task = await _claim_next_pending()
    if task is None:
        return False

    runtime_status.mark_task_started(str(task.id), task.title)
    try:
        result = await execute_task(task)
        await _persist_success(task.id, result)
        runtime_status.mark_task_done()
    except Exception as exc:
        error = str(exc)
        logger.error("runner: executor failed task_id=%s error=%s", task.id, error)
        await _persist_failure(task, error)
        runtime_status.mark_task_failed()

    return True


async def runner_loop() -> None:
    """Continuous single-process runner loop."""
    runtime_status.mark_started()
    logger.info("runner: loop started poll_interval=%s", POLL_INTERVAL)
    while True:
        try:
            processed = await run_once()
            if not processed:
                logger.debug("runner: no pending tasks")
        except asyncio.CancelledError:
            logger.info("runner: loop cancelled")
            raise
        except Exception as exc:
            logger.error("runner: loop error survived error=%s", exc)

        await asyncio.sleep(POLL_INTERVAL)
