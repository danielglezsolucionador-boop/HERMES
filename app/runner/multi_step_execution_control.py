"""
Multi-step execution control for Hermes workflows.

This layer validates step order, step transitions, continuity, governance, and
runtime consistency. It does not execute external workflow actions or modify
runtime loop behavior.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.workflow_execution_engine import WorkflowExecutionEngineResult

logger = logging.getLogger(__name__)

MULTI_STEP_STATUS_ADVANCED = "advanced"
MULTI_STEP_STATUS_COMPLETED = "completed"
MULTI_STEP_STATUS_BLOCKED = "blocked"
MULTI_STEP_STATUS_ERROR = "error"

VALID_STEP_STATUSES = {"ready", "pending", "executed", "completed", "validated"}
COMPLETED_STEP_STATUSES = {"executed", "completed", "validated", "already_completed"}
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
class MultiStepExecutionControlRequest:
    workflow_id: str | None = None
    workflow_steps: tuple[Any, ...] = field(default_factory=tuple)
    execution_order: tuple[str, ...] = field(default_factory=tuple)
    current_step: str | None = None
    next_step: str | None = None
    completed_steps: tuple[str, ...] = field(default_factory=tuple)
    step_statuses: dict[str, str] = field(default_factory=dict)
    workflow_execution: (
        WorkflowExecutionEngineResult | dict[str, Any] | Any | None
    ) = None
    continuation_status: str | None = "ready"
    governance_status: str | None = "approved"
    checkpoint_status: str | None = "not_required"
    runtime_state: dict[str, Any] = field(default_factory=dict)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    runtime_integrity_valid: bool = True
    operational_stability_valid: bool = True
    governance_consistency_valid: bool = True
    skip_step_requested: bool = False
    alter_execution_order_requested: bool = False
    ignore_critical_validations_requested: bool = False
    overwrite_checkpoints_requested: bool = False
    break_workflow_continuity_requested: bool = False
    hide_execution_failures_requested: bool = False
    minimize_blocking_conditions_requested: bool = False
    falsify_workflow_progression_requested: bool = False
    ignore_runtime_inconsistencies_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MultiStepExecutionControlResult:
    status: str
    success: bool
    control_id: str
    workflow_id: str | None
    current_step: str | None
    next_step: str | None
    expected_next_step: str | None
    continuation_status: str | None
    governance_status: str | None
    checkpoint_status: str | None
    workflow_consistency_valid: bool
    execution_sequencing_valid: bool
    step_transition_valid: bool
    runtime_integrity_valid: bool
    governance_alignment_valid: bool
    execution_continuity_valid: bool
    operational_stability_valid: bool
    workflow_integrity_preserved: bool
    execution_traceability_preserved: bool
    workflow_progression: str
    execution_order: tuple[str, ...] = field(default_factory=tuple)
    completed_steps: tuple[str, ...] = field(default_factory=tuple)
    pending_steps: tuple[str, ...] = field(default_factory=tuple)
    invalid_steps: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    human_visibility_payload: dict[str, Any] = field(default_factory=dict)
    control_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "control_id": self.control_id,
            "workflow_id": self.workflow_id,
            "current_step": self.current_step,
            "next_step": self.next_step,
            "expected_next_step": self.expected_next_step,
            "continuation_status": self.continuation_status,
            "governance_status": self.governance_status,
            "checkpoint_status": self.checkpoint_status,
            "workflow_consistency_valid": self.workflow_consistency_valid,
            "execution_sequencing_valid": self.execution_sequencing_valid,
            "step_transition_valid": self.step_transition_valid,
            "runtime_integrity_valid": self.runtime_integrity_valid,
            "governance_alignment_valid": self.governance_alignment_valid,
            "execution_continuity_valid": self.execution_continuity_valid,
            "operational_stability_valid": self.operational_stability_valid,
            "workflow_integrity_preserved": self.workflow_integrity_preserved,
            "execution_traceability_preserved": (
                self.execution_traceability_preserved
            ),
            "workflow_progression": self.workflow_progression,
            "execution_order": list(self.execution_order),
            "completed_steps": list(self.completed_steps),
            "pending_steps": list(self.pending_steps),
            "invalid_steps": list(self.invalid_steps),
            "blocking_conditions": list(self.blocking_conditions),
            "human_visibility_payload": dict(self.human_visibility_payload),
            "control_lifecycle": [
                dict(entry) for entry in self.control_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class MultiStepExecutionControl:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def control(
        self,
        request: MultiStepExecutionControlRequest,
        control_permitted: bool = True,
    ) -> MultiStepExecutionControlResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        control_id = str(uuid4())

        try:
            workflow_execution = self._as_dict(request.workflow_execution)
            workflow_id = request.workflow_id or workflow_execution.get("workflow_id")
            order = self._execution_order(request, workflow_execution)
            completed = tuple(str(step) for step in request.completed_steps)
            pending = tuple(step for step in order if step not in set(completed))
            expected_next = pending[0] if pending else None
            next_step = request.next_step or expected_next
            invalid_steps = self._invalid_steps(request, order)
            checks = self._checks(
                request=request,
                workflow_id=workflow_id,
                order=order,
                completed=completed,
                expected_next=expected_next,
                next_step=next_step,
                invalid_steps=invalid_steps,
                control_permitted=control_permitted,
            )
            reasons = self._reasons(
                request=request,
                checks=checks,
                expected_next=expected_next,
                next_step=next_step,
                invalid_steps=invalid_steps,
                control_permitted=control_permitted,
            )
            completed_workflow = bool(order) and not pending and not reasons
            if reasons:
                result = self._result(
                    status=MULTI_STEP_STATUS_BLOCKED,
                    success=False,
                    control_id=control_id,
                    workflow_id=workflow_id,
                    request=request,
                    order=order,
                    completed=completed,
                    pending=pending,
                    expected_next=expected_next,
                    next_step=next_step,
                    invalid_steps=invalid_steps,
                    checks=checks,
                    progression="blocked",
                    lifecycle=(
                        self._lifecycle("step_initialization"),
                        self._lifecycle(MULTI_STEP_STATUS_BLOCKED),
                    ),
                    reasons=reasons,
                    error=";".join(reasons),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            result = self._result(
                status=(
                    MULTI_STEP_STATUS_COMPLETED
                    if completed_workflow
                    else MULTI_STEP_STATUS_ADVANCED
                ),
                success=True,
                control_id=control_id,
                workflow_id=workflow_id,
                request=request,
                order=order,
                completed=completed,
                pending=pending,
                expected_next=expected_next,
                next_step=next_step,
                invalid_steps=tuple(),
                checks=checks,
                progression=(
                    "workflow_completed"
                    if completed_workflow
                    else f"next_step_authorized:{next_step}"
                ),
                lifecycle=(
                    self._lifecycle("step_initialization"),
                    self._lifecycle("step_execution"),
                    self._lifecycle("step_validation"),
                    self._lifecycle("continuation_management"),
                    self._lifecycle("final_execution_reporting"),
                ),
                reasons=["multi_step_execution_controlled"],
                error=None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                control_id=control_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def validate(
        self,
        request: MultiStepExecutionControlRequest,
        control_permitted: bool = True,
    ) -> MultiStepExecutionControlResult:
        return self.control(request, control_permitted=control_permitted)

    def _result(
        self,
        status: str,
        success: bool,
        control_id: str,
        workflow_id: str | None,
        request: MultiStepExecutionControlRequest,
        order: tuple[str, ...],
        completed: tuple[str, ...],
        pending: tuple[str, ...],
        expected_next: str | None,
        next_step: str | None,
        invalid_steps: tuple[str, ...],
        checks: dict[str, bool],
        progression: str,
        lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> MultiStepExecutionControlResult:
        finished_at = datetime.now(timezone.utc)
        visibility = self._visibility(
            status=status,
            progression=progression,
            checks=checks,
            blocking_conditions=tuple(request.blocking_conditions),
        )
        return MultiStepExecutionControlResult(
            status=status,
            success=success,
            control_id=control_id,
            workflow_id=workflow_id,
            current_step=request.current_step,
            next_step=next_step,
            expected_next_step=expected_next,
            continuation_status=request.continuation_status,
            governance_status=request.governance_status,
            checkpoint_status=request.checkpoint_status,
            workflow_consistency_valid=checks["workflow_consistency"],
            execution_sequencing_valid=checks["execution_sequencing"],
            step_transition_valid=checks["step_transition"],
            runtime_integrity_valid=checks["runtime_integrity"],
            governance_alignment_valid=checks["governance_alignment"],
            execution_continuity_valid=checks["execution_continuity"],
            operational_stability_valid=checks["operational_stability"],
            workflow_integrity_preserved=success
            and checks["workflow_consistency"],
            execution_traceability_preserved=success,
            workflow_progression=progression,
            execution_order=order,
            completed_steps=completed,
            pending_steps=pending,
            invalid_steps=invalid_steps,
            blocking_conditions=tuple(request.blocking_conditions),
            human_visibility_payload=visibility,
            control_lifecycle=lifecycle,
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons),
            error=error,
            metadata=dict(request.metadata),
        )

    def _checks(
        self,
        request: MultiStepExecutionControlRequest,
        workflow_id: str | None,
        order: tuple[str, ...],
        completed: tuple[str, ...],
        expected_next: str | None,
        next_step: str | None,
        invalid_steps: tuple[str, ...],
        control_permitted: bool,
    ) -> dict[str, bool]:
        return {
            "workflow_consistency": bool(workflow_id and order),
            "execution_sequencing": bool(
                control_permitted
                and self._completed_steps_are_prefix(completed, order)
                and not invalid_steps
            ),
            "step_transition": bool(
                next_step == expected_next or (expected_next is None and not next_step)
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
                and not request.blocking_conditions
            ),
        }

    def _reasons(
        self,
        request: MultiStepExecutionControlRequest,
        checks: dict[str, bool],
        expected_next: str | None,
        next_step: str | None,
        invalid_steps: tuple[str, ...],
        control_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not control_permitted:
            reasons.append("multi_step_control_not_permitted")
        if not checks["workflow_consistency"]:
            reasons.append("workflow_consistency_required")
        if not checks["execution_sequencing"]:
            reasons.append("execution_sequencing_required")
        if not checks["step_transition"]:
            reasons.append("step_transition_invalid")
        if not checks["runtime_integrity"]:
            reasons.append("runtime_integrity_required")
        if not checks["governance_alignment"]:
            reasons.append("governance_alignment_required")
        if not checks["execution_continuity"]:
            reasons.append("execution_continuity_required")
        if not checks["operational_stability"]:
            reasons.append("operational_stability_required")
        if expected_next and next_step and next_step != expected_next:
            reasons.append("workflow_step_skipping_detected")
        reasons.extend(f"invalid_step_status:{step}" for step in invalid_steps)
        reasons.extend(str(item) for item in request.blocking_conditions if item)
        if request.skip_step_requested:
            reasons.append("workflow_step_skip_blocked")
        if request.alter_execution_order_requested:
            reasons.append("execution_order_alteration_blocked")
        if request.ignore_critical_validations_requested:
            reasons.append("critical_validation_ignore_blocked")
        if request.overwrite_checkpoints_requested:
            reasons.append("checkpoint_overwrite_blocked")
        if request.break_workflow_continuity_requested:
            reasons.append("workflow_continuity_break_blocked")
        if request.hide_execution_failures_requested:
            reasons.append("execution_failure_concealment_blocked")
        if (
            request.minimize_blocking_conditions_requested
            and request.blocking_conditions
        ):
            reasons.append("blocking_condition_minimization_blocked")
        if request.falsify_workflow_progression_requested:
            reasons.append("workflow_progression_falsification_blocked")
        if request.ignore_runtime_inconsistencies_requested:
            reasons.append("runtime_inconsistency_ignore_blocked")
        return self._unique(reasons)

    def _execution_order(
        self,
        request: MultiStepExecutionControlRequest,
        workflow_execution: dict[str, Any],
    ) -> tuple[str, ...]:
        if request.execution_order:
            return tuple(str(step) for step in request.execution_order if step)
        steps = request.workflow_steps or tuple(
            workflow_execution.get("execution_steps") or []
        )
        return tuple(self._step_id(step) for step in steps if self._step_id(step))

    def _invalid_steps(
        self,
        request: MultiStepExecutionControlRequest,
        order: tuple[str, ...],
    ) -> tuple[str, ...]:
        invalid: list[str] = []
        for step_id, status in request.step_statuses.items():
            normalized = self._normalize(status)
            if step_id in order and normalized not in VALID_STEP_STATUSES:
                invalid.append(str(step_id))
        for step_id in request.completed_steps:
            normalized = self._normalize(request.step_statuses.get(step_id))
            if normalized and normalized not in COMPLETED_STEP_STATUSES:
                invalid.append(str(step_id))
        return tuple(self._unique(invalid))

    def _completed_steps_are_prefix(
        self,
        completed: tuple[str, ...],
        order: tuple[str, ...],
    ) -> bool:
        if not completed:
            return True
        return list(completed) == list(order[: len(completed)])

    def _step_id(self, value: Any) -> str | None:
        if isinstance(value, dict):
            step_id = value.get("step_id") or value.get("name") or value.get("id")
            return str(step_id) if step_id else None
        return str(value) if value else None

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
        status: str,
        progression: str,
        checks: dict[str, bool],
        blocking_conditions: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "workflow_progression": progression,
            "step_completion": status,
            "execution_continuity": checks["execution_continuity"],
            "runtime_integrity": checks["runtime_integrity"],
            "blocking_conditions": list(blocking_conditions),
            "governance_alignment": checks["governance_alignment"],
            "operational_stability": checks["operational_stability"],
        }

    def _error_result(
        self,
        control_id: str,
        request: MultiStepExecutionControlRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> MultiStepExecutionControlResult:
        return self._result(
            status=MULTI_STEP_STATUS_ERROR,
            success=False,
            control_id=control_id,
            workflow_id=request.workflow_id,
            request=request,
            order=tuple(),
            completed=tuple(),
            pending=tuple(),
            expected_next=None,
            next_step=None,
            invalid_steps=tuple(),
            checks={
                "workflow_consistency": False,
                "execution_sequencing": False,
                "step_transition": False,
                "runtime_integrity": False,
                "governance_alignment": False,
                "execution_continuity": False,
                "operational_stability": False,
            },
            progression="error",
            lifecycle=(self._lifecycle(MULTI_STEP_STATUS_ERROR),),
            reasons=["multi_step_execution_control_error_contained"],
            error=error,
            started=started,
            started_at=started_at,
        )

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, WorkflowExecutionEngineResult):
            return value.to_dict()
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

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

    def _publish(self, result: MultiStepExecutionControlResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_multi_step_execution_control_result",
        ):
            self.status.mark_multi_step_execution_control_result(result.to_dict())

    def _log_result(self, result: MultiStepExecutionControlResult) -> None:
        if result.status == MULTI_STEP_STATUS_ERROR:
            logger.error(
                "multi_step_execution_control: error control_id=%s error=%s",
                result.control_id,
                result.error,
            )
            return
        if result.status == MULTI_STEP_STATUS_BLOCKED:
            logger.warning(
                "multi_step_execution_control: blocked control_id=%s reasons=%s",
                result.control_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "multi_step_execution_control: %s control_id=%s workflow_id=%s next=%s",
            result.status,
            result.control_id,
            result.workflow_id,
            result.next_step,
        )
