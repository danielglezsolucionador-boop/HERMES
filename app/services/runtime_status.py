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
        self.last_ai_error: str | None = None
        self.last_ai_request_at: datetime | None = None
        self.telegram_messages_processed = 0
        self.telegram_messages_total = 0
        self.telegram_messages_failed = 0
        self.telegram_last_message_at: datetime | None = None
        self.telegram_last_error: str | None = None
        self.runtime_loop_started_at: datetime | None = None
        self.runtime_loop_last_heartbeat_at: datetime | None = None
        self.runtime_loop_last_cycle_duration_ms = 0
        self.runtime_loop_iteration = 0
        self.runtime_loop_alive = False
        self.runtime_loop_state = "stopped"
        self.runtime_loop_stop_requested = False
        self.runtime_loop_stop_reason: str | None = None
        self.runtime_loop_interval_seconds = 0.0
        self.polling_started_at: datetime | None = None
        self.last_poll_time: datetime | None = None
        self.polling_iteration = 0
        self.tasks_detected = 0
        self.polling_status = "stopped"
        self.polling_interval_seconds = 0.0
        self.polling_last_duration_ms = 0
        self.polling_errors = 0
        self.polling_last_error: str | None = None
        self.discovery_started_at: datetime | None = None
        self.last_discovery_at: datetime | None = None
        self.discovery_iteration = 0
        self.discovery_status = "stopped"
        self.discovery_interval_seconds = 0.0
        self.discovery_last_duration_ms = 0
        self.discovery_errors = 0
        self.discovery_last_error: str | None = None
        self.discovered_tasks = 0
        self.discovery_limit = 0
        self.discovery_max_payload_bytes = 0
        self.discovery_query_timeout_seconds = 0.0
        self.discovery_ignored_count = 0
        self.discovery_ignored_reasons: dict[str, int] = {}
        self.discovery_filters: dict[str, str] = {}
        self.discovery_ordering: list[str] = []
        self.discovery_candidates: list[dict] = []
        self.claiming_started_at: datetime | None = None
        self.last_claiming_at: datetime | None = None
        self.claiming_iteration = 0
        self.claiming_enabled = False
        self.claiming_status = "stopped"
        self.claiming_interval_seconds = 0.0
        self.claiming_last_duration_ms = 0
        self.claiming_errors = 0
        self.claiming_last_error: str | None = None
        self.claims_attempted = 0
        self.claims_succeeded = 0
        self.claims_conflicted = 0
        self.claims_rejected = 0
        self.active_claims = 0
        self.stale_claims = 0
        self.max_concurrent_claims = 0
        self.max_attempts_per_cycle = 0
        self.max_task_attempts = 0
        self.min_claim_interval_seconds = 0.0
        self.stale_claim_after_seconds = 0
        self.max_stale_claims = 0
        self.claiming_runner_id: str | None = None
        self.claiming_runtime_id: str | None = None
        self.last_claimed_task: dict | None = None
        self.runtime_safe = True
        self.consecutive_errors = 0
        self.degraded_state = False
        self.safety_stop_reason: str | None = None
        self.safety_events: list[dict] = []
        self.safety_event_limit = 20

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
        error: str | None = None,
    ) -> None:
        safe_duration = max(0, int(duration_ms or 0))
        safe_provider_ms = max(0, int(provider_ms or 0))
        safe_context_ms = max(0, int(context_build_ms or 0))

        self.last_ai_request_at = datetime.now(timezone.utc)
        self.total_ai_requests += 1
        if success:
            self.ai_success_requests += 1
            self.last_ai_error = None
        else:
            self.ai_failed_requests += 1
            self.last_ai_error = error or "unknown_ai_error"

        self.total_ai_duration_ms += safe_duration
        self.total_ai_provider_duration_ms += safe_provider_ms
        self.total_ai_context_build_ms += safe_context_ms
        self.last_ai_provider = provider
        self.last_ai_model = model

    def mark_telegram_message_processed(self) -> None:
        self.mark_telegram_message(success=True)

    def mark_telegram_message(
        self,
        success: bool,
        error: str | None = None,
    ) -> None:
        self.telegram_messages_total += 1
        self.telegram_messages_processed += 1
        self.telegram_last_message_at = datetime.now(timezone.utc)
        if success:
            self.telegram_last_error = None
            return
        self.telegram_messages_failed += 1
        self.telegram_last_error = error or "unknown_telegram_error"

    def mark_runtime_loop_started(self, interval_seconds: float) -> None:
        self.runtime_loop_started_at = datetime.now(timezone.utc)
        self.runtime_loop_last_heartbeat_at = None
        self.runtime_loop_last_cycle_duration_ms = 0
        self.runtime_loop_iteration = 0
        self.runtime_loop_alive = True
        self.runtime_loop_state = "active"
        self.runtime_loop_stop_requested = False
        self.runtime_loop_stop_reason = None
        self.runtime_loop_interval_seconds = interval_seconds
        self.runtime_safe = True
        self.consecutive_errors = 0
        self.degraded_state = False
        self.safety_stop_reason = None
        self.safety_events = []

    def mark_runtime_loop_heartbeat(
        self,
        state: str = "active",
        cycle_duration_ms: int = 0,
    ) -> None:
        self.runtime_loop_last_heartbeat_at = datetime.now(timezone.utc)
        self.runtime_loop_last_cycle_duration_ms = max(0, int(cycle_duration_ms or 0))
        self.runtime_loop_iteration += 1
        self.runtime_loop_alive = True
        self.runtime_loop_state = state
        self.runtime_loop_stop_requested = False

    def mark_runtime_loop_paused(self) -> None:
        self.runtime_loop_last_heartbeat_at = datetime.now(timezone.utc)
        self.runtime_loop_alive = True
        self.runtime_loop_state = "paused"

    def request_runtime_loop_stop(self, reason: str = "stop_requested") -> None:
        self.runtime_loop_stop_requested = True
        self.runtime_loop_stop_reason = reason

    def mark_runtime_loop_stopped(self, reason: str = "stopped") -> None:
        self.runtime_loop_alive = False
        self.runtime_loop_state = "stopped"
        self.runtime_loop_stop_requested = True
        self.runtime_loop_stop_reason = reason
        self.polling_status = "stopped"
        self.discovery_status = "stopped"
        self.claiming_status = "stopped"

    def configure_safety_event_limit(self, limit: int) -> None:
        self.safety_event_limit = max(1, int(limit or 1))
        self.safety_events = self.safety_events[-self.safety_event_limit :]

    def record_safety_event(
        self,
        event: str,
        severity: str = "info",
        detail: str | None = None,
    ) -> None:
        payload = {
            "at": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "severity": severity,
            "detail": detail,
            "consecutive_errors": self.consecutive_errors,
        }
        self.safety_events.append(payload)
        self.safety_events = self.safety_events[-self.safety_event_limit :]

    def mark_runtime_loop_cycle_success(self) -> None:
        if self.consecutive_errors:
            self.record_safety_event(
                "runtime_recovered",
                severity="info",
                detail="cycle_completed_after_error",
            )
        self.consecutive_errors = 0
        if self.runtime_safe:
            self.degraded_state = False

    def mark_runtime_loop_error(
        self,
        error: str,
        degraded_threshold: int,
        max_consecutive_errors: int,
    ) -> dict:
        self.consecutive_errors += 1
        detail = error or "unknown_runtime_loop_error"
        degraded_started = False
        should_stop = False
        if self.consecutive_errors >= degraded_threshold and not self.degraded_state:
            self.degraded_state = True
            degraded_started = True
            self.record_safety_event(
                "runtime_degraded",
                severity="warning",
                detail=detail,
            )
        if self.consecutive_errors >= max_consecutive_errors:
            self.runtime_safe = False
            self.safety_stop_reason = "max_consecutive_errors"
            should_stop = True
            self.record_safety_event(
                "runtime_safety_stop",
                severity="critical",
                detail=detail,
            )
        return {
            "degraded_started": degraded_started,
            "should_stop": should_stop,
        }

    def mark_polling_started(self, interval_seconds: float) -> None:
        self.polling_started_at = datetime.now(timezone.utc)
        self.polling_status = "active"
        self.polling_interval_seconds = interval_seconds
        self.polling_last_error = None

    def mark_polling_completed(
        self,
        tasks_detected: int,
        duration_ms: int,
    ) -> None:
        self.last_poll_time = datetime.now(timezone.utc)
        self.polling_iteration += 1
        self.tasks_detected = max(0, int(tasks_detected or 0))
        self.polling_last_duration_ms = max(0, int(duration_ms or 0))
        self.polling_status = (
            "tasks_detected" if self.tasks_detected > 0 else "idle"
        )
        self.polling_last_error = None

    def mark_polling_error(self, error: str, duration_ms: int = 0) -> None:
        self.last_poll_time = datetime.now(timezone.utc)
        self.polling_iteration += 1
        self.polling_last_duration_ms = max(0, int(duration_ms or 0))
        self.polling_errors += 1
        self.polling_status = "error"
        self.polling_last_error = error or "unknown_polling_error"

    def mark_task_discovery_started(self, interval_seconds: float) -> None:
        self.discovery_started_at = datetime.now(timezone.utc)
        self.discovery_status = "active"
        self.discovery_interval_seconds = interval_seconds
        self.discovery_last_error = None

    def mark_task_discovery_completed(self, result: dict) -> None:
        self.last_discovery_at = datetime.now(timezone.utc)
        self.discovery_iteration += 1
        self.discovery_status = result.get("status") or "unknown"
        self.discovered_tasks = max(0, int(result.get("discovered_count") or 0))
        self.discovery_last_duration_ms = max(0, int(result.get("duration_ms") or 0))
        self.discovery_limit = max(0, int(result.get("limit") or 0))
        self.discovery_max_payload_bytes = max(
            0,
            int(result.get("max_payload_bytes") or 0),
        )
        self.discovery_query_timeout_seconds = max(
            0.0,
            float(result.get("query_timeout_seconds") or 0.0),
        )
        self.discovery_ignored_count = max(
            0,
            int(result.get("ignored_count") or 0),
        )
        ignored_reasons = result.get("ignored_reasons") or {}
        self.discovery_ignored_reasons = {
            str(reason): max(0, int(count or 0))
            for reason, count in ignored_reasons.items()
        }
        self.discovery_filters = {
            str(name): str(value)
            for name, value in (result.get("filters") or {}).items()
        }
        self.discovery_ordering = [
            str(ordering) for ordering in (result.get("ordering") or [])
        ]
        self.discovery_candidates = list(result.get("candidates") or [])
        self.discovery_last_error = None

    def mark_task_discovery_error(self, error: str, duration_ms: int = 0) -> None:
        self.last_discovery_at = datetime.now(timezone.utc)
        self.discovery_iteration += 1
        self.discovery_last_duration_ms = max(0, int(duration_ms or 0))
        self.discovery_errors += 1
        self.discovery_status = "error"
        self.discovery_last_error = error or "unknown_discovery_error"

    def mark_task_claiming_started(
        self,
        enabled: bool,
        interval_seconds: float,
    ) -> None:
        self.claiming_started_at = datetime.now(timezone.utc)
        self.claiming_enabled = bool(enabled)
        self.claiming_status = "active" if enabled else "disabled"
        self.claiming_interval_seconds = interval_seconds
        self.claiming_last_error = None

    def mark_task_claiming_completed(self, result: dict) -> None:
        self.last_claiming_at = datetime.now(timezone.utc)
        self.claiming_iteration += 1
        self.claiming_status = result.get("status") or "unknown"
        self.claiming_last_duration_ms = max(0, int(result.get("duration_ms") or 0))
        self.claims_attempted += max(0, int(result.get("attempted_count") or 0))
        self.claims_succeeded += max(0, int(result.get("claimed_count") or 0))
        self.claims_conflicted += max(0, int(result.get("conflict_count") or 0))
        self.claims_rejected += max(0, int(result.get("rejected_count") or 0))
        self.active_claims = max(0, int(result.get("active_claims") or 0))
        self.stale_claims = max(0, int(result.get("stale_claims") or 0))
        self.max_concurrent_claims = max(
            0,
            int(result.get("max_concurrent_claims") or 0),
        )
        self.max_attempts_per_cycle = max(
            0,
            int(result.get("max_attempts_per_cycle") or 0),
        )
        self.max_task_attempts = max(0, int(result.get("max_task_attempts") or 0))
        self.min_claim_interval_seconds = max(
            0.0,
            float(result.get("min_interval_seconds") or 0.0),
        )
        self.stale_claim_after_seconds = max(
            0,
            int(result.get("stale_after_seconds") or 0),
        )
        self.max_stale_claims = max(0, int(result.get("max_stale_claims") or 0))
        self.claiming_runner_id = result.get("runner_id")
        self.claiming_runtime_id = result.get("runtime_id")
        if result.get("task_id"):
            self.last_claimed_task = {
                "id": result.get("task_id"),
                "title": result.get("task_title"),
                "claimed_at": result.get("claimed_at"),
                "claim_state": result.get("claim_state"),
            }
        self.claiming_last_error = result.get("error")

    def mark_task_claiming_error(self, error: str, duration_ms: int = 0) -> None:
        self.last_claiming_at = datetime.now(timezone.utc)
        self.claiming_iteration += 1
        self.claiming_last_duration_ms = max(0, int(duration_ms or 0))
        self.claiming_errors += 1
        self.claiming_status = "error"
        self.claiming_last_error = error or "unknown_claiming_error"

    def ai_metrics(self) -> dict:
        avg_duration = 0
        avg_provider = 0
        avg_context = 0
        if self.total_ai_requests:
            avg_duration = int(self.total_ai_duration_ms / self.total_ai_requests)
            avg_provider = int(self.total_ai_provider_duration_ms / self.total_ai_requests)
            avg_context = int(self.total_ai_context_build_ms / self.total_ai_requests)

        return {
            "ai_requests_total": self.total_ai_requests,
            "ai_requests_success": self.ai_success_requests,
            "ai_requests_failed": self.ai_failed_requests,
            "ai_avg_duration_ms": avg_duration,
            "last_ai_error": self.last_ai_error,
            "last_ai_request_at": self.last_ai_request_at.isoformat()
            if self.last_ai_request_at
            else None,
            "last_provider": self.last_ai_provider,
            "last_model": self.last_ai_model,
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
            "telegram_messages_total": self.telegram_messages_total,
            "telegram_messages_failed": self.telegram_messages_failed,
            "telegram_last_message_at": self.telegram_last_message_at.isoformat()
            if self.telegram_last_message_at
            else None,
            "telegram_last_error": self.telegram_last_error,
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

    def runtime_loop_health_status(self) -> str:
        if not self.runtime_loop_alive:
            return "stopped"
        if not self.runtime_safe:
            return "failed"
        if self.degraded_state:
            return "degraded"
        if self.runtime_loop_state == "paused":
            return "paused"
        if self.runtime_loop_last_heartbeat_at is None:
            return "starting"
        max_age = max(30.0, self.runtime_loop_interval_seconds * 3)
        age = (
            datetime.now(timezone.utc) - self.runtime_loop_last_heartbeat_at
        ).total_seconds()
        if age > max_age:
            return "degraded"
        return "healthy"

    def runtime_loop_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "alive": self.runtime_loop_alive,
            "status": self.runtime_loop_health_status(),
            "state": self.runtime_loop_state,
            "started_at": fmt(self.runtime_loop_started_at),
            "last_heartbeat_at": fmt(self.runtime_loop_last_heartbeat_at),
            "last_cycle_duration_ms": self.runtime_loop_last_cycle_duration_ms,
            "iteration": self.runtime_loop_iteration,
            "interval_seconds": self.runtime_loop_interval_seconds,
            "stop_requested": self.runtime_loop_stop_requested,
            "stop_reason": self.runtime_loop_stop_reason,
        }

    def safety_metrics(self) -> dict:
        return {
            "runtime_safe": self.runtime_safe,
            "consecutive_errors": self.consecutive_errors,
            "degraded_state": self.degraded_state,
            "stop_reason": self.safety_stop_reason,
            "safety_events": list(self.safety_events),
        }

    def polling_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "started_at": fmt(self.polling_started_at),
            "last_poll_time": fmt(self.last_poll_time),
            "polling_iteration": self.polling_iteration,
            "tasks_detected": self.tasks_detected,
            "polling_status": self.polling_status,
            "polling_interval_seconds": self.polling_interval_seconds,
            "polling_last_duration_ms": self.polling_last_duration_ms,
            "polling_errors": self.polling_errors,
            "polling_last_error": self.polling_last_error,
        }

    def discovery_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "started_at": fmt(self.discovery_started_at),
            "last_discovery_at": fmt(self.last_discovery_at),
            "discovery_iteration": self.discovery_iteration,
            "discovery_status": self.discovery_status,
            "discovered_tasks": self.discovered_tasks,
            "discovery_interval_seconds": self.discovery_interval_seconds,
            "discovery_last_duration_ms": self.discovery_last_duration_ms,
            "discovery_errors": self.discovery_errors,
            "discovery_last_error": self.discovery_last_error,
            "discovery_limit": self.discovery_limit,
            "discovery_max_payload_bytes": self.discovery_max_payload_bytes,
            "discovery_query_timeout_seconds": self.discovery_query_timeout_seconds,
            "discovery_ignored_count": self.discovery_ignored_count,
            "discovery_ignored_reasons": dict(self.discovery_ignored_reasons),
            "discovery_filters": dict(self.discovery_filters),
            "discovery_ordering": list(self.discovery_ordering),
            "discovery_candidates": list(self.discovery_candidates),
        }

    def claiming_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "started_at": fmt(self.claiming_started_at),
            "last_claiming_at": fmt(self.last_claiming_at),
            "claiming_iteration": self.claiming_iteration,
            "claiming_enabled": self.claiming_enabled,
            "claiming_status": self.claiming_status,
            "claiming_interval_seconds": self.claiming_interval_seconds,
            "claiming_last_duration_ms": self.claiming_last_duration_ms,
            "claiming_errors": self.claiming_errors,
            "claiming_last_error": self.claiming_last_error,
            "claims_attempted": self.claims_attempted,
            "claims_succeeded": self.claims_succeeded,
            "claims_conflicted": self.claims_conflicted,
            "claims_rejected": self.claims_rejected,
            "active_claims": self.active_claims,
            "stale_claims": self.stale_claims,
            "max_concurrent_claims": self.max_concurrent_claims,
            "max_attempts_per_cycle": self.max_attempts_per_cycle,
            "max_task_attempts": self.max_task_attempts,
            "min_claim_interval_seconds": self.min_claim_interval_seconds,
            "stale_claim_after_seconds": self.stale_claim_after_seconds,
            "max_stale_claims": self.max_stale_claims,
            "runner_id": self.claiming_runner_id,
            "runtime_id": self.claiming_runtime_id,
            "last_claimed_task": self.last_claimed_task,
        }

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
            "runtime_loop": self.runtime_loop_metrics(),
            "polling": self.polling_metrics(),
            "discovery": self.discovery_metrics(),
            "claiming": self.claiming_metrics(),
            "safety": self.safety_metrics(),
        }
        data.update(self.ai_metrics())
        data.update(self.telegram_metrics())
        return data


runtime_status = RuntimeStatus()
