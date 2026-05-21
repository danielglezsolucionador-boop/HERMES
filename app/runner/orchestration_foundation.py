"""
Controlled orchestration foundation for Hermes execution runtime.

This layer validates coordination intent, dependency state, and execution
ordering. It does not schedule work autonomously, route AI decisions, recover
executions, call providers, or mutate database state.
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
from app.runner.task_execution import EXECUTION_STATE_CLAIMED

logger = logging.getLogger(__name__)

DEPENDENCY_READY_STATES = {"completed", "released", "satisfied", "skipped"}
ORCHESTRATION_ACTIVE_STATES = {"registered", "coordinating"}


@dataclass(frozen=True)
class OrchestrationResult:
    status: str
    success: bool
    orchestration_state: str
    dependency_state: str
    coordination_state: str
    dependency_status: str
    coordination_allowed: bool
    runtime_protected: bool
    orchestration_registered: bool = False
    coordination_registered: bool = False
    coordination_started: bool = False
    coordination_completed: bool = False
    execution_released: bool = False
    conflict_detected: bool = False
    linkage_valid: bool = True
    ownership_consistent: bool = True
    dependency_valid: bool = True
    sequencing_valid: bool = True
    orchestration_id: str | None = None
    coordination_id: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    runner_id: str | None = None
    runtime_id: str | None = None
    runtime_owner: str | None = None
    execution_state: str | None = None
    task_status: str | None = None
    execution_order: int = 0
    execution_sequence: int = 0
    dependency_count: int = 0
    max_execution_dependencies: int = 0
    max_dependency_chain: int = 0
    active_orchestrations: int = 0
    max_active_orchestrations: int = 0
    runtime_orchestration_load: float | None = None
    max_orchestration_load: float = 0.0
    max_orchestration_duration_ms: int = 0
    coordination_overhead_ms: int = 0
    max_coordination_overhead_ms: int = 0
    coordination_started_at: str | None = None
    coordination_completed_at: str | None = None
    coordination_duration_ms: int = 0
    checked_at: str | None = None
    dependencies: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success": self.success,
            "orchestration_state": self.orchestration_state,
            "dependency_state": self.dependency_state,
            "coordination_state": self.coordination_state,
            "dependency_status": self.dependency_status,
            "coordination_allowed": self.coordination_allowed,
            "runtime_protected": self.runtime_protected,
            "orchestration_registered": self.orchestration_registered,
            "coordination_registered": self.coordination_registered,
            "coordination_started": self.coordination_started,
            "coordination_completed": self.coordination_completed,
            "execution_released": self.execution_released,
            "conflict_detected": self.conflict_detected,
            "linkage_valid": self.linkage_valid,
            "ownership_consistent": self.ownership_consistent,
            "dependency_valid": self.dependency_valid,
            "sequencing_valid": self.sequencing_valid,
            "orchestration_id": self.orchestration_id,
            "coordination_id": self.coordination_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "runner_id": self.runner_id,
            "runtime_id": self.runtime_id,
            "runtime_owner": self.runtime_owner,
            "execution_state": self.execution_state,
            "task_status": self.task_status,
            "execution_order": self.execution_order,
            "execution_sequence": self.execution_sequence,
            "dependency_count": self.dependency_count,
            "max_execution_dependencies": self.max_execution_dependencies,
            "max_dependency_chain": self.max_dependency_chain,
            "active_orchestrations": self.active_orchestrations,
            "max_active_orchestrations": self.max_active_orchestrations,
            "runtime_orchestration_load": self.runtime_orchestration_load,
            "max_orchestration_load": self.max_orchestration_load,
            "max_orchestration_duration_ms": self.max_orchestration_duration_ms,
            "coordination_overhead_ms": self.coordination_overhead_ms,
            "max_coordination_overhead_ms": self.max_coordination_overhead_ms,
            "coordination_started_at": self.coordination_started_at,
            "coordination_completed_at": self.coordination_completed_at,
            "coordination_duration_ms": self.coordination_duration_ms,
            "checked_at": self.checked_at,
            "dependencies": [dict(item) for item in self.dependencies],
            "metadata": dict(self.metadata),
            "reasons": list(self.reasons),
            "error": self.error,
        }


class OrchestrationRuntime:
    def __init__(
        self,
        runtime_owner: str = f"{settings.RUNNER_ID}:{settings.RUNTIME_ID}",
        max_active_orchestrations: int = settings.ORCHESTRATION_MAX_ACTIVE,
        max_execution_dependencies: int = settings.ORCHESTRATION_MAX_DEPENDENCIES,
        max_dependency_chain: int = settings.ORCHESTRATION_MAX_DEPENDENCY_CHAIN,
        max_orchestration_duration_ms: int = (
            settings.ORCHESTRATION_MAX_DURATION_MS
        ),
        max_orchestration_load: float = settings.ORCHESTRATION_MAX_RUNTIME_LOAD,
        max_coordination_overhead_ms: int = settings.ORCHESTRATION_MAX_OVERHEAD_MS,
    ) -> None:
        self.runtime_owner = runtime_owner
        self.max_active_orchestrations = max(
            1,
            int(max_active_orchestrations or 1),
        )
        self.max_execution_dependencies = max(
            0,
            int(max_execution_dependencies or 0),
        )
        self.max_dependency_chain = max(
            1,
            int(max_dependency_chain or 1),
        )
        self.max_orchestration_duration_ms = max(
            1,
            int(max_orchestration_duration_ms or 1),
        )
        self.max_orchestration_load = max(
            0.0,
            float(max_orchestration_load or 0.0),
        )
        self.max_coordination_overhead_ms = max(
            1,
            int(max_coordination_overhead_ms or 1),
        )
        self._active_orchestrations = 0

    async def inspect(
        self,
        execution_context: Any | None = None,
        execution_result: Any | None = None,
        task: Task | dict[str, Any] | None = None,
        dependencies: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
        execution_order: int | None = None,
        runtime_active: bool = True,
        coordination_permitted: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> OrchestrationResult:
        return self.evaluate(
            execution_context=execution_context,
            execution_result=execution_result,
            task=task,
            dependencies=dependencies,
            execution_order=execution_order,
            runtime_active=runtime_active,
            coordination_permitted=coordination_permitted,
            metadata=metadata,
        )

    async def coordinate(
        self,
        execution_context: Any | None = None,
        execution_result: Any | None = None,
        task: Task | dict[str, Any] | None = None,
        dependencies: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
        execution_order: int | None = None,
        runtime_active: bool = True,
        coordination_permitted: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> OrchestrationResult:
        registered: OrchestrationResult | None = None
        try:
            flow_metadata = dict(metadata or {})
            flow_metadata.setdefault("coordination_flow", "queued")
            registered = self.evaluate(
                execution_context=execution_context,
                execution_result=execution_result,
                task=task,
                dependencies=dependencies,
                execution_order=execution_order,
                runtime_active=runtime_active,
                coordination_permitted=coordination_permitted,
                metadata=flow_metadata,
            )
            if registered.status != "registered":
                return registered

            coordinating = self.start(registered)
            if coordinating.status != "coordinating":
                return coordinating
            return self.release(coordinating)
        except Exception as exc:
            if (
                registered is not None
                and registered.status in ORCHESTRATION_ACTIVE_STATES
            ):
                self._active_orchestrations = max(
                    0,
                    self._active_orchestrations - 1,
                )
            result = self._result(
                status="error",
                success=False,
                orchestration_state="error",
                dependency_state="unknown",
                coordination_allowed=False,
                runtime_protected=True,
                reasons=["coordination_error_contained"],
                error=str(exc),
                metadata=metadata,
                started=None,
            )
            self._log_result(result)
            return result

    def evaluate(
        self,
        execution_context: Any | None = None,
        execution_result: Any | None = None,
        task: Task | dict[str, Any] | None = None,
        dependencies: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
        execution_order: int | None = None,
        runtime_active: bool = True,
        coordination_permitted: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> OrchestrationResult:
        started = time.perf_counter()
        active_registered = False
        try:
            execution = self._execution_snapshot(execution_context, execution_result)
            task_data = self._task_snapshot(task)
            dependency_data = self._dependencies(dependencies)
            context = self._orchestration_context(
                execution=execution,
                task=task_data,
                dependencies=dependency_data,
                execution_order=execution_order,
                metadata=metadata,
            )
            reasons = self._preflight_reasons(
                runtime_active=runtime_active,
                coordination_permitted=coordination_permitted,
            )
            requested = self._orchestration_requested(
                execution=execution,
                task=task_data,
                dependencies=dependency_data,
                execution_order=execution_order,
                metadata=metadata,
            )
            if not requested:
                result = self._result(
                    status="idle",
                    success=True,
                    orchestration_state="ready",
                    dependency_state="clear",
                    coordination_allowed=not reasons,
                    context=context,
                    dependencies=dependency_data,
                    reasons=reasons,
                    metadata=metadata,
                    started=started,
                )
                self._log_result(result)
                return result

            reasons.extend(self._context_reasons(context))
            reasons.extend(self._dependency_reasons(dependency_data, context))
            reasons.extend(self._limit_reasons(context, dependency_data, started))
            unique_reasons = self._unique(reasons)
            if unique_reasons:
                result = self._result(
                    status="rejected",
                    success=False,
                    orchestration_state="rejected",
                    dependency_state=self._dependency_state(dependency_data),
                    coordination_allowed=False,
                    context=context,
                    dependencies=dependency_data,
                    reasons=unique_reasons,
                    metadata=metadata,
                    started=started,
                )
                self._log_result(result)
                return result

            self._active_orchestrations += 1
            active_registered = True
            coordination_id = str(uuid4())
            result = self._result(
                status="registered",
                success=True,
                orchestration_state="registered",
                dependency_state=self._dependency_state(dependency_data),
                coordination_allowed=True,
                orchestration_registered=True,
                orchestration_id=coordination_id,
                context=context,
                dependencies=dependency_data,
                metadata=metadata,
                started=started,
            )
            self._log_result(result)
            return result
        except Exception as exc:
            if active_registered:
                self._active_orchestrations = max(
                    0,
                    self._active_orchestrations - 1,
                )
            result = self._result(
                status="error",
                success=False,
                orchestration_state="error",
                dependency_state="unknown",
                coordination_allowed=False,
                runtime_protected=True,
                reasons=["orchestration_error_contained"],
                error=str(exc),
                metadata=metadata,
                started=started,
            )
            self._log_result(result)
            return result

    def start(self, result: OrchestrationResult) -> OrchestrationResult:
        if result.status != "registered" or not result.orchestration_registered:
            rejected = self._invalid_transition(
                result,
                "orchestration_start_requires_registered_state",
            )
            self._log_result(rejected)
            return rejected
        updated = replace(
            result,
            status="coordinating",
            orchestration_state="coordinating",
            coordination_state="coordinating",
            coordination_started=True,
            coordination_started_at=datetime.now(timezone.utc).isoformat(),
            active_orchestrations=self._active_orchestrations,
            runtime_orchestration_load=self._runtime_orchestration_load(),
        )
        self._log_result(updated)
        return updated

    def release(self, result: OrchestrationResult) -> OrchestrationResult:
        return self._finish(
            result=result,
            status="released",
            orchestration_state="released",
            success=True,
            coordination_completed=True,
            execution_released=True,
        )

    def fail(
        self,
        result: OrchestrationResult,
        error: str = "unknown_orchestration_failure",
    ) -> OrchestrationResult:
        return self._finish(
            result=result,
            status="failed",
            orchestration_state="failed",
            success=False,
            reasons=["orchestration_failed"],
            error=error or "unknown_orchestration_failure",
        )

    def visibility(self) -> dict[str, Any]:
        return {
            "active_orchestrations": self._active_orchestrations,
            "max_active_orchestrations": self.max_active_orchestrations,
            "runtime_orchestration_load": self._runtime_orchestration_load(),
            "max_orchestration_load": self.max_orchestration_load,
            "max_execution_dependencies": self.max_execution_dependencies,
            "max_dependency_chain": self.max_dependency_chain,
            "max_orchestration_duration_ms": self.max_orchestration_duration_ms,
            "max_coordination_overhead_ms": self.max_coordination_overhead_ms,
            "runtime_owner": self.runtime_owner,
        }

    def _finish(
        self,
        result: OrchestrationResult,
        status: str,
        orchestration_state: str,
        success: bool,
        coordination_completed: bool = False,
        execution_released: bool = False,
        reasons: list[str] | None = None,
        error: str | None = None,
    ) -> OrchestrationResult:
        if result.status not in ORCHESTRATION_ACTIVE_STATES:
            rejected = self._invalid_transition(
                result,
                "orchestration_release_requires_active_state",
            )
            self._log_result(rejected)
            return rejected

        self._active_orchestrations = max(0, self._active_orchestrations - 1)
        completed_at = datetime.now(timezone.utc).isoformat()
        started_at = result.coordination_started_at or result.checked_at
        duration_ms = self._elapsed_ms(started_at, completed_at)
        final_reasons = self._unique(list(result.reasons) + list(reasons or []))
        updated = replace(
            result,
            status=status,
            success=success,
            orchestration_state=orchestration_state,
            coordination_state=orchestration_state,
            coordination_allowed=success,
            orchestration_registered=False,
            coordination_registered=False,
            coordination_completed=coordination_completed,
            execution_released=execution_released,
            coordination_completed_at=completed_at,
            coordination_duration_ms=duration_ms,
            active_orchestrations=self._active_orchestrations,
            runtime_orchestration_load=self._runtime_orchestration_load(),
            reasons=tuple(final_reasons),
            error=error,
        )
        self._log_result(updated)
        return updated

    def _invalid_transition(
        self,
        result: OrchestrationResult,
        reason: str,
    ) -> OrchestrationResult:
        return replace(
            result,
            status="rejected",
            success=False,
            orchestration_state="rejected",
            coordination_state="rejected",
            coordination_allowed=False,
            reasons=tuple(self._unique(list(result.reasons) + [reason])),
        )

    def _orchestration_requested(
        self,
        execution: dict[str, Any],
        task: dict[str, Any],
        dependencies: list[dict[str, Any]],
        execution_order: int | None,
        metadata: dict[str, Any] | None,
    ) -> bool:
        if execution or task or dependencies or execution_order is not None:
            return True
        if metadata and any(
            key in metadata
            for key in (
                "orchestration_id",
                "execution_id",
                "task_id",
                "execution_order",
                "dependencies",
            )
        ):
            return True
        return False

    def _preflight_reasons(
        self,
        runtime_active: bool,
        coordination_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not coordination_permitted:
            reasons.append("coordination_not_permitted")
        return reasons

    def _context_reasons(self, context: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        if not context.get("execution_id"):
            reasons.append("missing_execution_id")
        if not context.get("task_id"):
            reasons.append("missing_task_id")
        if not context.get("runtime_owner"):
            reasons.append("missing_runtime_owner")
        elif context.get("runtime_owner") != self.runtime_owner:
            reasons.append("runtime_owner_mismatch")
        if context.get("task_id_mismatch"):
            reasons.append("execution_task_mismatch")
        if context.get("execution_state") != EXECUTION_STATE_CLAIMED:
            reasons.append("execution_not_claimed")
        if context.get("execution_order", 0) <= 0:
            reasons.append("invalid_execution_order")
        return reasons

    def _dependency_reasons(
        self,
        dependencies: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[str]:
        reasons: list[str] = []
        seen_dependencies: set[str] = set()
        current_execution_id = context.get("execution_id")
        current_task_id = context.get("task_id")
        current_order = self._int(context.get("execution_order"), 0)
        for dependency in dependencies:
            dependency_key = self._dependency_key(dependency)
            if not dependency_key:
                reasons.append("orphan_dependency")
            elif dependency_key in seen_dependencies:
                reasons.append("duplicate_dependency")
            else:
                seen_dependencies.add(dependency_key)
            if (
                dependency.get("execution_id")
                and current_execution_id
                and str(dependency.get("execution_id")) == str(current_execution_id)
            ) or (
                dependency.get("task_id")
                and current_task_id
                and str(dependency.get("task_id")) == str(current_task_id)
            ):
                reasons.append("dependency_self_reference")
            if not dependency.get("state"):
                reasons.append("missing_dependency_state")
            elif (
                dependency.get("required", True)
                and dependency.get("state") not in DEPENDENCY_READY_STATES
            ):
                reasons.append("dependency_unsatisfied")
            order = self._int(dependency.get("execution_order"), 0)
            if order < 0:
                reasons.append("invalid_dependency_order")
            if current_order > 0 and order >= current_order:
                reasons.append("invalid_execution_sequence")
            if self._dependency_chain_depth(dependency) > self.max_dependency_chain:
                reasons.append("max_dependency_chain_reached")
        return reasons

    def _limit_reasons(
        self,
        context: dict[str, Any],
        dependencies: list[dict[str, Any]],
        started: float,
    ) -> list[str]:
        reasons: list[str] = []
        if self._active_orchestrations >= self.max_active_orchestrations:
            reasons.append("max_active_orchestrations_reached")
        runtime_load = self._runtime_orchestration_load()
        if (
            runtime_load is not None
            and self.max_orchestration_load > 0
            and runtime_load > self.max_orchestration_load
        ):
            reasons.append("max_orchestration_load_reached")
        if len(dependencies) > self.max_execution_dependencies:
            reasons.append("max_execution_dependencies_reached")
        duration_ms = self._int(context.get("coordination_duration_ms"), 0)
        if duration_ms > self.max_orchestration_duration_ms:
            reasons.append("max_orchestration_duration_reached")
        if self._duration_ms(started) > self.max_coordination_overhead_ms:
            reasons.append("coordination_overhead_exceeded")
        return reasons

    def _orchestration_context(
        self,
        execution: dict[str, Any],
        task: dict[str, Any],
        dependencies: list[dict[str, Any]],
        execution_order: int | None,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        metadata = dict(metadata or {})
        task_id = (
            execution.get("task_id")
            or task.get("task_id")
            or metadata.get("task_id")
        )
        execution_id = (
            execution.get("execution_id") or metadata.get("execution_id")
        )
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

        order = self._int(
            self._first_present(
                execution_order,
                execution.get("execution_order"),
                metadata.get("execution_order"),
                1,
            ),
            1,
        )

        return {
            "execution_id": str(execution_id) if execution_id else None,
            "task_id": str(task_id) if task_id else None,
            "runner_id": str(runner_id) if runner_id else None,
            "runtime_id": str(runtime_id) if runtime_id else None,
            "runtime_owner": str(runtime_owner) if runtime_owner else None,
            "execution_state": self._lower(
                execution.get("execution_state")
                or metadata.get("execution_state")
                or EXECUTION_STATE_CLAIMED
            ),
            "task_status": self._lower(
                task.get("status")
                or execution.get("task_status")
                or metadata.get("task_status")
            ),
            "execution_order": max(0, order),
            "task_id_mismatch": bool(
                execution.get("task_id")
                and task.get("task_id")
                and str(execution.get("task_id")) != str(task.get("task_id"))
            ),
            "coordination_duration_ms": self._int(
                metadata.get("coordination_duration_ms"),
                0,
            ),
            "dependency_count": len(dependencies),
        }

    def _execution_snapshot(
        self,
        execution_context: Any | None,
        execution_result: Any | None,
    ) -> dict[str, Any]:
        result = self._as_dict(execution_result)
        context = self._as_dict(execution_context)
        if not context and isinstance(result.get("context"), dict):
            context = dict(result.get("context") or {})
        merged = dict(result)
        merged.update(context)
        return merged

    def _task_snapshot(self, task: Task | dict[str, Any] | None) -> dict[str, Any]:
        if task is None:
            return {}
        if isinstance(task, dict):
            return {
                "task_id": task.get("task_id") or task.get("id"),
                "status": task.get("status") or task.get("task_status"),
                "runner_id": task.get("runner_id"),
                "runtime_id": task.get("runtime_id"),
                "runtime_owner": task.get("runtime_owner"),
            }
        return {
            "task_id": getattr(task, "id", None),
            "status": getattr(task, "status", None),
            "runner_id": getattr(task, "runner_id", None),
            "runtime_id": getattr(task, "runtime_id", None),
            "runtime_owner": self._task_runtime_owner(task),
        }

    def _dependencies(
        self,
        dependencies: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None,
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for index, dependency in enumerate(dependencies or [], start=1):
            if not isinstance(dependency, dict):
                normalized.append(
                    {
                        "dependency_id": None,
                        "execution_id": None,
                        "task_id": None,
                        "state": None,
                        "execution_order": index,
                    }
                )
                continue
            metadata = dict(dependency.get("metadata") or {})
            normalized.append(
                {
                    "dependency_id": dependency.get("dependency_id")
                    or dependency.get("id"),
                    "execution_id": dependency.get("execution_id"),
                    "task_id": dependency.get("task_id"),
                    "state": self._lower(
                        dependency.get("state")
                        or dependency.get("dependency_state")
                    ),
                    "execution_order": self._int(
                        dependency.get("execution_order")
                        or dependency.get("order")
                        or index,
                        index,
                    ),
                    "required": bool(dependency.get("required", True)),
                    "chain_depth": self._int(
                        dependency.get("chain_depth")
                        or dependency.get("dependency_chain_depth")
                        or metadata.get("chain_depth")
                        or metadata.get("dependency_chain_depth")
                        or 1,
                        1,
                    ),
                    "dependency_chain": self._list(
                        dependency.get("dependency_chain")
                        or metadata.get("dependency_chain")
                        or []
                    ),
                    "metadata": metadata,
                }
            )
        return normalized

    def _task_runtime_owner(self, task: Task) -> str | None:
        runner_id = getattr(task, "runner_id", None)
        runtime_id = getattr(task, "runtime_id", None)
        if runner_id and runtime_id:
            return f"{runner_id}:{runtime_id}"
        return None

    def _dependency_key(self, dependency: dict[str, Any]) -> str | None:
        for key in ("dependency_id", "execution_id", "task_id"):
            value = dependency.get(key)
            if value:
                return f"{key}:{value}"
        return None

    def _dependency_chain_depth(self, dependency: dict[str, Any]) -> int:
        chain = dependency.get("dependency_chain")
        if isinstance(chain, (list, tuple)):
            return max(self._int(dependency.get("chain_depth"), 1), len(chain))
        return self._int(dependency.get("chain_depth"), 1)

    def _dependency_state(self, dependencies: list[dict[str, Any]]) -> str:
        if not dependencies:
            return "clear"
        if all(
            (not item.get("required", True))
            or item.get("state") in DEPENDENCY_READY_STATES
            for item in dependencies
        ):
            return "satisfied"
        return "blocked"

    def _result(
        self,
        status: str,
        success: bool,
        orchestration_state: str,
        dependency_state: str,
        coordination_allowed: bool,
        runtime_protected: bool = True,
        orchestration_registered: bool = False,
        orchestration_id: str | None = None,
        context: dict[str, Any] | None = None,
        dependencies: list[dict[str, Any]] | None = None,
        reasons: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        error: str | None = None,
        started: float | None = None,
    ) -> OrchestrationResult:
        context = context or {}
        dependencies = dependencies or []
        reasons = reasons or []
        now = datetime.now(timezone.utc).isoformat()
        return OrchestrationResult(
            status=status,
            success=success,
            orchestration_state=orchestration_state,
            dependency_state=dependency_state,
            coordination_state=orchestration_state,
            dependency_status=dependency_state,
            coordination_allowed=coordination_allowed,
            runtime_protected=runtime_protected,
            orchestration_registered=orchestration_registered,
            coordination_registered=orchestration_registered,
            conflict_detected=self._has_conflict_reason(reasons),
            linkage_valid=not self._has_linkage_reason(reasons),
            ownership_consistent="runtime_owner_mismatch" not in reasons,
            dependency_valid=not self._has_dependency_reason(reasons),
            sequencing_valid=not self._has_sequencing_reason(reasons),
            orchestration_id=orchestration_id,
            coordination_id=orchestration_id,
            execution_id=context.get("execution_id"),
            task_id=context.get("task_id"),
            runner_id=context.get("runner_id"),
            runtime_id=context.get("runtime_id"),
            runtime_owner=context.get("runtime_owner") or self.runtime_owner,
            execution_state=context.get("execution_state"),
            task_status=context.get("task_status"),
            execution_order=max(0, self._int(context.get("execution_order"), 0)),
            execution_sequence=max(0, self._int(context.get("execution_order"), 0)),
            dependency_count=len(dependencies),
            max_execution_dependencies=self.max_execution_dependencies,
            max_dependency_chain=self.max_dependency_chain,
            active_orchestrations=self._active_orchestrations,
            max_active_orchestrations=self.max_active_orchestrations,
            runtime_orchestration_load=self._runtime_orchestration_load(),
            max_orchestration_load=self.max_orchestration_load,
            max_orchestration_duration_ms=self.max_orchestration_duration_ms,
            coordination_overhead_ms=self._duration_ms(started),
            max_coordination_overhead_ms=self.max_coordination_overhead_ms,
            checked_at=now,
            dependencies=tuple(dict(item) for item in dependencies),
            metadata=dict(metadata or {}),
            reasons=tuple(reasons),
            error=error,
        )

    def _has_linkage_reason(self, reasons: list[str]) -> bool:
        return any(
            reason
            in {
                "missing_execution_id",
                "missing_task_id",
                "missing_runtime_owner",
                "execution_task_mismatch",
                "execution_not_claimed",
                "invalid_execution_order",
                "invalid_execution_sequence",
            }
            for reason in reasons
        )

    def _has_dependency_reason(self, reasons: list[str]) -> bool:
        return any(
            reason
            in {
                "orphan_dependency",
                "missing_dependency_state",
                "dependency_unsatisfied",
                "invalid_dependency_order",
                "invalid_execution_sequence",
                "duplicate_dependency",
                "dependency_self_reference",
                "max_execution_dependencies_reached",
                "max_dependency_chain_reached",
            }
            for reason in reasons
        )

    def _has_sequencing_reason(self, reasons: list[str]) -> bool:
        return any(
            reason
            in {
                "invalid_execution_order",
                "invalid_execution_sequence",
                "invalid_dependency_order",
                "duplicate_dependency",
                "dependency_self_reference",
            }
            for reason in reasons
        )

    def _has_conflict_reason(self, reasons: list[str]) -> bool:
        return any(
            reason
            in {
                "runtime_owner_mismatch",
                "execution_task_mismatch",
                "dependency_unsatisfied",
                "invalid_execution_sequence",
                "duplicate_dependency",
                "dependency_self_reference",
                "max_active_orchestrations_reached",
                "max_orchestration_load_reached",
                "max_dependency_chain_reached",
            }
            for reason in reasons
        )

    def _runtime_orchestration_load(self) -> float | None:
        if self.max_active_orchestrations <= 0:
            return None
        return round(self._active_orchestrations / self.max_active_orchestrations, 4)

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

    def _lower(self, value: Any) -> str:
        return str(value or "").strip().lower()

    def _first_present(self, *values: Any) -> Any:
        for value in values:
            if value is not None:
                return value
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

    def _list(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return list(value)
        if isinstance(value, tuple):
            return list(value)
        return [value]

    def _unique(self, reasons: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for reason in reasons:
            if reason and reason not in seen:
                seen.add(reason)
                unique.append(reason)
        return unique

    def _log_result(self, result: OrchestrationResult) -> None:
        if result.status == "idle":
            logger.debug(
                "orchestration coordination: idle active_orchestrations=%s",
                result.active_orchestrations,
            )
            return
        if result.status == "registered":
            logger.info(
                "orchestration coordination: registered coordination_id=%s execution_id=%s sequence=%s dependencies=%s",
                result.coordination_id,
                result.execution_id,
                result.execution_sequence,
                result.dependency_count,
            )
            return
        if result.status == "coordinating":
            logger.info(
                "orchestration coordination: started coordination_id=%s execution_id=%s",
                result.coordination_id,
                result.execution_id,
            )
            return
        if result.status == "released":
            logger.info(
                "orchestration coordination: completed coordination_id=%s execution_id=%s duration_ms=%s",
                result.coordination_id,
                result.execution_id,
                result.coordination_duration_ms,
            )
            return
        if result.status == "failed":
            logger.warning(
                "orchestration coordination: failed coordination_id=%s execution_id=%s reasons=%s error=%s",
                result.coordination_id,
                result.execution_id,
                ",".join(result.reasons),
                result.error,
            )
            return
        if result.status == "error":
            logger.error(
                "orchestration coordination: error reasons=%s error=%s",
                ",".join(result.reasons),
                result.error,
            )
            return
        logger.warning(
            "orchestration coordination: rejected execution_id=%s reasons=%s",
            result.execution_id,
            ",".join(result.reasons),
        )
