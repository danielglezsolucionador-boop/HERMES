"""
Controlled retry monitoring for Hermes execution runtime.

This layer validates and registers retry intent. It does not requeue tasks,
call providers, recover executions, orchestrate retries, or mutate database
state.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.models.task import Task
from app.runner.task_execution import EXECUTION_STATE_FAILED

logger = logging.getLogger(__name__)

FAILED_STATUSES = {"failed", "error"}
PROVIDER_BLOCKING_STATUSES = {
    "provider_error",
    "invalid_response",
    "timeout",
    "rate_limited",
    "error",
}


@dataclass(frozen=True)
class RetryControlResult:
    status: str
    success: bool
    retry_state: str
    retry_allowed: bool
    runtime_protected: bool
    retry_registered: bool = False
    retry_started: bool = False
    retry_completed: bool = False
    retry_failed: bool = False
    linkage_valid: bool = True
    ownership_consistent: bool = True
    threshold_valid: bool = True
    retry_id: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    runner_id: str | None = None
    runtime_id: str | None = None
    runtime_owner: str | None = None
    execution_state: str | None = None
    task_status: str | None = None
    provider_status: str | None = None
    provider_available: bool = True
    retry_attempt: int = 0
    retry_threshold: int = 0
    retry_reason: str | None = None
    retry_started_at: str | None = None
    retry_completed_at: str | None = None
    retry_duration_ms: int = 0
    active_retries: int = 0
    max_concurrent_retries: int = 0
    runtime_retry_load: float | None = None
    max_runtime_retry_load: float = 0.0
    max_retry_duration_ms: int = 0
    retry_control_overhead_ms: int = 0
    max_retry_overhead_ms: int = 0
    checked_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success": self.success,
            "retry_state": self.retry_state,
            "retry_allowed": self.retry_allowed,
            "runtime_protected": self.runtime_protected,
            "retry_registered": self.retry_registered,
            "retry_started": self.retry_started,
            "retry_completed": self.retry_completed,
            "retry_failed": self.retry_failed,
            "linkage_valid": self.linkage_valid,
            "ownership_consistent": self.ownership_consistent,
            "threshold_valid": self.threshold_valid,
            "retry_id": self.retry_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "runner_id": self.runner_id,
            "runtime_id": self.runtime_id,
            "runtime_owner": self.runtime_owner,
            "execution_state": self.execution_state,
            "task_status": self.task_status,
            "provider_status": self.provider_status,
            "provider_available": self.provider_available,
            "retry_attempt": self.retry_attempt,
            "retry_threshold": self.retry_threshold,
            "retry_reason": self.retry_reason,
            "retry_started_at": self.retry_started_at,
            "retry_completed_at": self.retry_completed_at,
            "retry_duration_ms": self.retry_duration_ms,
            "active_retries": self.active_retries,
            "max_concurrent_retries": self.max_concurrent_retries,
            "runtime_retry_load": self.runtime_retry_load,
            "max_runtime_retry_load": self.max_runtime_retry_load,
            "max_retry_duration_ms": self.max_retry_duration_ms,
            "retry_control_overhead_ms": self.retry_control_overhead_ms,
            "max_retry_overhead_ms": self.max_retry_overhead_ms,
            "checked_at": self.checked_at,
            "metadata": dict(self.metadata),
            "reasons": list(self.reasons),
            "error": self.error,
        }


class RetryControl:
    def __init__(
        self,
        runtime_owner: str = f"{settings.RUNNER_ID}:{settings.RUNTIME_ID}",
        max_retry_attempts: int = settings.RETRY_CONTROL_MAX_ATTEMPTS,
        max_concurrent_retries: int = (
            settings.RETRY_CONTROL_MAX_CONCURRENT_RETRIES
        ),
        max_retry_duration_ms: int = settings.RETRY_CONTROL_MAX_DURATION_MS,
        max_runtime_retry_load: float = settings.RETRY_CONTROL_MAX_RUNTIME_LOAD,
        max_retry_overhead_ms: int = settings.RETRY_CONTROL_MAX_OVERHEAD_MS,
    ) -> None:
        self.runtime_owner = runtime_owner
        self.max_retry_attempts = max(0, int(max_retry_attempts or 0))
        self.max_concurrent_retries = max(1, int(max_concurrent_retries or 1))
        self.max_retry_duration_ms = max(1, int(max_retry_duration_ms or 1))
        self.max_runtime_retry_load = max(
            0.0,
            float(max_runtime_retry_load or 0.0),
        )
        self.max_retry_overhead_ms = max(1, int(max_retry_overhead_ms or 1))
        self._active_retries = 0

    async def inspect(
        self,
        execution_result: Any | None = None,
        provider_result: Any | None = None,
        task: Task | dict[str, Any] | None = None,
        retry_reason: str | None = None,
        runtime_active: bool = True,
        retry_permitted: bool = True,
        provider_available: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> RetryControlResult:
        return self.evaluate(
            execution_result=execution_result,
            provider_result=provider_result,
            task=task,
            retry_reason=retry_reason,
            runtime_active=runtime_active,
            retry_permitted=retry_permitted,
            provider_available=provider_available,
            metadata=metadata,
        )

    def evaluate(
        self,
        execution_result: Any | None = None,
        provider_result: Any | None = None,
        task: Task | dict[str, Any] | None = None,
        retry_reason: str | None = None,
        runtime_active: bool = True,
        retry_permitted: bool = True,
        provider_available: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> RetryControlResult:
        started = time.perf_counter()
        active_registered = False
        try:
            execution = self._as_dict(execution_result)
            provider = self._as_dict(provider_result)
            task_data = self._task_snapshot(task)
            context = self._retry_context(
                execution=execution,
                task=task_data,
                retry_reason=retry_reason,
                metadata=metadata,
            )
            reasons = self._preflight_reasons(
                runtime_active=runtime_active,
                retry_permitted=retry_permitted,
                provider_available=provider_available,
                provider=provider,
            )
            retry_requested = self._retry_requested(
                execution=execution,
                task=task_data,
                retry_reason=retry_reason,
                metadata=metadata,
            )
            if not retry_requested:
                result = self._result(
                    status="idle",
                    success=True,
                    retry_state="ready",
                    retry_allowed=not reasons,
                    context=context,
                    reasons=reasons,
                    metadata=metadata,
                    provider=provider,
                    provider_available=provider_available,
                    started=started,
                )
                self._log_result(result)
                return result

            reasons.extend(self._context_reasons(context))
            reasons.extend(self._limit_reasons(context, started))
            unique_reasons = self._unique(reasons)
            if unique_reasons:
                result = self._result(
                    status="rejected",
                    success=False,
                    retry_state="rejected",
                    retry_allowed=False,
                    context=context,
                    reasons=unique_reasons,
                    metadata=metadata,
                    provider=provider,
                    provider_available=provider_available,
                    started=started,
                )
                self._log_result(result)
                return result

            self._active_retries += 1
            active_registered = True
            result = self._result(
                status="registered",
                success=True,
                retry_state="registered",
                retry_allowed=True,
                retry_registered=True,
                retry_started=True,
                retry_id=str(uuid4()),
                context=context,
                metadata=metadata,
                provider=provider,
                provider_available=provider_available,
                started=started,
            )
            self._log_result(result)
            return result
        except Exception as exc:
            if active_registered:
                self._active_retries = max(0, self._active_retries - 1)
            result = self._result(
                status="error",
                success=False,
                retry_state="error",
                retry_allowed=False,
                runtime_protected=True,
                reasons=["retry_control_error_contained"],
                error=str(exc),
                metadata=metadata,
                started=started,
            )
            self._log_result(result)
            return result

    def start(self, result: RetryControlResult) -> RetryControlResult:
        if result.status != "registered" or not result.retry_registered:
            started = time.perf_counter()
            rejected = self._result(
                status="rejected",
                success=False,
                retry_state="rejected",
                retry_allowed=False,
                runtime_protected=True,
                retry_id=result.retry_id,
                context=result.to_dict(),
                reasons=["retry_start_requires_registered_state"],
                metadata=result.metadata,
                started=started,
            )
            self._log_result(rejected)
            return rejected
        updated = replace(
            result,
            status="executing",
            retry_state="executing",
            retry_started=True,
            active_retries=self._active_retries,
            runtime_retry_load=self._runtime_retry_load(),
        )
        self._log_result(updated)
        return updated

    def complete(self, result: RetryControlResult) -> RetryControlResult:
        return self._finish(
            result=result,
            status="completed",
            retry_state="completed",
            success=True,
            retry_completed=True,
        )

    def fail(
        self,
        result: RetryControlResult,
        error: str = "unknown_retry_failure",
    ) -> RetryControlResult:
        return self._finish(
            result=result,
            status="failed",
            retry_state="failed",
            success=False,
            retry_failed=True,
            reasons=["retry_execution_failed"],
            error=error or "unknown_retry_failure",
        )

    def visibility(self) -> dict[str, Any]:
        return {
            "active_retries": self._active_retries,
            "max_concurrent_retries": self.max_concurrent_retries,
            "runtime_retry_load": self._runtime_retry_load(),
            "max_runtime_retry_load": self.max_runtime_retry_load,
            "max_retry_attempts": self.max_retry_attempts,
            "max_retry_duration_ms": self.max_retry_duration_ms,
            "max_retry_overhead_ms": self.max_retry_overhead_ms,
            "runtime_owner": self.runtime_owner,
        }

    def _finish(
        self,
        result: RetryControlResult,
        status: str,
        retry_state: str,
        success: bool,
        retry_completed: bool = False,
        retry_failed: bool = False,
        reasons: list[str] | None = None,
        error: str | None = None,
    ) -> RetryControlResult:
        if result.retry_state not in {"registered", "executing"}:
            started = time.perf_counter()
            rejected = self._result(
                status="rejected",
                success=False,
                retry_state="rejected",
                retry_allowed=False,
                retry_id=result.retry_id,
                context=result.to_dict(),
                reasons=["retry_finish_requires_active_state"],
                metadata=result.metadata,
                started=started,
            )
            self._log_result(rejected)
            return rejected

        self._active_retries = max(0, self._active_retries - 1)
        completed_at = datetime.now(timezone.utc).isoformat()
        duration_ms = self._elapsed_ms(result.retry_started_at, completed_at)
        final_reasons = self._unique(list(result.reasons) + list(reasons or []))
        updated = replace(
            result,
            status=status,
            success=success,
            retry_state=retry_state,
            retry_allowed=success,
            retry_registered=False,
            retry_completed=retry_completed,
            retry_failed=retry_failed,
            retry_completed_at=completed_at,
            retry_duration_ms=duration_ms,
            active_retries=self._active_retries,
            runtime_retry_load=self._runtime_retry_load(),
            reasons=tuple(final_reasons),
            error=error,
        )
        self._log_result(updated)
        return updated

    def _retry_requested(
        self,
        execution: dict[str, Any],
        task: dict[str, Any],
        retry_reason: str | None,
        metadata: dict[str, Any] | None,
    ) -> bool:
        if execution or task:
            return True
        if retry_reason:
            return True
        if metadata and any(
            key in metadata
            for key in (
                "retry_attempt",
                "retry_count",
                "retry_reason",
                "execution_id",
                "task_id",
            )
        ):
            return True
        return False

    def _preflight_reasons(
        self,
        runtime_active: bool,
        retry_permitted: bool,
        provider_available: bool,
        provider: dict[str, Any],
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not retry_permitted:
            reasons.append("retry_not_permitted")

        provider_status = str(provider.get("status") or "").strip().lower()
        provider_failed = bool(provider) and (
            provider_status in PROVIDER_BLOCKING_STATUSES
            or provider.get("success") is False
        )
        if not provider_available or provider_failed:
            reasons.append("provider_unavailable")
        return reasons

    def _context_reasons(self, context: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        if not context.get("task_id"):
            reasons.append("missing_task_id")
        if not context.get("failed_signal"):
            reasons.append("missing_failed_execution_signal")
        if context.get("task_id_mismatch"):
            reasons.append("execution_task_mismatch")
        if context.get("runtime_owner_mismatch"):
            reasons.append("runtime_owner_mismatch")
        if context.get("retry_threshold", 0) <= 0:
            reasons.append("invalid_retry_threshold")
        if context.get("retry_count", 0) >= context.get("retry_threshold", 0):
            reasons.append("max_retry_attempts_reached")
        if not context.get("retry_reason"):
            reasons.append("missing_retry_reason")
        return reasons

    def _limit_reasons(
        self,
        context: dict[str, Any],
        started: float,
    ) -> list[str]:
        reasons: list[str] = []
        if self._active_retries >= self.max_concurrent_retries:
            reasons.append("max_concurrent_retries_reached")

        runtime_load = self._runtime_retry_load()
        if (
            runtime_load is not None
            and self.max_runtime_retry_load > 0
            and runtime_load > self.max_runtime_retry_load
        ):
            reasons.append("max_runtime_retry_load_reached")

        retry_duration_ms = self._int(
            context.get("retry_duration_ms"),
            0,
        )
        if retry_duration_ms > self.max_retry_duration_ms:
            reasons.append("max_retry_duration_reached")
        if self._duration_ms(started) > self.max_retry_overhead_ms:
            reasons.append("retry_control_overhead_exceeded")
        return reasons

    def _retry_context(
        self,
        execution: dict[str, Any],
        task: dict[str, Any],
        retry_reason: str | None,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        metadata = dict(metadata or {})
        task_id = (
            task.get("task_id")
            or execution.get("task_id")
            or metadata.get("task_id")
        )
        execution_id = execution.get("execution_id") or metadata.get("execution_id")
        runner_id = (
            execution.get("runner_id")
            or task.get("runner_id")
            or metadata.get("runner_id")
        )
        runtime_id = (
            execution.get("runtime_id")
            or task.get("runtime_id")
            or metadata.get("runtime_id")
        )
        runtime_owner = (
            execution.get("runtime_owner")
            or task.get("runtime_owner")
            or metadata.get("runtime_owner")
        )
        if not runtime_owner and runner_id and runtime_id:
            runtime_owner = f"{runner_id}:{runtime_id}"
        if not runtime_owner:
            runtime_owner = self.runtime_owner

        retry_count = self._int(
            self._first_present(
                task.get("retry_count"),
                execution.get("retry_count"),
                execution.get("retry_attempts"),
                metadata.get("retry_count"),
                metadata.get("retry_attempt"),
            ),
            0,
        )
        retry_threshold = self._int(
            self._first_present(
                task.get("max_retries"),
                execution.get("max_retries"),
                metadata.get("retry_threshold"),
                metadata.get("max_retries"),
                self.max_retry_attempts,
            ),
            self.max_retry_attempts,
        )
        task_status = self._lower(task.get("status") or execution.get("task_status"))
        execution_state = self._lower(
            execution.get("execution_state") or metadata.get("execution_state")
        )
        execution_status = self._lower(
            execution.get("status") or metadata.get("execution_status")
        )
        failed_signal = (
            task_status in FAILED_STATUSES
            or execution_state == EXECUTION_STATE_FAILED
            or execution_status in FAILED_STATUSES
        )
        task_id_mismatch = bool(
            task.get("task_id")
            and execution.get("task_id")
            and str(task.get("task_id")) != str(execution.get("task_id"))
        )

        return {
            "execution_id": str(execution_id) if execution_id else None,
            "task_id": str(task_id) if task_id else None,
            "runner_id": str(runner_id) if runner_id else None,
            "runtime_id": str(runtime_id) if runtime_id else None,
            "runtime_owner": str(runtime_owner) if runtime_owner else None,
            "execution_state": execution_state or None,
            "task_status": task_status or None,
            "failed_signal": failed_signal,
            "task_id_mismatch": task_id_mismatch,
            "runtime_owner_mismatch": bool(
                runtime_owner and str(runtime_owner) != self.runtime_owner
            ),
            "retry_count": max(0, retry_count),
            "retry_attempt": max(0, retry_count) + 1,
            "retry_threshold": max(0, retry_threshold),
            "retry_reason": (
                retry_reason
                or task.get("error")
                or execution.get("error")
                or metadata.get("retry_reason")
            ),
            "retry_duration_ms": self._int(metadata.get("retry_duration_ms"), 0),
        }

    def _task_snapshot(self, task: Task | dict[str, Any] | None) -> dict[str, Any]:
        if task is None:
            return {}
        if isinstance(task, dict):
            return {
                "task_id": task.get("task_id") or task.get("id"),
                "status": task.get("status") or task.get("task_status"),
                "retry_count": task.get("retry_count"),
                "max_retries": task.get("max_retries"),
                "runner_id": task.get("runner_id"),
                "runtime_id": task.get("runtime_id"),
                "runtime_owner": task.get("runtime_owner"),
                "error": task.get("error"),
            }
        return {
            "task_id": getattr(task, "id", None),
            "status": getattr(task, "status", None),
            "retry_count": getattr(task, "retry_count", None),
            "max_retries": getattr(task, "max_retries", None),
            "runner_id": getattr(task, "runner_id", None),
            "runtime_id": getattr(task, "runtime_id", None),
            "runtime_owner": self._task_runtime_owner(task),
            "error": getattr(task, "error", None),
        }

    def _task_runtime_owner(self, task: Task) -> str | None:
        runner_id = getattr(task, "runner_id", None)
        runtime_id = getattr(task, "runtime_id", None)
        if runner_id and runtime_id:
            return f"{runner_id}:{runtime_id}"
        return None

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

    def _result(
        self,
        status: str,
        success: bool,
        retry_state: str,
        retry_allowed: bool,
        runtime_protected: bool = True,
        retry_registered: bool = False,
        retry_started: bool = False,
        retry_id: str | None = None,
        context: dict[str, Any] | None = None,
        provider: dict[str, Any] | None = None,
        provider_available: bool = True,
        reasons: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        error: str | None = None,
        started: float | None = None,
    ) -> RetryControlResult:
        context = context or {}
        provider = provider or {}
        reasons = reasons or []
        now = datetime.now(timezone.utc).isoformat()
        retry_attempt = self._int(context.get("retry_attempt"), 0)
        retry_threshold = self._int(context.get("retry_threshold"), 0)
        return RetryControlResult(
            status=status,
            success=success,
            retry_state=retry_state,
            retry_allowed=retry_allowed,
            runtime_protected=runtime_protected,
            retry_registered=retry_registered,
            retry_started=retry_started,
            linkage_valid=not self._has_linkage_reason(reasons),
            ownership_consistent="runtime_owner_mismatch" not in reasons,
            threshold_valid="invalid_retry_threshold" not in reasons,
            retry_id=retry_id,
            execution_id=context.get("execution_id"),
            task_id=context.get("task_id"),
            runner_id=context.get("runner_id"),
            runtime_id=context.get("runtime_id"),
            runtime_owner=context.get("runtime_owner") or self.runtime_owner,
            execution_state=context.get("execution_state"),
            task_status=context.get("task_status"),
            provider_status=provider.get("status"),
            provider_available=(
                provider_available and "provider_unavailable" not in reasons
            ),
            retry_attempt=max(0, retry_attempt),
            retry_threshold=max(0, retry_threshold),
            retry_reason=context.get("retry_reason"),
            retry_started_at=now if retry_started else None,
            retry_duration_ms=0,
            active_retries=self._active_retries,
            max_concurrent_retries=self.max_concurrent_retries,
            runtime_retry_load=self._runtime_retry_load(),
            max_runtime_retry_load=self.max_runtime_retry_load,
            max_retry_duration_ms=self.max_retry_duration_ms,
            retry_control_overhead_ms=self._duration_ms(started),
            max_retry_overhead_ms=self.max_retry_overhead_ms,
            checked_at=now,
            metadata=dict(metadata or {}),
            reasons=tuple(reasons),
            error=error,
        )

    def _has_linkage_reason(self, reasons: list[str]) -> bool:
        return any(
            reason
            in {
                "missing_task_id",
                "missing_failed_execution_signal",
                "execution_task_mismatch",
            }
            for reason in reasons
        )

    def _runtime_retry_load(self) -> float | None:
        if self.max_concurrent_retries <= 0:
            return None
        return round(self._active_retries / self.max_concurrent_retries, 4)

    def _elapsed_ms(self, started_at: str | None, completed_at: str) -> int:
        if not started_at:
            return 0
        try:
            start = datetime.fromisoformat(started_at)
            end = datetime.fromisoformat(completed_at)
        except ValueError:
            return 0
        return max(0, int((end - start).total_seconds() * 1000))

    def _duration_ms(self, started: float | None) -> int:
        return int((time.perf_counter() - started) * 1000) if started else 0

    def _int(self, value: Any, default: int) -> int:
        try:
            if value is None:
                return int(default)
            return int(value)
        except (TypeError, ValueError):
            return int(default)

    def _first_present(self, *values: Any) -> Any:
        for value in values:
            if value is not None:
                return value
        return None

    def _lower(self, value: Any) -> str:
        return str(value or "").strip().lower()

    def _unique(self, reasons: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for reason in reasons:
            if reason and reason not in seen:
                seen.add(reason)
                unique.append(reason)
        return unique

    def _log_result(self, result: RetryControlResult) -> None:
        if result.status == "idle":
            logger.debug("retry_control: idle active_retries=%s", result.active_retries)
            return
        if result.status == "registered":
            logger.info(
                "retry_control: registered retry_id=%s task_id=%s attempt=%s/%s reason=%s",
                result.retry_id,
                result.task_id,
                result.retry_attempt,
                result.retry_threshold,
                result.retry_reason,
            )
            return
        if result.status == "executing":
            logger.info(
                "retry_control: started retry_id=%s task_id=%s attempt=%s/%s",
                result.retry_id,
                result.task_id,
                result.retry_attempt,
                result.retry_threshold,
            )
            return
        if result.status == "completed":
            logger.info(
                "retry_control: completed retry_id=%s task_id=%s duration_ms=%s",
                result.retry_id,
                result.task_id,
                result.retry_duration_ms,
            )
            return
        if result.status == "failed":
            logger.warning(
                "retry_control: failed retry_id=%s task_id=%s reasons=%s error=%s",
                result.retry_id,
                result.task_id,
                ",".join(result.reasons),
                result.error,
            )
            return
        if result.status == "error":
            logger.error(
                "retry_control: error reasons=%s error=%s",
                ",".join(result.reasons),
                result.error,
            )
            return
        logger.warning(
            "retry_control: rejected task_id=%s reasons=%s",
            result.task_id,
            ",".join(result.reasons),
        )
