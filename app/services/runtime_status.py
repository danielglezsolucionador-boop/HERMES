"""
In-memory runtime status for the local runner process.
PostgreSQL remains the source of truth for tasks.
"""
from datetime import datetime, timezone


class RuntimeStatus:
    def __init__(self):
        self.runner_started_at: datetime | None = None
        self.last_loop_at: datetime | None = None
        self.last_task_started_at: datetime | None = None
        self.last_task_completed_at: datetime | None = None
        self.current_task_id: str | None = None
        self.current_task_title: str | None = None
        self.total_processed = 0
        self.total_success = 0
        self.total_failed = 0
        self.runner_alive = False
        self.total_ai_requests = 0
        self.ai_success_requests = 0
        self.ai_failed_requests = 0
        self.total_ai_duration_ms = 0
        self.total_ai_provider_duration_ms = 0
        self.total_ai_context_build_ms = 0
        self.last_ai_provider: str | None = None
        self.last_ai_model: str | None = None
        self.telegram_messages_processed = 0

    def mark_started(self) -> None:
        self.runner_started_at = datetime.now(timezone.utc)
        self.runner_alive = True

    def mark_loop(self) -> None:
        self.last_loop_at = datetime.now(timezone.utc)

    def mark_task_started(self, task_id: str, task_title: str) -> None:
        self.current_task_id = task_id
        self.current_task_title = task_title
        self.last_task_started_at = datetime.now(timezone.utc)

    def mark_task_done(self) -> None:
        self.last_task_completed_at = datetime.now(timezone.utc)
        self.current_task_id = None
        self.current_task_title = None
        self.total_processed += 1
        self.total_success += 1

    def mark_task_failed(self) -> None:
        self.last_task_completed_at = datetime.now(timezone.utc)
        self.current_task_id = None
        self.current_task_title = None
        self.total_processed += 1
        self.total_failed += 1

    def mark_ai_request(
        self,
        success: bool,
        duration_ms: int,
        provider: str | None = None,
        model: str | None = None,
        provider_ms: int = 0,
        context_build_ms: int = 0,
    ) -> None:
        safe_duration = max(0, int(duration_ms or 0))
        safe_provider_ms = max(0, int(provider_ms or 0))
        safe_context_ms = max(0, int(context_build_ms or 0))

        self.total_ai_requests += 1
        if success:
            self.ai_success_requests += 1
        else:
            self.ai_failed_requests += 1

        self.total_ai_duration_ms += safe_duration
        self.total_ai_provider_duration_ms += safe_provider_ms
        self.total_ai_context_build_ms += safe_context_ms
        self.last_ai_provider = provider
        self.last_ai_model = model

    def mark_telegram_message_processed(self) -> None:
        self.telegram_messages_processed += 1

    def ai_metrics(self) -> dict:
        avg_duration = 0
        avg_provider = 0
        avg_context = 0
        if self.total_ai_requests:
            avg_duration = int(self.total_ai_duration_ms / self.total_ai_requests)
            avg_provider = int(self.total_ai_provider_duration_ms / self.total_ai_requests)
            avg_context = int(self.total_ai_context_build_ms / self.total_ai_requests)

        return {
            "total_ai_requests": self.total_ai_requests,
            "ai_success_requests": self.ai_success_requests,
            "ai_failed_requests": self.ai_failed_requests,
            "avg_ai_duration_ms": avg_duration,
            "avg_ai_provider_duration_ms": avg_provider,
            "avg_ai_context_build_ms": avg_context,
            "last_ai_provider": self.last_ai_provider,
            "last_ai_model": self.last_ai_model,
        }

    def telegram_metrics(self) -> dict:
        return {
            "telegram_messages_processed": self.telegram_messages_processed,
        }

    def health_status(self) -> str:
        if not self.runner_alive:
            return "offline"
        if self.last_loop_at is None:
            return "starting"
        age = (datetime.now(timezone.utc) - self.last_loop_at).total_seconds()
        if age > 30:
            return "degraded"
        return "healthy"

    def to_dict(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        data = {
            "runner_alive": self.runner_alive,
            "runner_status": self.health_status(),
            "runner_started_at": fmt(self.runner_started_at),
            "last_loop_at": fmt(self.last_loop_at),
            "last_task_started_at": fmt(self.last_task_started_at),
            "last_task_completed_at": fmt(self.last_task_completed_at),
            "current_task_id": self.current_task_id,
            "current_task_title": self.current_task_title,
            "total_processed": self.total_processed,
            "total_success": self.total_success,
            "total_failed": self.total_failed,
        }
        data.update(self.ai_metrics())
        data.update(self.telegram_metrics())
        return data


runtime_status = RuntimeStatus()
