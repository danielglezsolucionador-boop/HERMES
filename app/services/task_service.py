"""
Task service for Telegram task commands.
Keeps Telegram handlers away from direct database access.
"""
import logging
from uuid import UUID

from app.db.engine import AsyncSessionLocal
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskStatus

logger = logging.getLogger(__name__)


VALID_TASK_STATUSES = {status.value for status in TaskStatus}


async def get_tasks(status: str | None = None, limit: int = 10):
    """Return recent tasks, optionally filtered by official task status."""
    if status is not None and status not in VALID_TASK_STATUSES:
        raise ValueError(f"invalid status: {status}")

    async with AsyncSessionLocal() as session:
        repo = TaskRepository(session)
        tasks, total = await repo.list_tasks(limit=limit, offset=0, status=status)
        logger.debug("task_service.get_tasks status=%s total=%d", status, total)
        return tasks


async def get_task(task_id: str):
    """Return one task by UUID string, or None if it does not exist."""
    try:
        uid = UUID(task_id)
    except (ValueError, AttributeError):
        logger.warning("task_service.get_task invalid_uuid=%s", task_id)
        return None

    async with AsyncSessionLocal() as session:
        repo = TaskRepository(session)
        task = await repo.get_task(uid)
        logger.debug("task_service.get_task id=%s found=%s", task_id, task is not None)
        return task
