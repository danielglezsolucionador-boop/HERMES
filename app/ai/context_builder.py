"""
Build safe operational context for AI providers.
The provider never queries PostgreSQL directly.
"""
import logging
import time
from datetime import datetime, timezone

from app.ai.context_isolation import MAX_CONTEXT_CHARS, safe_json_chars, sanitize_text
from app.db.engine import AsyncSessionLocal
from app.repositories.task_repository import TaskRepository
from app.services.runtime_status import runtime_status

logger = logging.getLogger(__name__)

MAX_TASKS_CONTEXT = 12


def _fmt(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def _task_summary(task) -> dict:
    return {
        "id": str(task.id),
        "title": sanitize_text(task.title),
        "description": sanitize_text(task.description),
        "status": task.status,
        "phase": task.phase,
        "error": sanitize_text(task.error) if task.error else None,
        "retry_count": task.retry_count,
        "created_at": _fmt(task.created_at),
        "updated_at": _fmt(task.updated_at),
    }


async def build_context() -> dict:
    start = time.monotonic()
    tasks = []
    incidents = []
    counts = {"pending": 0, "doing": 0, "review": 0, "done": 0, "failed": 0}

    try:
        async with AsyncSessionLocal() as session:
            repo = TaskRepository(session)
            for status, limit in [
                ("failed", 5),
                ("doing", 3),
                ("pending", 3),
                ("review", 2),
                ("done", 3),
            ]:
                rows, total = await repo.list_tasks(limit=limit, offset=0, status=status)
                counts[status] = total
                for task in rows:
                    tasks.append(_task_summary(task))
                    if task.status == "failed" and task.error:
                        incidents.append(
                            f"Task fallida: {sanitize_text(task.title)} - {sanitize_text(task.error)}"
                        )
    except Exception as exc:
        logger.error("context_builder: DB context error=%s", exc)
        incidents.append(f"Error consultando PostgreSQL: {sanitize_text(exc)}")

    tasks = tasks[:MAX_TASKS_CONTEXT]
    context = {
        "summary": (
            f"Runner: {runtime_status.health_status()} | "
            f"Pending: {counts['pending']} | Doing: {counts['doing']} | "
            f"Review: {counts['review']} | Failed: {counts['failed']}"
        ),
        "tasks": tasks,
        "incidents": incidents[:5],
        "runtime": runtime_status.to_dict(),
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "hermes",
            "context_version": "3.6",
            "runtime": runtime_status.health_status(),
        },
    }
    total_chars = safe_json_chars(context)
    context["_isolation"] = {
        "total_chars": total_chars,
        "truncated": total_chars > MAX_CONTEXT_CHARS,
        "redactions": 0,
    }
    context["_timing"] = {
        "build_ms": int((time.monotonic() - start) * 1000),
        "chars": total_chars,
    }
    logger.info(
        "context_builder: built tasks=%s incidents=%s chars=%s duration_ms=%s",
        len(tasks),
        len(context["incidents"]),
        context["_timing"]["chars"],
        context["_timing"]["build_ms"],
    )
    return context
