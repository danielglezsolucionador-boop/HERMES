"""
Execution safety controls for Hermes runtime.

This layer inspects execution and provider bridge signals to prevent unsafe
execution flow. It does not execute tasks, retry work, recover tasks, call
providers, or mutate database state.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

PROVIDER_FAILURE_REASONS = {
    "provider_error": "provider_error_detected",
    "invalid_response": "provider_invalid_response_detected",
    "timeout": "provider_timeout_detected",
    "error": "provider_bridge_error_detected",
}
EXECUTION_CONFLICT_REASONS = {
    "max_concurrent_executions_reached",
    "start_requires_claimed_state",
    "complete_requires_executing_state",
    "duration_check_requires_executing_state",
    "invalid_runner_owner",
    "invalid_runtime_owner",
    "invalid_claim_state",
}


@dataclass(frozen=True)
class ExecutionSafetyResult:
    status: str
    allows_execution: bool
    runtime_protected: bool
    conflict_detected: bool = False
    timeout_detected: bool = False
    provider_failure_detected: bool = False
    retry_allowed: bool = True
    retry_attempts: int = 0
    max_retries: int = 0
    active_executions: int = 0
    max_concurrent_executions: int = 0
    runtime_load: float | None = None
    max_runtime_load: float = 0.0
    memory_usage_mb: float | None = None
    max_memory_mb: int = 0
    active_provider_calls: int = 0
    max_concurrent_provider_calls: int = 0
    provider_status: str | None = None
    execution_status: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None
    checked_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "allows_execution": self.allows_execution,
            "runtime_protected": self.runtime_protected,
            "conflict_detected": self.conflict_detected,
            "timeout_detected": self.timeout_detected,
            "provider_failure_detected": self.provider_failure_detected,
            "retry_allowed": self.retry_allowed,
            "retry_attempts": self.retry_attempts,
            "max_retries": self.max_retries,
            "active_executions": self.active_executions,
            "max_concurrent_executions": self.max_concurrent_executions,
            "runtime_load": self.runtime_load,
            "max_runtime_load": self.max_runtime_load,
            "memory_usage_mb": self.memory_usage_mb,
            "max_memory_mb": self.max_memory_mb,
            "active_provider_calls": self.active_provider_calls,
            "max_concurrent_provider_calls": self.max_concurrent_provider_calls,
            "provider_status": self.provider_status,
            "execution_status": self.execution_status,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "reasons": list(self.reasons),
            "error": self.error,
            "checked_at": self.checked_at,
            "duration_ms": self.duration_ms,
        }


class ExecutionSafety:
    def __init__(
        self,
        max_retries: int = settings.TASK_EXECUTION_SAFETY_MAX_RETRIES,
        max_concurrent_executions: int = (
            settings.TASK_EXECUTION_MAX_CONCURRENT_EXECUTIONS
        ),
        max_duration_seconds: int = settings.TASK_EXECUTION_MAX_DURATION_SECONDS,
        max_runtime_load: float = settings.TASK_EXECUTION_MAX_RUNTIME_LOAD,
        max_memory_mb: int = settings.TASK_EXECUTION_MAX_MEMORY_MB,
        max_concurrent_provider_calls: int = (
            settings.PROVIDER_BRIDGE_MAX_CONCURRENT_CALLS
        ),
    ) -> None:
        self.max_retries = max(0, int(max_retries or 0))
        self.max_concurrent_executions = max(1, int(max_concurrent_executions or 1))
        self.max_duration_seconds = max(1, int(max_duration_seconds or 1))
        self.max_runtime_load = max(0.0, float(max_runtime_load or 0.0))
        self.max_memory_mb = max(0, int(max_memory_mb or 0))
        self.max_concurrent_provider_calls = max(
            1,
            int(max_concurrent_provider_calls or 1),
        )

    async def inspect(
        self,
        execution_visibility: dict[str, Any] | None = None,
        execution_result: Any | None = None,
        provider_result: Any | None = None,
        provider_visibility: dict[str, Any] | None = None,
        runtime_active: bool = True,
        retry_attempts: int = 0,
    ) -> ExecutionSafetyResult:
        return self.evaluate(
            execution_visibility=execution_visibility,
            execution_result=execution_result,
            provider_result=provider_result,
            provider_visibility=provider_visibility,
            runtime_active=runtime_active,
            retry_attempts=retry_attempts,
        )

    def evaluate(
        self,
        execution_visibility: dict[str, Any] | None = None,
        execution_result: Any | None = None,
        provider_result: Any | None = None,
        provider_visibility: dict[str, Any] | None = None,
        runtime_active: bool = True,
        retry_attempts: int = 0,
    ) -> ExecutionSafetyResult:
        started = time.perf_counter()
        try:
            result = self._evaluate(
                execution_visibility=execution_visibility or {},
                execution_result=self._as_dict(execution_result),
                provider_result=self._as_dict(provider_result),
                provider_visibility=provider_visibility or {},
                runtime_active=runtime_active,
                retry_attempts=max(0, int(retry_attempts or 0)),
                started=started,
            )
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._result(
                status="error",
                allows_execution=False,
                runtime_protected=True,
                retry_attempts=max(0, int(retry_attempts or 0)),
                reasons=["execution_safety_error_contained"],
                error=str(exc),
                started=started,
            )
            self._log_result(result)
            return result

    def _evaluate(
        self,
        execution_visibility: dict[str, Any],
        execution_result: dict[str, Any],
        provider_result: dict[str, Any],
        provider_visibility: dict[str, Any],
        runtime_active: bool,
        retry_attempts: int,
        started: float,
    ) -> ExecutionSafetyResult:
        reasons: list[str] = []
        active_contexts = self._contexts(execution_visibility)
        active_executions = self._int(
            execution_visibility.get("active_executions"),
            len(active_contexts),
        )
        max_concurrent_executions = self._int(
            execution_visibility.get("max_concurrent_executions"),
            self.max_concurrent_executions,
        )
        max_duration_seconds = self._int(
            execution_visibility.get("max_duration_seconds"),
            self.max_duration_seconds,
        )
        max_runtime_load = self._float(
            execution_visibility.get("max_runtime_load"),
            self.max_runtime_load,
        )
        runtime_load = self._maybe_float(execution_visibility.get("runtime_load"))
        max_memory_mb = self._int(
            execution_visibility.get("max_memory_mb"),
            self.max_memory_mb,
        )
        memory_usage_mb = self._maybe_float(
            execution_visibility.get("memory_usage_mb")
        )
        active_provider_calls = self._int(
            provider_visibility.get("active_provider_calls"),
            provider_result.get("active_provider_calls", 0),
        )
        max_concurrent_provider_calls = self._int(
            provider_visibility.get("max_concurrent_provider_calls"),
            provider_result.get(
                "max_concurrent_provider_calls",
                self.max_concurrent_provider_calls,
            ),
        )
        execution_reasons = [
            str(reason) for reason in (execution_result.get("reasons") or [])
        ]
        provider_reasons = [
            str(reason) for reason in (provider_result.get("reasons") or [])
        ]
        provider_status = provider_result.get("status")
        execution_status = execution_result.get("status")

        if not runtime_active:
            reasons.append("runtime_inactive")
        if active_executions > max_concurrent_executions:
            reasons.append("execution_overlap_detected")
        reasons.extend(self._duplicate_context_reasons(active_contexts))
        reasons.extend(
            reason
            for reason in execution_reasons
            if reason in EXECUTION_CONFLICT_REASONS
        )
        if execution_status == "error":
            reasons.append("execution_error_contained")
        if "max_execution_duration_exceeded" in execution_reasons:
            reasons.append("execution_timeout_detected")
        reasons.extend(
            self._stale_context_reasons(active_contexts, max_duration_seconds)
        )
        if (
            runtime_load is not None
            and max_runtime_load > 0
            and runtime_load > max_runtime_load
        ):
            reasons.append("runtime_load_degraded")
        if memory_usage_mb is not None and max_memory_mb > 0 and memory_usage_mb > max_memory_mb:
            reasons.append("runtime_memory_degraded")
        if provider_status in PROVIDER_FAILURE_REASONS:
            reasons.append(PROVIDER_FAILURE_REASONS[provider_status])
        reasons.extend(reason for reason in provider_reasons if "provider" in reason)
        if (
            max_concurrent_provider_calls > 0
            and active_provider_calls >= max_concurrent_provider_calls
        ):
            reasons.append("provider_saturation_detected")
        if retry_attempts >= self.max_retries and retry_attempts > 0:
            reasons.append("max_execution_retries_reached")

        unique_reasons = self._unique(reasons)
        conflict_detected = any(
            reason
            in {
                "execution_overlap_detected",
                "duplicate_execution_id_detected",
                "duplicate_task_execution_detected",
            }
            or reason in EXECUTION_CONFLICT_REASONS
            for reason in unique_reasons
        )
        timeout_detected = any(
            reason
            in {
                "execution_timeout_detected",
                "stale_execution_detected",
                "provider_timeout_detected",
            }
            for reason in unique_reasons
        )
        provider_failure_detected = any(
            reason.startswith("provider_") for reason in unique_reasons
        )
        retry_allowed = retry_attempts == 0 or retry_attempts < self.max_retries
        allows_execution = not unique_reasons
        status = "safe" if allows_execution else "blocked"

        return self._result(
            status=status,
            allows_execution=allows_execution,
            runtime_protected=True,
            conflict_detected=conflict_detected,
            timeout_detected=timeout_detected,
            provider_failure_detected=provider_failure_detected,
            retry_allowed=retry_allowed,
            retry_attempts=retry_attempts,
            active_executions=active_executions,
            max_concurrent_executions=max_concurrent_executions,
            runtime_load=runtime_load,
            max_runtime_load=max_runtime_load,
            memory_usage_mb=memory_usage_mb,
            max_memory_mb=max_memory_mb,
            active_provider_calls=active_provider_calls,
            max_concurrent_provider_calls=max_concurrent_provider_calls,
            provider_status=provider_status,
            execution_status=execution_status,
            execution_id=execution_result.get("execution_id")
            or provider_result.get("execution_id"),
            task_id=execution_result.get("task_id") or provider_result.get("task_id"),
            reasons=unique_reasons,
            error=execution_result.get("error") or provider_result.get("error"),
            started=started,
        )

    def _result(
        self,
        status: str,
        allows_execution: bool,
        runtime_protected: bool,
        conflict_detected: bool = False,
        timeout_detected: bool = False,
        provider_failure_detected: bool = False,
        retry_allowed: bool = True,
        retry_attempts: int = 0,
        active_executions: int = 0,
        max_concurrent_executions: int | None = None,
        runtime_load: float | None = None,
        max_runtime_load: float | None = None,
        memory_usage_mb: float | None = None,
        max_memory_mb: int | None = None,
        active_provider_calls: int = 0,
        max_concurrent_provider_calls: int | None = None,
        provider_status: str | None = None,
        execution_status: str | None = None,
        execution_id: str | None = None,
        task_id: str | None = None,
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
    ) -> ExecutionSafetyResult:
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        return ExecutionSafetyResult(
            status=status,
            allows_execution=allows_execution,
            runtime_protected=runtime_protected,
            conflict_detected=conflict_detected,
            timeout_detected=timeout_detected,
            provider_failure_detected=provider_failure_detected,
            retry_allowed=retry_allowed,
            retry_attempts=retry_attempts,
            max_retries=self.max_retries,
            active_executions=max(0, int(active_executions or 0)),
            max_concurrent_executions=(
                self.max_concurrent_executions
                if max_concurrent_executions is None
                else max(0, int(max_concurrent_executions or 0))
            ),
            runtime_load=runtime_load,
            max_runtime_load=(
                self.max_runtime_load
                if max_runtime_load is None
                else max(0.0, float(max_runtime_load or 0.0))
            ),
            memory_usage_mb=memory_usage_mb,
            max_memory_mb=(
                self.max_memory_mb
                if max_memory_mb is None
                else max(0, int(max_memory_mb or 0))
            ),
            active_provider_calls=max(0, int(active_provider_calls or 0)),
            max_concurrent_provider_calls=(
                self.max_concurrent_provider_calls
                if max_concurrent_provider_calls is None
                else max(0, int(max_concurrent_provider_calls or 0))
            ),
            provider_status=provider_status,
            execution_status=execution_status,
            execution_id=execution_id,
            task_id=task_id,
            reasons=tuple(reasons or []),
            error=error,
            duration_ms=duration_ms,
        )

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            return to_dict()
        return {}

    def _contexts(self, visibility: dict[str, Any]) -> list[dict[str, Any]]:
        contexts = visibility.get("active_contexts") or []
        result: list[dict[str, Any]] = []
        for context in contexts:
            result.append(self._as_dict(context))
        return result

    def _duplicate_context_reasons(
        self,
        active_contexts: list[dict[str, Any]],
    ) -> list[str]:
        reasons: list[str] = []
        execution_ids = [
            context.get("execution_id")
            for context in active_contexts
            if context.get("execution_id")
        ]
        task_ids = [
            context.get("task_id")
            for context in active_contexts
            if context.get("task_id")
        ]
        if len(execution_ids) != len(set(execution_ids)):
            reasons.append("duplicate_execution_id_detected")
        if len(task_ids) != len(set(task_ids)):
            reasons.append("duplicate_task_execution_detected")
        return reasons

    def _stale_context_reasons(
        self,
        active_contexts: list[dict[str, Any]],
        max_duration_seconds: int,
    ) -> list[str]:
        for context in active_contexts:
            duration_ms = self._int(context.get("execution_duration_ms"), 0)
            if duration_ms > max_duration_seconds * 1000:
                return ["stale_execution_detected"]
        return []

    def _int(self, value: Any, default: int) -> int:
        try:
            if value is None:
                return int(default)
            return int(value)
        except (TypeError, ValueError):
            return int(default)

    def _float(self, value: Any, default: float) -> float:
        try:
            if value is None:
                return float(default)
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def _maybe_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _unique(self, reasons: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for reason in reasons:
            if reason and reason not in seen:
                seen.add(reason)
                unique.append(reason)
        return unique

    def _log_result(self, result: ExecutionSafetyResult) -> None:
        if result.status == "safe":
            logger.debug(
                "execution_safety: safe active_executions=%s provider_calls=%s",
                result.active_executions,
                result.active_provider_calls,
            )
            return
        if result.status == "error":
            logger.error(
                "execution_safety: error reasons=%s error=%s",
                ",".join(result.reasons),
                result.error,
            )
            return
        logger.warning(
            "execution_safety: blocked reasons=%s active_executions=%s provider_calls=%s",
            ",".join(result.reasons),
            result.active_executions,
            result.active_provider_calls,
        )
