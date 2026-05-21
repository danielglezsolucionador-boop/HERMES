"""
Controlled timeout monitoring for Hermes execution runtime.

This layer observes execution duration and records timeout state. It does not
kill executions, retry work, recover tasks, restart services, call providers,
or mutate database state.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.runner.task_execution import (
    EXECUTION_STATE_EXECUTING,
    ExecutionContext,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TimeoutControlResult:
    status: str
    success: bool
    timeout_state: str
    monitoring_allowed: bool
    runtime_protected: bool
    timeout_detected: bool = False
    timeout_registered: bool = False
    duration_tracking: bool = False
    linkage_valid: bool = True
    ownership_consistent: bool = True
    timeout_id: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    runtime_id: str | None = None
    runtime_owner: str | None = None
    execution_state: str | None = None
    execution_started_at: str | None = None
    current_runtime_duration_ms: int = 0
    timeout_threshold_ms: int = 0
    max_tracking_duration_ms: int = 0
    detected_at: str | None = None
    checked_at: str | None = None
    active_timeout_checks: int = 0
    max_concurrent_timeout_checks: int = 0
    runtime_timeout_load: float | None = None
    max_runtime_timeout_load: float = 0.0
    timeout_check_duration_ms: int = 0
    max_timeout_check_duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success": self.success,
            "timeout_state": self.timeout_state,
            "monitoring_allowed": self.monitoring_allowed,
            "runtime_protected": self.runtime_protected,
            "timeout_detected": self.timeout_detected,
            "timeout_registered": self.timeout_registered,
            "duration_tracking": self.duration_tracking,
            "linkage_valid": self.linkage_valid,
            "ownership_consistent": self.ownership_consistent,
            "timeout_id": self.timeout_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "runtime_id": self.runtime_id,
            "runtime_owner": self.runtime_owner,
            "execution_state": self.execution_state,
            "execution_started_at": self.execution_started_at,
            "current_runtime_duration_ms": self.current_runtime_duration_ms,
            "timeout_threshold_ms": self.timeout_threshold_ms,
            "max_tracking_duration_ms": self.max_tracking_duration_ms,
            "detected_at": self.detected_at,
            "checked_at": self.checked_at,
            "active_timeout_checks": self.active_timeout_checks,
            "max_concurrent_timeout_checks": self.max_concurrent_timeout_checks,
            "runtime_timeout_load": self.runtime_timeout_load,
            "max_runtime_timeout_load": self.max_runtime_timeout_load,
            "timeout_check_duration_ms": self.timeout_check_duration_ms,
            "max_timeout_check_duration_ms": self.max_timeout_check_duration_ms,
            "metadata": dict(self.metadata),
            "reasons": list(self.reasons),
            "error": self.error,
        }


class TimeoutControl:
    def __init__(
        self,
        runtime_owner: str = f"{settings.RUNNER_ID}:{settings.RUNTIME_ID}",
        max_execution_duration_seconds: int = (
            settings.TASK_EXECUTION_MAX_DURATION_SECONDS
        ),
        max_concurrent_timeout_checks: int = (
            settings.TIMEOUT_CONTROL_MAX_CONCURRENT_CHECKS
        ),
        max_tracking_duration_seconds: int = (
            settings.TIMEOUT_CONTROL_MAX_TRACKING_DURATION_SECONDS
        ),
        max_runtime_timeout_load: float = (
            settings.TIMEOUT_CONTROL_MAX_RUNTIME_LOAD
        ),
        max_check_duration_ms: int = settings.TIMEOUT_CONTROL_MAX_CHECK_DURATION_MS,
    ) -> None:
        self.runtime_owner = runtime_owner
        self.max_execution_duration_seconds = max(
            1,
            int(max_execution_duration_seconds or 1),
        )
        self.max_concurrent_timeout_checks = max(
            1,
            int(max_concurrent_timeout_checks or 1),
        )
        self.max_tracking_duration_seconds = max(
            1,
            int(max_tracking_duration_seconds or 1),
        )
        self.max_runtime_timeout_load = max(
            0.0,
            float(max_runtime_timeout_load or 0.0),
        )
        self.max_check_duration_ms = max(1, int(max_check_duration_ms or 1))
        self._active_timeout_checks = 0

    async def inspect(
        self,
        execution_visibility: dict[str, Any] | None = None,
        execution_context: ExecutionContext | dict[str, Any] | None = None,
        runtime_active: bool = True,
        monitoring_permitted: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> TimeoutControlResult:
        return self.evaluate(
            execution_visibility=execution_visibility,
            execution_context=execution_context,
            runtime_active=runtime_active,
            monitoring_permitted=monitoring_permitted,
            metadata=metadata,
        )

    def evaluate(
        self,
        execution_visibility: dict[str, Any] | None = None,
        execution_context: ExecutionContext | dict[str, Any] | None = None,
        runtime_active: bool = True,
        monitoring_permitted: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> TimeoutControlResult:
        started = time.perf_counter()
        try:
            visibility = execution_visibility or {}
            contexts = self._contexts(visibility, execution_context)
            reasons = self._preflight_reasons(
                runtime_active=runtime_active,
                monitoring_permitted=monitoring_permitted,
            )
            if reasons:
                result = self._result(
                    status="rejected",
                    success=False,
                    timeout_state="monitoring_rejected",
                    monitoring_allowed=False,
                    reasons=reasons,
                    metadata=metadata,
                    started=started,
                )
                self._log_result(result)
                return result

            self._active_timeout_checks += 1
            try:
                result = self._evaluate_contexts(
                    contexts=contexts,
                    visibility=visibility,
                    metadata=metadata,
                    started=started,
                )
            finally:
                self._active_timeout_checks = max(
                    0,
                    self._active_timeout_checks - 1,
                )
            result = replace(
                result,
                active_timeout_checks=self._active_timeout_checks,
                runtime_timeout_load=self._runtime_timeout_load(),
            )
            self._log_result(result)
            return result
        except Exception as exc:
            self._active_timeout_checks = max(0, self._active_timeout_checks - 1)
            result = self._result(
                status="error",
                success=False,
                timeout_state="error",
                monitoring_allowed=False,
                runtime_protected=True,
                reasons=["timeout_control_error_contained"],
                error=str(exc),
                metadata=metadata,
                started=started,
            )
            self._log_result(result)
            return result

    def visibility(self) -> dict[str, Any]:
        return {
            "active_timeout_checks": self._active_timeout_checks,
            "max_concurrent_timeout_checks": self.max_concurrent_timeout_checks,
            "max_tracking_duration_ms": self.max_tracking_duration_seconds * 1000,
            "runtime_timeout_load": self._runtime_timeout_load(),
            "max_runtime_timeout_load": self.max_runtime_timeout_load,
            "max_timeout_check_duration_ms": self.max_check_duration_ms,
        }

    def _evaluate_contexts(
        self,
        contexts: list[dict[str, Any]],
        visibility: dict[str, Any],
        metadata: dict[str, Any] | None,
        started: float,
    ) -> TimeoutControlResult:
        if not contexts:
            return self._result(
                status="clear",
                success=True,
                timeout_state="ready",
                monitoring_allowed=True,
                runtime_protected=True,
                metadata=metadata,
                started=started,
            )

        tracked_context = contexts[0]
        all_reasons: list[str] = []
        timeout_context: dict[str, Any] | None = None
        timeout_duration_ms = 0
        timeout_threshold_ms = 0

        for context in contexts:
            reasons, duration_ms, threshold_ms = self._context_reasons(
                context,
                visibility,
            )
            all_reasons.extend(reasons)
            if "execution_timeout_detected" in reasons and timeout_context is None:
                timeout_context = context
                timeout_duration_ms = duration_ms
                timeout_threshold_ms = threshold_ms

        all_reasons.extend(self._duration_reasons(started))
        unique_reasons = self._unique(all_reasons)
        chosen_context = timeout_context or tracked_context
        duration_ms = timeout_duration_ms or self._execution_duration_ms(
            chosen_context
        )
        threshold_ms = timeout_threshold_ms or self._timeout_threshold_ms(
            chosen_context,
            visibility,
        )
        timeout_detected = "execution_timeout_detected" in unique_reasons
        invalid_monitoring = any(
            reason
            in {
                "missing_execution_id",
                "missing_task_id",
                "missing_runtime_id",
                "missing_runtime_owner",
                "missing_execution_started_at",
                "invalid_execution_started_at",
                "invalid_execution_state",
                "runtime_owner_mismatch",
                "invalid_timeout_threshold",
            }
            for reason in unique_reasons
        )

        if timeout_detected:
            status = "timeout_detected"
            timeout_state = "detected"
            success = False
            monitoring_allowed = True
        elif invalid_monitoring or "timeout_control_overhead_exceeded" in unique_reasons:
            status = "rejected"
            timeout_state = "monitoring_rejected"
            success = False
            monitoring_allowed = False
        else:
            status = "tracking"
            timeout_state = "tracking"
            success = True
            monitoring_allowed = True

        return self._result(
            status=status,
            success=success,
            timeout_state=timeout_state,
            monitoring_allowed=monitoring_allowed,
            runtime_protected=True,
            timeout_detected=timeout_detected,
            timeout_registered=timeout_detected,
            duration_tracking=bool(contexts) and not invalid_monitoring,
            linkage_valid=not self._has_linkage_reason(unique_reasons),
            ownership_consistent="runtime_owner_mismatch" not in unique_reasons,
            context=chosen_context,
            duration_ms=duration_ms,
            threshold_ms=threshold_ms,
            reasons=unique_reasons,
            metadata=metadata,
            started=started,
        )

    def _preflight_reasons(
        self,
        runtime_active: bool,
        monitoring_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not monitoring_permitted:
            reasons.append("timeout_monitoring_not_permitted")
        if self._active_timeout_checks >= self.max_concurrent_timeout_checks:
            reasons.append("max_concurrent_timeout_checks_reached")
        runtime_load = self._runtime_timeout_load()
        if (
            runtime_load is not None
            and self.max_runtime_timeout_load > 0
            and runtime_load > self.max_runtime_timeout_load
        ):
            reasons.append("max_runtime_timeout_load_reached")
        return reasons

    def _context_reasons(
        self,
        context: dict[str, Any],
        visibility: dict[str, Any],
    ) -> tuple[list[str], int, int]:
        reasons: list[str] = []
        if not context.get("execution_id"):
            reasons.append("missing_execution_id")
        if not context.get("task_id"):
            reasons.append("missing_task_id")
        if not context.get("runtime_id"):
            reasons.append("missing_runtime_id")
        runtime_owner = context.get("runtime_owner")
        if not runtime_owner:
            reasons.append("missing_runtime_owner")
        elif runtime_owner != self.runtime_owner:
            reasons.append("runtime_owner_mismatch")
        if context.get("execution_state") != EXECUTION_STATE_EXECUTING:
            reasons.append("invalid_execution_state")

        started_at = context.get("started_at")
        if not started_at:
            reasons.append("missing_execution_started_at")
        elif self._parse_datetime(started_at) is None:
            reasons.append("invalid_execution_started_at")

        threshold_ms = self._timeout_threshold_ms(context, visibility)
        if threshold_ms <= 0:
            reasons.append("invalid_timeout_threshold")

        duration_ms = self._execution_duration_ms(context)
        if threshold_ms > 0 and duration_ms > threshold_ms:
            reasons.append("execution_timeout_detected")
        if duration_ms > self.max_tracking_duration_seconds * 1000:
            reasons.append("max_timeout_tracking_duration_exceeded")
        return reasons, duration_ms, threshold_ms

    def _contexts(
        self,
        visibility: dict[str, Any],
        execution_context: ExecutionContext | dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        contexts: list[dict[str, Any]] = []
        if execution_context is not None:
            contexts.append(self._as_dict(execution_context))
        for context in visibility.get("active_contexts") or []:
            contexts.append(self._as_dict(context))
        return [context for context in contexts if context]

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

    def _timeout_threshold_ms(
        self,
        context: dict[str, Any],
        visibility: dict[str, Any],
    ) -> int:
        value = (
            context.get("max_duration_seconds")
            or visibility.get("max_duration_seconds")
            or self.max_execution_duration_seconds
        )
        try:
            return max(0, int(value or 0) * 1000)
        except (TypeError, ValueError):
            return 0

    def _execution_duration_ms(self, context: dict[str, Any]) -> int:
        started_at = self._parse_datetime(context.get("started_at"))
        if started_at is None:
            return max(0, self._int(context.get("execution_duration_ms"), 0))
        return max(
            0,
            int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000),
        )

    def _parse_datetime(self, value: Any) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

    def _duration_reasons(self, started: float) -> list[str]:
        if self._duration_ms(started) > self.max_check_duration_ms:
            return ["timeout_control_overhead_exceeded"]
        return []

    def _result(
        self,
        status: str,
        success: bool,
        timeout_state: str,
        monitoring_allowed: bool,
        runtime_protected: bool = True,
        timeout_detected: bool = False,
        timeout_registered: bool = False,
        duration_tracking: bool = False,
        linkage_valid: bool = True,
        ownership_consistent: bool = True,
        context: dict[str, Any] | None = None,
        duration_ms: int = 0,
        threshold_ms: int = 0,
        reasons: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        error: str | None = None,
        started: float | None = None,
    ) -> TimeoutControlResult:
        context = context or {}
        checked_at = datetime.now(timezone.utc).isoformat()
        return TimeoutControlResult(
            status=status,
            success=success,
            timeout_state=timeout_state,
            monitoring_allowed=monitoring_allowed,
            runtime_protected=runtime_protected,
            timeout_detected=timeout_detected,
            timeout_registered=timeout_registered,
            duration_tracking=duration_tracking,
            linkage_valid=linkage_valid,
            ownership_consistent=ownership_consistent,
            timeout_id=str(uuid4()) if timeout_detected else None,
            execution_id=context.get("execution_id"),
            task_id=context.get("task_id"),
            runtime_id=context.get("runtime_id"),
            runtime_owner=context.get("runtime_owner"),
            execution_state=context.get("execution_state"),
            execution_started_at=context.get("started_at"),
            current_runtime_duration_ms=max(0, int(duration_ms or 0)),
            timeout_threshold_ms=max(0, int(threshold_ms or 0)),
            max_tracking_duration_ms=self.max_tracking_duration_seconds * 1000,
            detected_at=checked_at if timeout_detected else None,
            checked_at=checked_at,
            active_timeout_checks=self._active_timeout_checks,
            max_concurrent_timeout_checks=self.max_concurrent_timeout_checks,
            runtime_timeout_load=self._runtime_timeout_load(),
            max_runtime_timeout_load=self.max_runtime_timeout_load,
            timeout_check_duration_ms=self._duration_ms(started),
            max_timeout_check_duration_ms=self.max_check_duration_ms,
            metadata=dict(metadata or {}),
            reasons=tuple(reasons or []),
            error=error,
        )

    def _has_linkage_reason(self, reasons: list[str]) -> bool:
        return any(
            reason
            in {
                "missing_execution_id",
                "missing_task_id",
                "missing_runtime_id",
                "missing_runtime_owner",
                "missing_execution_started_at",
                "invalid_execution_started_at",
                "invalid_execution_state",
            }
            for reason in reasons
        )

    def _runtime_timeout_load(self) -> float | None:
        if self.max_concurrent_timeout_checks <= 0:
            return None
        return round(self._active_timeout_checks / self.max_concurrent_timeout_checks, 4)

    def _duration_ms(self, started: float | None) -> int:
        return int((time.perf_counter() - started) * 1000) if started else 0

    def _int(self, value: Any, default: int) -> int:
        try:
            if value is None:
                return int(default)
            return int(value)
        except (TypeError, ValueError):
            return int(default)

    def _unique(self, reasons: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for reason in reasons:
            if reason and reason not in seen:
                seen.add(reason)
                unique.append(reason)
        return unique

    def _log_result(self, result: TimeoutControlResult) -> None:
        if result.status in {"clear", "tracking"}:
            logger.debug(
                "timeout_control: %s execution_id=%s duration_ms=%s threshold_ms=%s",
                result.status,
                result.execution_id,
                result.current_runtime_duration_ms,
                result.timeout_threshold_ms,
            )
            return
        if result.status == "error":
            logger.error(
                "timeout_control: error reasons=%s error=%s",
                ",".join(result.reasons),
                result.error,
            )
            return
        if result.status == "timeout_detected":
            logger.warning(
                "timeout_control: timeout detected timeout_id=%s execution_id=%s duration_ms=%s threshold_ms=%s",
                result.timeout_id,
                result.execution_id,
                result.current_runtime_duration_ms,
                result.timeout_threshold_ms,
            )
            return
        logger.warning(
            "timeout_control: rejected reasons=%s execution_id=%s",
            ",".join(result.reasons),
            result.execution_id,
        )
