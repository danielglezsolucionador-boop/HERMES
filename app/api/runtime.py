import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_session
from app.models.task import Task
from app.services.operational_health import build_operational_health
from app.services.runtime_status import runtime_status as runner_runtime_status

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
        doing = counts.get("doing", 0)
        review = counts.get("review", 0)
        running_legacy = counts.get("running", 0)
        pending = counts.get("pending", 0)
        ai_metrics = runner_runtime_status.ai_metrics()
        telegram_metrics = runner_runtime_status.telegram_metrics()
        operational_health = await build_operational_health(session, counts)

        return {
            "status": "online",
            "uptime": "active",
            "tasks": {
                "total": total,
                "done": done,
                "failed": failed,
                "doing": doing,
                "review": review,
                "pending": pending,
                "running_legacy": running_legacy,
            },
            "runner": runner_runtime_status.to_dict(),
            "ai": ai_metrics,
            "telegram": telegram_metrics,
            "operational_health": operational_health,
            "operational_risks": operational_health.get("risks", []),
            "telegram_messages_processed": telegram_metrics["telegram_messages_processed"],
            "pipeline_avg_ms": ai_metrics["avg_ai_duration_ms"],
            "provider_avg_ms": ai_metrics["avg_ai_provider_duration_ms"],
            "db_context_avg_ms": ai_metrics["avg_ai_context_build_ms"],
        }
    except Exception as exc:
        logger.error("runtime/status error: %s", exc)
        return {"status": "degraded", "error": str(exc)}
