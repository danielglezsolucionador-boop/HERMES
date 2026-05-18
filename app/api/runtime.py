import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_session
from app.models.task import Task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.get("/status")
async def runtime_status(session: AsyncSession = Depends(get_session)):
    try:
        # Conteos por status
        result = await session.execute(
            select(Task.status, func.count(Task.id)).group_by(Task.status)
        )
        counts = {row[0]: row[1] for row in result.all()}

        total = sum(counts.values())
        done = counts.get("done", 0)
        failed = counts.get("failed", 0)
        running = counts.get("running", 0)
        pending = counts.get("pending", 0)

        return {
            "status": "online",
            "uptime": "active",
            "tasks": {
                "total": total,
                "done": done,
                "failed": failed,
                "running": running,
                "pending": pending,
            },
            "ai": {
                "provider": "openrouter",
                "model": "default",
                "requests": 0,
            },
            "pipeline_avg_ms": 0,
            "provider_avg_ms": 0,
            "db_context_avg_ms": 0,
        }
    except Exception as exc:
        logger.error("runtime/status error: %s", exc)
        return {"status": "degraded", "error": str(exc)}