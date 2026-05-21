"""
Controlled execution foundation for Hermes runtime.

This layer prepares and validates execution flow. It does not call AI
providers, deploy code, mutate tasks, retry execution, or run autonomous work.
"""
from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.models.task import Task
from app.runner.task_claiming import TASK_CLAIM_STATE_CLAIMED
from app.schemas.task import TaskStatus

logger = logging.getLogger(__name__)

EXECUTION_STATE_CLAIMED = "claimed"
EXECUTION_STATE_EXECUTING = "executing"
EXECUTION_STATE_COMPLETED = "completed"
EXECUTION_STATE_FAILED = "failed"

MetricProvider = Callable[[], float | int | None]


@dataclass(frozen=True)
class ExecutionContext:
    execution_id: str
    task_id: str
    task_title: str
    task_status: str
    runner_id: str
    runtime_id: str
    runtime_owner: str
    claim_state: str | None
    claimed_at: str | None
    execution_state: str = EXECUTION_STATE_CLAIMED
    phase: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    started_at: str | None = None
    finished_at: str | None = None
    max_duration_seconds: int = 0

    def execution_duration_ms(self) -> int:
        if not self.started_at:
            return 0
        start = datetime.fromisoformat(self.started_at)
        end = (
            datetime.fromisoformat(self.finished_at)
            if self.finished_at
            else datetime.now(timezone.utc)
        )
        return max(0, int((end - start).total_seconds() * 1000))

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "task_title": self.task_title,
            "task_status": self.task_status,
            "phase": self.phase,
            "runner_id": self.runner_id,
            "runtime_id": self.runtime_id,
            "runtime_owner": self.runtime_owner,
            "claim_state": self.claim_state,
            "claimed_at": self.claimed_at,
            "execution_state": self.execution_state,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "execution_duration_ms": self.execution_duration_ms(),
            "max_duration_seconds": self.max_duration_seconds,
        }


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    eligible: bool
    runner_id: str
    runtime_id: str
    runtime_owner: str
    execution_id: str | None = None
    execution_state: str | None = None
    task_id: str | None = None
    task_title: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    execution_duration_ms: int = 0
    active_executions: int = 0
    max_concurrent_executions: int = 0
    max_duration_seconds: int = 0
    max_runtime_load: float = 0.0
    runtime_load: float | None = None
    max_memory_mb: int = 0
    memory_usage_mb: float | None = None
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None
    context: ExecutionContext | None = None
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "eligible": self.eligible,
            "runner_id": self.runner_id,
            "runtime_id": self.runtime_id,
            "runtime_owner": self.runtime_owner,
            "execution_id": self.execution_id,
            "execution_state": self.execution_state,
            "task_id": self.task_id,
            "task_title": self.task_title,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "execution_duration_ms": self.execution_duration_ms,
            "active_executions": self.active_executions,
            "max_concurrent_executions": self.max_concurrent_executions,
            "max_duration_seconds": self.max_duration_seconds,
            "max_runtime_load": self.max_runtime_load,
            "runtime_load": self.runtime_load,
            "max_memory_mb": self.max_memory_mb,
            "memory_usage_mb": self.memory_usage_mb,
            "reasons": list(self.reasons),
            "error": self.error,
            "context": self.context.to_dict() if self.context else None,
            "duration_ms": self.duration_ms,
        }


