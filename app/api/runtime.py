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
        claimed = counts.get("claimed", 0)
        review = counts.get("review", 0)
        running_legacy = counts.get("running", 0)
        pending = counts.get("pending", 0)
        ai_metrics = runner_runtime_status.ai_metrics()
        telegram_metrics = runner_runtime_status.telegram_metrics()
        runtime_loop_metrics = runner_runtime_status.runtime_loop_metrics()
        polling_metrics = runner_runtime_status.polling_metrics()
        discovery_metrics = runner_runtime_status.discovery_metrics()
        claiming_metrics = runner_runtime_status.claiming_metrics()
        pickup_safety_metrics = runner_runtime_status.pickup_safety_metrics()
        execution_metrics = runner_runtime_status.execution_metrics()
        execution_safety_metrics = runner_runtime_status.execution_safety_metrics()
        provider_bridge_metrics = runner_runtime_status.provider_bridge_metrics()
        response_ingestion_metrics = runner_runtime_status.response_ingestion_metrics()
        response_validation_metrics = runner_runtime_status.response_validation_metrics()
        safety_metrics = runner_runtime_status.safety_metrics()
        operational_health = await build_operational_health(session, counts)

        return {
            "status": "online",
            "uptime": "active",
            "tasks": {
                "total": total,
                "done": done,
                "failed": failed,
                "doing": doing,
                "claimed": claimed,
                "review": review,
                "pending": pending,
                "running_legacy": running_legacy,
            },
            "runner": runner_runtime_status.to_dict(),
            "runtime_loop": runtime_loop_metrics,
            "polling": polling_metrics,
            "discovery": discovery_metrics,
            "claiming": claiming_metrics,
            "pickup_safety": pickup_safety_metrics,
            "execution": execution_metrics,
            "execution_safety": execution_safety_metrics,
            "provider_bridge": provider_bridge_metrics,
            "response_ingestion": response_ingestion_metrics,
            "response_validation": response_validation_metrics,
            "safety": safety_metrics,
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
