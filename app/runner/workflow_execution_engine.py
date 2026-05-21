"""
Controlled workflow execution engine for Hermes operational workflows.

This layer validates and executes declared workflow steps in order. It records
execution state and visibility, but it does not run external code, alter
roadmaps, bypass checkpoints, or change runtime loop behavior.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

WORKFLOW_EXECUTION_STATUS_COMPLETED = "completed"
WORKFLOW_EXECUTION_STATUS_BLOCKED = "blocked"
WORKFLOW_EXECUTION_STATUS_ERROR = "error"

APPROVED_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "governance_approved",
    "authorized_by_human",
}
CLEAR_CHECKPOINT_STATUSES = {
    "approved",
    "clear",
    "not_required",
    "human_approved",
}
VALID_CONTINUATION_STATUSES = {"ready", "active", "continued", "resumed"}
SAFE_RUNTIME_STATES = {"active", "online", "ready", "stable"}


@dataclass(frozen=True)
class WorkflowExecutionEngineRequest:
    workflow_id: str | None = None
    workflow_objective: str | None = None
    execution_steps: tuple[Any, ...] = field(default_factory=tuple)
    completed_steps: tuple[str, ...] = field(default_factory=tuple)
    official_workflows: tuple[str, ...] = field(default_factory=tuple)
    execution_state: str | None = "ready"
    continuation_status: str | None = "ready"
    governance_status: str | None = "approved"
    checkpoint_status: str | None = "not_required"
    runtime_state: dict[str, Any] = field(default_factory=dict)
    operational_dependencies: tuple[str, ...] = field(default_factory=tuple)
    satisfied_dependencies: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    workflow_authorized: bool = True
    runtime_integrity_valid: bool = True
    operational_stability_valid: bool = True
    governance_consistency_valid: bool = True
    invent_workflow_requested: bool = False
    alter_execution_sequence_requested: bool = False
    ignore_human_checkpoints_requested: bool = False
    break_execution_continuity_requested: bool = False
    overwrite_operational_controls_requested: bool = False
    hide_execution_failures_requested: bool = False
    minimize_blocking_conditions_requested: bool = False
    falsify_workflow_completion_requested: bool = False
    ignore_runtime_inconsistencies_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowExecutionEngineResult:
    status: str
    success: bool
    execution_id: str
    workflow_id: str | None
    workflow_objective: str | None
    execution_state: str | None
    continuation_status: str | None
    governance_status: str | None
    checkpoint_status: str | None
    workflow_consistency_valid: bool
    runtime_integrity_valid: bool
    governance_alignment_valid: bool
    execution_continuity_valid: bool
    operational_stability_valid: bool
    execution_sequencing_controlled: bool
    workflow_integrity_preserved: bool
    execution_traceability_preserved: bool
    workflow_completion_confirmed: bool
    execution_steps: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    executed_steps: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    pending_steps: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    missing_dependencies: tuple[str, ...] = field(default_factory=tuple)
    human_visibility_payload: dict[str, Any] = field(default_factory=dict)
    execution_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int = 0
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success": self.success,
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "workflow_objective": self.workflow_objective,
            "execution_state": self.execution_state,
            "continuation_status": self.continuation_status,
            "governance_status": self.governance_status,
            "checkpoint_status": self.checkpoint_status,
            "workflow_consistency_valid": self.workflow_consistency_valid,
            "runtime_integrity_valid": self.runtime_integrity_valid,
            "governance_alignment_valid": self.governance_alignment_valid,
            "execution_continuity_valid": self.execution_continuity_valid,
            "operational_stability_valid": self.operational_stability_valid,
            "execution_sequencing_controlled": (
                self.execution_sequencing_controlled
            ),
            "workflow_integrity_preserved": self.workflow_integrity_preserved,
            "execution_traceability_preserved": (
                self.execution_traceability_preserved
            ),
            "workflow_completion_confirmed": self.workflow_completion_confirmed,
            "execution_steps": [dict(step) for step in self.execution_steps],
            "executed_steps": [dict(step) for step in self.executed_steps],
            "pending_steps": [dict(step) for step in self.pending_steps],
            "blocking_conditions": list(self.blocking_conditions),
            "missing_dependencies": list(self.missing_dependencies),
            "human_visibility_payload": dict(self.human_visibility_payload),
            "execution_lifecycle": [
                dict(entry) for entry in self.execution_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class WorkflowExecutionEngine:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def execute(
        self,
        request: WorkflowExecutionEngineRequest,
        execution_permitted: bool = True,
    ) -> WorkflowExecutionEngineResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        execution_id = str(uuid4())

        try:
            steps = self._steps(request.execution_steps)
            missing_dependencies = self._missing_dependencies(request)
            checks = self._checks(
                request=request,
                steps=steps,
                missing_dependencies=missing_dependencies,
                execution_permitted=execution_permitted,
            )
            reasons = self._reasons(
                request=request,
                checks=checks,
                missing_dependencies=missing_dependencies,
                execution_permitted=execution_permitted,
            )
            if reasons:
                result = self._result(
                    status=WORKFLOW_EXECUTION_STATUS_BLOCKED,
                    success=False,
                    execution_id=execution_id,
                    request=request,
                    steps=steps,
                    executed_steps=tuple(),
                    pending_steps=steps,
                    missing_dependencies=missing_dependencies,
                    checks=checks,
                    lifecycle=(
                        self._lifecycle("workflow_initialization"),
                        self._lifecycle(WORKFLOW_EXECUTION_STATUS_BLOCKED),
                    ),
                    reasons=reasons,
                    error=";".join(reasons),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            executed_steps = self._executed_steps(request, steps)
            result = self._result(
                status=WORKFLOW_EXECUTION_STATUS_COMPLETED,
                success=True,
                execution_id=execution_id,
                request=request,
                steps=steps,
                executed_steps=executed_steps,
                pending_steps=tuple(),
                missing_dependencies=tuple(),
                checks=checks,
                lifecycle=(
                    self._lifecycle("workflow_initialization"),
                    self._lifecycle("step_execution"),
                    self._lifecycle("execution_validation"),
                    self._lifecycle("continuation_control"),
                    self._lifecycle("final_workflow_reporting"),
                    self._lifecycle(WORKFLOW_EXECUTION_STATUS_COMPLETED),
                ),
                reasons=["workflow_execution_completed"],
                error=None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                execution_id=execution_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def run(
        self,
        request: WorkflowExecutionEngineRequest,
        execution_permitted: bool = True,
    ) -> WorkflowExecutionEngineResult:
        return self.execute(
            request,
            execution_permitted=execution_permitted,
        )

    def _result(
        self,
        status: str,
        success: bool,
        execution_id: str,
        request: WorkflowExecutionEngineRequest,
        steps: tuple[dict[str, Any], ...],
        executed_steps: tuple[dict[str, Any], ...],
        pending_steps: tuple[dict[str, Any], ...],
        missing_dependencies: tuple[str, ...],
        checks: dict[str, bool],
        lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> WorkflowExecutionEngineResult:
        finished_at = datetime.now(timezone.utc)
        completion_confirmed = success and len(executed_steps) == len(steps)
        visibility = self._visibility(
            request=request,
            status=status,
            checks=checks,
            blocking_conditions=tuple(request.blocking_conditions),
            missing_dependencies=missing_dependencies,
            completion_confirmed=completion_confirmed,
        )
        return WorkflowExecutionEngineResult(
            status=status,
            success=success,
            execution_id=execution_id,
            workflow_id=request.workflow_id,
            workflow_objective=request.workflow_objective,
            execution_state=(
                WORKFLOW_EXECUTION_STATUS_COMPLETED
                if completion_confirmed
                else request.execution_state
            ),
            continuation_status=request.continuation_status,
            governance_status=request.governance_status,
            checkpoint_status=request.checkpoint_status,
            workflow_consistency_valid=checks["workflow_consistency"],
            runtime_integrity_valid=checks["runtime_integrity"],
            governance_alignment_valid=checks["governance_alignment"],
            execution_continuity_valid=checks["execution_continuity"],
            operational_stability_valid=checks["operational_stability"],
            execution_sequencing_controlled=checks["sequencing"],
            workflow_integrity_preserved=success
            and checks["workflow_consistency"],
            execution_traceability_preserved=success,
            workflow_completion_confirmed=completion_confirmed,
            execution_steps=steps,
            executed_steps=executed_steps,
            pending_steps=pending_steps,
            blocking_conditions=tuple(request.blocking_conditions),
            missing_dependencies=missing_dependencies,
            human_visibility_payload=visibility,
            execution_lifecycle=lifecycle,
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons),
            error=error,
            metadata=dict(request.metadata),
        )

    def _checks(
        self,
        request: WorkflowExecutionEngineRequest,
        steps: tuple[dict[str, Any], ...],
        missing_dependencies: tuple[str, ...],
        execution_permitted: bool,
    ) -> dict[str, bool]:
        workflow_official = (
            not request.official_workflows
            or request.workflow_id in request.official_workflows
        )
        return {
            "workflow_consistency": bool(
                request.workflow_id
                and steps
                and request.workflow_authorized
                and workflow_official
            ),
            "runtime_integrity": bool(
                request.runtime_integrity_valid
                and self._runtime_safe(request.runtime_state)
            ),
            "governance_alignment": bool(
                request.governance_consistency_valid
                and self._normalize(request.governance_status)
                in APPROVED_GOVERNANCE_STATUSES
            ),
            "execution_continuity": bool(
                self._normalize(request.continuation_status)
                in VALID_CONTINUATION_STATUSES
            ),
            "operational_stability": bool(
                request.operational_stability_valid
                and self._normalize(request.checkpoint_status)
                in CLEAR_CHECKPOINT_STATUSES
                and not missing_dependencies
            ),
            "sequencing": bool(
                execution_permitted
                and self._completed_steps_are_prefix(request, steps)
            ),
        }

    def _reasons(
        self,
        request: WorkflowExecutionEngineRequest,
        checks: dict[str, bool],
        missing_dependencies: tuple[str, ...],
        execution_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not execution_permitted:
            reasons.append("workflow_execution_not_permitted")
        if not checks["workflow_consistency"]:
            reasons.append("workflow_consistency_required")
        if not checks["runtime_integrity"]:
            reasons.append("runtime_integrity_required")
        if not checks["governance_alignment"]:
            reasons.append("governance_alignment_required")
        if not checks["execution_continuity"]:
            reasons.append("execution_continuity_required")
        if not checks["operational_stability"]:
            reasons.append("operational_stability_required")
        if not checks["sequencing"]:
            reasons.append("execution_sequencing_required")
        reasons.extend(
            f"missing_dependency:{dependency}"
            for dependency in missing_dependencies
        )
        reasons.extend(str(item) for item in request.blocking_conditions if item)
        if request.invent_workflow_requested:
            reasons.append("arbitrary_workflow_invention_blocked")
        if request.alter_execution_sequence_requested:
            reasons.append("execution_sequence_alteration_blocked")
        if request.ignore_human_checkpoints_requested:
            reasons.append("human_checkpoint_ignore_blocked")
        if request.break_execution_continuity_requested:
            reasons.append("execution_continuity_break_blocked")
        if request.overwrite_operational_controls_requested:
            reasons.append("operational_control_overwrite_blocked")
        if request.hide_execution_failures_requested:
            reasons.append("execution_failure_concealment_blocked")
        if (
            request.minimize_blocking_conditions_requested
            and request.blocking_conditions
        ):
            reasons.append("blocking_condition_minimization_blocked")
        if request.falsify_workflow_completion_requested:
            reasons.append("workflow_completion_falsification_blocked")
        if request.ignore_runtime_inconsistencies_requested:
            reasons.append("runtime_inconsistency_ignore_blocked")
        return self._unique(reasons)

    def _steps(self, values: tuple[Any, ...]) -> tuple[dict[str, Any], ...]:
        steps: list[dict[str, Any]] = []
        for index, value in enumerate(values, start=1):
            if isinstance(value, dict):
                name = value.get("step_id") or value.get("name") or value.get("id")
                step = dict(value)
                step["step_id"] = str(name or f"step-{index}")
            else:
                step = {"step_id": str(value), "name": str(value)}
            step["sequence"] = index
            steps.append(step)
        return tuple(steps)

    def _executed_steps(
        self,
        request: WorkflowExecutionEngineRequest,
        steps: tuple[dict[str, Any], ...],
    ) -> tuple[dict[str, Any], ...]:
        completed = set(request.completed_steps)
        executed: list[dict[str, Any]] = []
        for step in steps:
            step_id = str(step["step_id"])
            status = "already_completed" if step_id in completed else "executed"
            executed.append(
                {
                    **step,
                    "status": status,
                    "executed_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        return tuple(executed)

    def _completed_steps_are_prefix(
        self,
        request: WorkflowExecutionEngineRequest,
        steps: tuple[dict[str, Any], ...],
    ) -> bool:
        if not request.completed_steps:
            return True
        ordered_ids = [str(step["step_id"]) for step in steps]
        completed = [str(step) for step in request.completed_steps]
        return completed == ordered_ids[: len(completed)]

    def _missing_dependencies(
        self,
        request: WorkflowExecutionEngineRequest,
    ) -> tuple[str, ...]:
        satisfied = set(request.satisfied_dependencies)
        return tuple(
            dependency
            for dependency in request.operational_dependencies
            if dependency not in satisfied
        )

    def _runtime_safe(self, runtime_state: dict[str, Any]) -> bool:
        if not runtime_state:
            return True
        values = (
            runtime_state.get("state"),
            runtime_state.get("status"),
            runtime_state.get("loop_state"),
        )
        return any(
            self._normalize(value) in SAFE_RUNTIME_STATES
            for value in values
        )

    def _visibility(
        self,
        request: WorkflowExecutionEngineRequest,
        status: str,
        checks: dict[str, bool],
        blocking_conditions: tuple[str, ...],
        missing_dependencies: tuple[str, ...],
        completion_confirmed: bool,
    ) -> dict[str, Any]:
        return {
            "workflow_status": status,
            "execution_continuity": checks["execution_continuity"],
            "runtime_integrity": checks["runtime_integrity"],
            "blocking_conditions": list(blocking_conditions),
            "missing_dependencies": list(missing_dependencies),
            "governance_alignment": checks["governance_alignment"],
            "operational_stability": checks["operational_stability"],
            "workflow_completion_confirmed": completion_confirmed,
        }

    def _error_result(
        self,
        execution_id: str,
        request: WorkflowExecutionEngineRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> WorkflowExecutionEngineResult:
        return self._result(
            status=WORKFLOW_EXECUTION_STATUS_ERROR,
            success=False,
            execution_id=execution_id,
            request=request,
            steps=tuple(),
            executed_steps=tuple(),
            pending_steps=tuple(),
            missing_dependencies=tuple(),
            checks={
                "workflow_consistency": False,
                "runtime_integrity": False,
                "governance_alignment": False,
                "execution_continuity": False,
                "operational_stability": False,
                "sequencing": False,
            },
            lifecycle=(self._lifecycle(WORKFLOW_EXECUTION_STATUS_ERROR),),
            reasons=["workflow_execution_engine_error_contained"],
            error=error,
            started=started,
            started_at=started_at,
        )

    def _normalize(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower().replace("-", "_").replace(" ", "_")

    def _lifecycle(self, state: str) -> dict[str, Any]:
        return {
            "state": state,
            "at": datetime.now(timezone.utc).isoformat(),
        }

    def _unique(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for value in values:
            if value and value not in seen:
                seen.add(value)
                unique.append(value)
        return unique

    def _publish(self, result: WorkflowExecutionEngineResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_workflow_execution_engine_result",
        ):
            self.status.mark_workflow_execution_engine_result(result.to_dict())

    def _log_result(self, result: WorkflowExecutionEngineResult) -> None:
        if result.status == WORKFLOW_EXECUTION_STATUS_ERROR:
            logger.error(
                "workflow_execution_engine: error execution_id=%s error=%s",
                result.execution_id,
                result.error,
            )
            return
        if result.status == WORKFLOW_EXECUTION_STATUS_BLOCKED:
            logger.warning(
                "workflow_execution_engine: blocked execution_id=%s reasons=%s",
                result.execution_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "workflow_execution_engine: completed execution_id=%s workflow_id=%s steps=%s",
            result.execution_id,
            result.workflow_id,
            len(result.executed_steps),
        )