class TaskExecutionRuntime:
    def __init__(
        self,
        runner_id: str = settings.RUNNER_ID,
        runtime_id: str = settings.RUNTIME_ID,
        max_concurrent_executions: int = (
            settings.TASK_EXECUTION_MAX_CONCURRENT_EXECUTIONS
        ),
        max_duration_seconds: int = settings.TASK_EXECUTION_MAX_DURATION_SECONDS,
        max_runtime_load: float = settings.TASK_EXECUTION_MAX_RUNTIME_LOAD,
        max_memory_mb: int = settings.TASK_EXECUTION_MAX_MEMORY_MB,
        runtime_load_provider: MetricProvider | None = None,
        memory_usage_provider: MetricProvider | None = None,
    ) -> None:
        self.runner_id = runner_id
        self.runtime_id = runtime_id
        self.runtime_owner = f"{runner_id}:{runtime_id}"
        self.max_concurrent_executions = max(
            1,
            int(max_concurrent_executions or 1),
        )
        self.max_duration_seconds = max(1, int(max_duration_seconds or 1))
        self.max_runtime_load = max(0.0, float(max_runtime_load or 0.0))
        self.max_memory_mb = max(0, int(max_memory_mb or 0))
        self.runtime_load_provider = runtime_load_provider
        self.memory_usage_provider = memory_usage_provider
        self._active_contexts: dict[str, ExecutionContext] = {}

    def prepare(
        self,
        task: Task,
        runtime_active: bool = True,
    ) -> ExecutionResult:
        started = time.perf_counter()
        try:
            reasons = self._eligibility_reasons(task, runtime_active)
            reasons.extend(self._limit_reasons())
            if reasons:
                result = self._result(
                    "rejected",
                    eligible=False,
                    reasons=reasons,
                    started=started,
                )
                self._log_result(result)
                return result

            context = self._build_context(task)
            result = self._result(
                "prepared",
                eligible=True,
                context=context,
                started=started,
            )
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._result(
                "error",
                eligible=False,
                reasons=["execution_prepare_failed"],
                error=str(exc),
                started=started,
            )
            self._log_result(result)
            return result

    def start(self, context: ExecutionContext) -> ExecutionResult:
        started = time.perf_counter()
        try:
            if context.execution_state != EXECUTION_STATE_CLAIMED:
                return self._invalid_transition(
                    context,
                    "start_requires_claimed_state",
                    started,
                )
            reasons = self._limit_reasons()
            if reasons:
                result = self._result(
                    "rejected",
                    eligible=False,
                    reasons=reasons,
                    context=context,
                    started=started,
                )
                self._log_result(result)
                return result

            executing = replace(
                context,
                execution_state=EXECUTION_STATE_EXECUTING,
                started_at=datetime.now(timezone.utc).isoformat(),
            )
            self._active_contexts[executing.execution_id] = executing
            result = self._result(
                "started",
                eligible=True,
                context=executing,
                started=started,
            )
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._result(
                "error",
                eligible=False,
                reasons=["execution_start_failed"],
                error=str(exc),
                context=context,
                started=started,
            )
            self._log_result(result)
            return result

    def complete(self, context: ExecutionContext) -> ExecutionResult:
        started = time.perf_counter()
        if context.execution_state != EXECUTION_STATE_EXECUTING:
            return self._invalid_transition(
                context,
                "complete_requires_executing_state",
                started,
            )

        completed = replace(
            context,
            execution_state=EXECUTION_STATE_COMPLETED,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
        self._active_contexts.pop(context.execution_id, None)
        result = self._result(
            "completed",
            eligible=True,
            context=completed,
            started=started,
        )
        self._log_result(result)
        return result

    def fail(self, context: ExecutionContext, error: str) -> ExecutionResult:
        started = time.perf_counter()
        failed = replace(
            context,
            execution_state=EXECUTION_STATE_FAILED,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
        self._active_contexts.pop(context.execution_id, None)
        result = self._result(
            "error",
            eligible=False,
            reasons=["execution_error_contained"],
            error=error or "unknown_execution_error",
            context=failed,
            started=started,
        )
        self._log_result(result)
        return result

    def check_duration(self, context: ExecutionContext) -> ExecutionResult:
        started = time.perf_counter()
        if context.execution_state != EXECUTION_STATE_EXECUTING:
            return self._invalid_transition(
                context,
                "duration_check_requires_executing_state",
                started,
            )
        if context.execution_duration_ms() <= self.max_duration_seconds * 1000:
            return self._result(
                "within_limits",
                eligible=True,
                context=context,
                started=started,
            )
        return self._result(
            "rejected",
            eligible=False,
            reasons=["max_execution_duration_exceeded"],
            context=context,
            started=started,
        )

    def visibility(self) -> dict[str, Any]:
        active = [context.to_dict() for context in self._active_contexts.values()]
        return {
            "runtime_owner": self.runtime_owner,
            "active_executions": len(active),
            "max_concurrent_executions": self.max_concurrent_executions,
            "max_duration_seconds": self.max_duration_seconds,
            "max_runtime_load": self.max_runtime_load,
            "runtime_load": self._runtime_load(),
            "max_memory_mb": self.max_memory_mb,
            "memory_usage_mb": self._memory_usage_mb(),
            "active_contexts": active,
        }

    def _build_context(self, task: Task) -> ExecutionContext:
        claimed_at = getattr(task, "claimed_at", None)
        if isinstance(claimed_at, datetime):
            claimed_at_value = claimed_at.isoformat()
        else:
            claimed_at_value = str(claimed_at) if claimed_at else None

        return ExecutionContext(
            execution_id=str(uuid4()),
            task_id=str(getattr(task, "id")),
            task_title=str(getattr(task, "title")),
            task_status=str(getattr(task, "status")),
            phase=getattr(task, "phase", None),
            runner_id=self.runner_id,
            runtime_id=self.runtime_id,
            runtime_owner=self.runtime_owner,
            claim_state=getattr(task, "claim_state", None),
            claimed_at=claimed_at_value,
            max_duration_seconds=self.max_duration_seconds,
        )

    def _eligibility_reasons(self, task: Task, runtime_active: bool) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not getattr(task, "id", None):
            reasons.append("missing_task_id")
        if not getattr(task, "title", None):
            reasons.append("missing_task_title")
        if getattr(task, "status", None) != TaskStatus.claimed.value:
            reasons.append("task_not_claimed")
        if getattr(task, "runner_id", None) != self.runner_id:
            reasons.append("invalid_runner_owner")
        if getattr(task, "runtime_id", None) != self.runtime_id:
            reasons.append("invalid_runtime_owner")
        if getattr(task, "claim_state", None) != TASK_CLAIM_STATE_CLAIMED:
            reasons.append("invalid_claim_state")
        if getattr(task, "claimed_at", None) is None:
            reasons.append("missing_claimed_at")
        return reasons

    def _limit_reasons(self) -> list[str]:
        reasons: list[str] = []
        if len(self._active_contexts) >= self.max_concurrent_executions:
            reasons.append("max_concurrent_executions_reached")

        runtime_load = self._runtime_load()
        if (
            runtime_load is not None
            and self.max_runtime_load > 0
            and runtime_load > self.max_runtime_load
        ):
            reasons.append("max_runtime_load_reached")

        memory_usage_mb = self._memory_usage_mb()
        if (
            memory_usage_mb is not None
            and self.max_memory_mb > 0
            and memory_usage_mb > self.max_memory_mb
        ):
            reasons.append("max_execution_memory_reached")
        return reasons

    def _runtime_load(self) -> float | None:
        if self.runtime_load_provider is not None:
            value = self.runtime_load_provider()
            return float(value) if value is not None else None
        if self.max_concurrent_executions <= 0:
            return None
        return round(len(self._active_contexts) / self.max_concurrent_executions, 4)

    def _memory_usage_mb(self) -> float | None:
        if self.memory_usage_provider is not None:
            value = self.memory_usage_provider()
            return float(value) if value is not None else None
        statm_path = Path("/proc/self/statm")
        if os.name != "posix" or not statm_path.exists():
            return None
        try:
            resident_pages = int(statm_path.read_text().split()[1])
            page_size = os.sysconf("SC_PAGE_SIZE")
            return round((resident_pages * page_size) / (1024 * 1024), 2)
        except Exception:
            return None

    def _invalid_transition(
        self,
        context: ExecutionContext,
        reason: str,
        started: float,
    ) -> ExecutionResult:
        result = self._result(
            "rejected",
            eligible=False,
            reasons=[reason],
            context=context,
            started=started,
        )
        self._log_result(result)
        return result

    def _result(
        self,
        status: str,
        eligible: bool,
        reasons: list[str] | None = None,
        error: str | None = None,
        context: ExecutionContext | None = None,
        started: float | None = None,
    ) -> ExecutionResult:
        duration_ms = 0
        if started is not None:
            duration_ms = int((time.perf_counter() - started) * 1000)

        return ExecutionResult(
            status=status,
            eligible=eligible,
            runner_id=self.runner_id,
            runtime_id=self.runtime_id,
            runtime_owner=self.runtime_owner,
            execution_id=context.execution_id if context else None,
            execution_state=context.execution_state if context else None,
            task_id=context.task_id if context else None,
            task_title=context.task_title if context else None,
            started_at=context.started_at if context else None,
            finished_at=context.finished_at if context else None,
            execution_duration_ms=(
                context.execution_duration_ms() if context else 0
            ),
            active_executions=len(self._active_contexts),
            max_concurrent_executions=self.max_concurrent_executions,
            max_duration_seconds=self.max_duration_seconds,
            max_runtime_load=self.max_runtime_load,
            runtime_load=self._runtime_load(),
            max_memory_mb=self.max_memory_mb,
            memory_usage_mb=self._memory_usage_mb(),
            reasons=tuple(reasons or []),
            error=error,
            context=context,
            duration_ms=duration_ms,
        )

    def _log_result(self, result: ExecutionResult) -> None:
        if result.status in {"prepared", "started", "completed"}:
            logger.info(
                "task_execution: %s execution_id=%s task_id=%s state=%s duration_ms=%s",
                result.status,
                result.execution_id,
                result.task_id,
                result.execution_state,
                result.execution_duration_ms,
            )
            return
        if result.status == "error":
            logger.error(
                "task_execution: error execution_id=%s task_id=%s reasons=%s error=%s",
                result.execution_id,
                result.task_id,
                ",".join(result.reasons),
                result.error,
            )
            return
        logger.warning(
            "task_execution: rejected execution_id=%s task_id=%s reasons=%s",
            result.execution_id,
            result.task_id,
            ",".join(result.reasons),
        )
