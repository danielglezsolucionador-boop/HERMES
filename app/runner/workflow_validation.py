"""
Workflow validation for complete Hermes operational workflows.

This layer validates complete workflow context across execution, multi-step,
human checkpoint, and recovery controls. It does not approve corrupt workflows,
continue execution, or mutate runtime state.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.human_checkpoint_control import HumanCheckpointControlResult
from app.runner.multi_step_execution_control import MultiStepExecutionControlResult
from app.runner.workflow_execution_engine import WorkflowExecutionEngineResult
from app.runner.workflow_recovery_control import WorkflowRecoveryControlResult

logger = logging.getLogger(__name__)

WORKFLOW_VALIDATION_STATUS_VALIDATED = "validated"
WORKFLOW_VALIDATION_STATUS_BLOCKED = "blocked"
WORKFLOW_VALIDATION_STATUS_ERROR = "error"

VALID_WORKFLOW_STATUSES = {"completed", "advanced", "recovered", "stable"}
VALID_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "governance_approved",
    "authorized_by_human",
}
VALID_CONTINUATION_STATUSES = {
    "ready",
    "active",
    "continued",
    "resumed",
    "authorized_by_human",
    "workflow_reactivated_under_resume_control",
    "recovery_validated",
}
SAFE_RUNTIME_STATES = {"active", "online", "ready", "stable", "resumed"}


@dataclass(frozen=True)
class WorkflowValidationRequest:
    validation_id: str | None = None
    workflow_id: str | None = None
    workflow_status: str | None = None
    continuation_status: str | None = None
    governance_status: str | None = None
    runtime_state: dict[str, Any] = field(default_factory=dict)
    workflow_execution: (
        WorkflowExecutionEngineResult | dict[str, Any] | Any | None
    ) = None
    multi_step_control: (
        MultiStepExecutionControlResult | dict[str, Any] | Any | None
    ) = None
    human_checkpoint_control: (
        HumanCheckpointControlResult | dict[str, Any] | Any | None
    ) = None
    workflow_recovery_control: (
        WorkflowRecoveryControlResult | dict[str, Any] | Any | None
    ) = None
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    detected_inconsistencies: tuple[str, ...] = field(default_factory=tuple)
    workflow_integrity_valid: bool = True
    execution_integrity_valid: bool = True
    runtime_integrity_valid: bool = True
    governance_alignment_valid: bool = True
    continuity_valid: bool = True
    operational_stability_valid: bool = True
    approve_corrupt_workflow_requested: bool = False
    ignore_runtime_inconsistencies_requested: bool = False
    minimize_execution_failures_requested: bool = False
    falsify_validations_requested: bool = False
    unsafe_continuation_requested: bool = False
    hide_execution_failures_requested: bool = False
    minimize_blocking_conditions_requested: bool = False
    alter_workflow_history_requested: bool = False
    ignore_governance_conflicts_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowValidationResult:
    status: str
    success: bool
    validation_id: str
    workflow_id: str | None
    workflow_status: str | None
    continuation_status: str | None
    governance_status: str | None
    workflow_validation_valid: bool
    execution_validation_valid: bool
    runtime_validation_valid: bool
    governance_validation_valid: bool
    continuity_validation_valid: bool
    operational_validation_valid: bool
    workflow_safe: bool
    continuation_allowed: bool
    workflow_integrity_preserved: bool
    execution_traceability_preserved: bool
    governance_consistency_preserved: bool
    operational_continuity_preserved: bool
    detected_inconsistencies: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    validation_report: dict[str, Any] = field(default_factory=dict)
    human_visibility_payload: dict[str, Any] = field(default_factory=dict)
    validation_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "validation_id": self.validation_id,
            "workflow_id": self.workflow_id,
            "workflow_status": self.workflow_status,
            "continuation_status": self.continuation_status,
            "governance_status": self.governance_status,
            "workflow_validation_valid": self.workflow_validation_valid,
            "execution_validation_valid": self.execution_validation_valid,
            "runtime_validation_valid": self.runtime_validation_valid,
            "governance_validation_valid": self.governance_validation_valid,
            "continuity_validation_valid": self.continuity_validation_valid,
            "operational_validation_valid": self.operational_validation_valid,
            "workflow_safe": self.workflow_safe,
            "continuation_allowed": self.continuation_allowed,
            "workflow_integrity_preserved": self.workflow_integrity_preserved,
            "execution_traceability_preserved": (
                self.execution_traceability_preserved
            ),
            "governance_consistency_preserved": (
                self.governance_consistency_preserved
            ),
            "operational_continuity_preserved": (
                self.operational_continuity_preserved
            ),
            "detected_inconsistencies": list(self.detected_inconsistencies),
            "blocking_conditions": list(self.blocking_conditions),
            "validation_report": dict(self.validation_report),
            "human_visibility_payload": dict(self.human_visibility_payload),
            "validation_lifecycle": [
                dict(entry) for entry in self.validation_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class WorkflowValidation:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def validate(
        self,
        request: WorkflowValidationRequest,
        validation_permitted: bool = True,
    ) -> WorkflowValidationResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        validation_id = request.validation_id or str(uuid4())

        try:
            context = self._context(request)
            checks = self._checks(
                request=request,
                context=context,
                validation_permitted=validation_permitted,
            )
            inconsistencies = tuple(
                self._inconsistencies(request, checks, context)
            )
            blocking_conditions = tuple(
                self._blocking_conditions(request, inconsistencies)
            )
            reasons = self._reasons(
                request=request,
                checks=checks,
                inconsistencies=inconsistencies,
                blocking_conditions=blocking_conditions,
                validation_permitted=validation_permitted,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    WORKFLOW_VALIDATION_STATUS_BLOCKED
                    if blocked
                    else WORKFLOW_VALIDATION_STATUS_VALIDATED
                ),
                success=not blocked,
                validation_id=validation_id,
                request=request,
                context=context,
                checks=checks,
                inconsistencies=inconsistencies,
                blocking_conditions=blocking_conditions,
                reasons=reasons
                or ["workflow_validation_completed"],
                error=";".join(reasons) if blocked else None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                validation_id=validation_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def inspect(
        self,
        request: WorkflowValidationRequest,
        validation_permitted: bool = True,
    ) -> WorkflowValidationResult:
        return self.validate(
            request,
            validation_permitted=validation_permitted,
        )

    def _result(
        self,
        status: str,
        success: bool,
        validation_id: str,
        request: WorkflowValidationRequest,
        context: dict[str, Any],
        checks: dict[str, bool],
        inconsistencies: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> WorkflowValidationResult:
        finished_at = datetime.now(timezone.utc)
        workflow_safe = success and all(checks.values())
        return WorkflowValidationResult(
            status=status,
            success=success,
            validation_id=validation_id,
            workflow_id=context["workflow_id"],
            workflow_status=context["workflow_status"],
            continuation_status=context["continuation_status"],
            governance_status=context["governance_status"],
            workflow_validation_valid=checks["workflow"],
            execution_validation_valid=checks["execution"],
            runtime_validation_valid=checks["runtime"],
            governance_validation_valid=checks["governance"],
            continuity_validation_valid=checks["continuity"],
            operational_validation_valid=checks["operational"],
            workflow_safe=workflow_safe,
            continuation_allowed=workflow_safe,
            workflow_integrity_preserved=success and checks["workflow"],
            execution_traceability_preserved=success,
            governance_consistency_preserved=success and checks["governance"],
            operational_continuity_preserved=success and checks["continuity"],
            detected_inconsistencies=inconsistencies,
            blocking_conditions=blocking_conditions,
            validation_report=self._report(checks, inconsistencies, blocking_conditions),
            human_visibility_payload=self._visibility(
                status=status,
                context=context,
                checks=checks,
                blocking_conditions=blocking_conditions,
            ),
            validation_lifecycle=(
                self._lifecycle("workflow_analysis"),
                self._lifecycle("execution_validation"),
                self._lifecycle("governance_validation"),
                self._lifecycle("inconsistency_detection"),
                self._lifecycle("final_validation_report"),
            ),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons),
            error=error,
            metadata=dict(request.metadata),
        )

    def _context(self, request: WorkflowValidationRequest) -> dict[str, Any]:
        workflow_execution = self._as_dict(request.workflow_execution)
        multi_step = self._as_dict(request.multi_step_control)
        human_checkpoint = self._as_dict(request.human_checkpoint_control)
        recovery = self._as_dict(request.workflow_recovery_control)
        return {
            "workflow_id": (
                request.workflow_id
                or workflow_execution.get("workflow_id")
                or multi_step.get("workflow_id")
                or human_checkpoint.get("workflow_id")
                or recovery.get("workflow_id")
            ),
            "workflow_status": (
                request.workflow_status
                or recovery.get("status")
                or workflow_execution.get("status")
                or multi_step.get("status")
            ),
            "continuation_status": (
                request.continuation_status
                or recovery.get("continuation_status")
                or human_checkpoint.get("continuation_status")
                or workflow_execution.get("continuation_status")
                or multi_step.get("continuation_status")
            ),
            "governance_status": (
                request.governance_status
                or recovery.get("governance_status")
                or human_checkpoint.get("governance_status")
                or workflow_execution.get("governance_status")
                or multi_step.get("governance_status")
            ),
            "workflow_execution": workflow_execution,
            "multi_step": multi_step,
            "human_checkpoint": human_checkpoint,
            "recovery": recovery,
        }

    def _checks(
        self,
        request: WorkflowValidationRequest,
        context: dict[str, Any],
        validation_permitted: bool,
    ) -> dict[str, bool]:
        workflow_status = self._normalize(context["workflow_status"])
        continuation_status = self._normalize(context["continuation_status"])
        governance_status = self._normalize(context["governance_status"])
        return {
            "workflow": bool(
                validation_permitted
                and request.workflow_integrity_valid
                and context["workflow_id"]
                and workflow_status in VALID_WORKFLOW_STATUSES
            ),
            "execution": bool(
                request.execution_integrity_valid
                and self._component_success(
                    context["workflow_execution"],
                    context["multi_step"],
                    context["recovery"],
                )
            ),
            "runtime": bool(
                request.runtime_integrity_valid
                and self._runtime_safe(request.runtime_state)
            ),
            "governance": bool(
                request.governance_alignment_valid
                and governance_status in VALID_GOVERNANCE_STATUSES
            ),
            "continuity": bool(
                request.continuity_valid
                and continuation_status in VALID_CONTINUATION_STATUSES
                and self._continuation_components_safe(context)
            ),
            "operational": bool(
                request.operational_stability_valid
                and not request.blocking_conditions
                and not request.detected_inconsistencies
                and self._components_operational(context)
            ),
        }

    def _component_success(self, *components: dict[str, Any]) -> bool:
        available = [component for component in components if component]
        if not available:
            return True
        return all(
            component.get("success") is True
            and self._normalize(component.get("status"))
            not in {"blocked", "error"}
            for component in available
        )

    def _continuation_components_safe(self, context: dict[str, Any]) -> bool:
        human_checkpoint = context["human_checkpoint"]
        recovery = context["recovery"]
        if human_checkpoint and human_checkpoint.get("continuation_allowed") is False:
            return False
        if recovery and recovery.get("continuation_allowed") is False:
            return False
        return True

    def _components_operational(self, context: dict[str, Any]) -> bool:
        blocked_statuses = {"blocked", "error", "changes_requested", "escalated"}
        for key in (
            "workflow_execution",
            "multi_step",
            "human_checkpoint",
            "recovery",
        ):
            component = context.get(key) or {}
            if self._normalize(component.get("status")) in blocked_statuses:
                return False
        return True

    def _inconsistencies(
        self,
        request: WorkflowValidationRequest,
        checks: dict[str, bool],
        context: dict[str, Any],
    ) -> list[str]:
        inconsistencies = [str(item) for item in request.detected_inconsistencies]
        for name, valid in checks.items():
            if not valid:
                inconsistencies.append(f"{name}_validation_failed")
        for key in (
            "workflow_execution",
            "multi_step",
            "human_checkpoint",
            "recovery",
        ):
            status = self._normalize((context.get(key) or {}).get("status"))
            if status in {"blocked", "error", "changes_requested", "escalated"}:
                inconsistencies.append(f"{key}_{status}")
            if key == "human_checkpoint" and status == "waiting":
                inconsistencies.append("human_checkpoint_waiting")
        return self._unique(inconsistencies)

    def _blocking_conditions(
        self,
        request: WorkflowValidationRequest,
        inconsistencies: tuple[str, ...],
    ) -> list[str]:
        return self._unique(
            [
                *[str(item) for item in request.blocking_conditions],
                *[str(item) for item in inconsistencies],
            ]
        )

    def _reasons(
        self,
        request: WorkflowValidationRequest,
        checks: dict[str, bool],
        inconsistencies: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        validation_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not validation_permitted:
            reasons.append("workflow_validation_not_permitted")
        for name, valid in checks.items():
            if not valid:
                reasons.append(f"{name}_validation_required")
        if blocking_conditions:
            reasons.append("workflow_blocking_conditions_active")
        if inconsistencies:
            reasons.append("workflow_inconsistencies_detected")
        if request.approve_corrupt_workflow_requested:
            reasons.append("corrupt_workflow_approval_blocked")
        if request.ignore_runtime_inconsistencies_requested:
            reasons.append("runtime_inconsistency_ignore_blocked")
        if request.minimize_execution_failures_requested:
            reasons.append("execution_failure_minimization_blocked")
        if request.falsify_validations_requested:
            reasons.append("validation_falsification_blocked")
        if request.unsafe_continuation_requested:
            reasons.append("unsafe_continuation_blocked")
        if request.hide_execution_failures_requested:
            reasons.append("execution_failure_concealment_blocked")
        if (
            request.minimize_blocking_conditions_requested
            and blocking_conditions
        ):
            reasons.append("blocking_condition_minimization_blocked")
        if request.alter_workflow_history_requested:
            reasons.append("workflow_history_alteration_blocked")
        if request.ignore_governance_conflicts_requested:
            reasons.append("governance_conflict_ignore_blocked")
        if inconsistencies and request.hide_execution_failures_requested:
            reasons.append("workflow_inconsistency_concealment_blocked")
        return self._unique(reasons)

    def _report(
        self,
        checks: dict[str, bool],
        inconsistencies: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "checks": dict(checks),
            "detected_inconsistencies": list(inconsistencies),
            "blocking_conditions": list(blocking_conditions),
            "continuation_status": (
                "allowed" if all(checks.values()) and not blocking_conditions else "blocked"
            ),
        }

    def _visibility(
        self,
        status: str,
        context: dict[str, Any],
        checks: dict[str, bool],
        blocking_conditions: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "workflow_status": status,
            "execution_integrity": checks["execution"],
            "runtime_consistency": checks["runtime"],
            "blocking_conditions": list(blocking_conditions),
            "governance_alignment": checks["governance"],
            "continuation_status": context["continuation_status"],
        }

    def _error_result(
        self,
        validation_id: str,
        request: WorkflowValidationRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> WorkflowValidationResult:
        return self._result(
            status=WORKFLOW_VALIDATION_STATUS_ERROR,
            success=False,
            validation_id=validation_id,
            request=request,
            context={
                "workflow_id": request.workflow_id,
                "workflow_status": request.workflow_status,
                "continuation_status": request.continuation_status,
                "governance_status": request.governance_status,
            },
            checks={
                "workflow": False,
                "execution": False,
                "runtime": False,
                "governance": False,
                "continuity": False,
                "operational": False,
            },
            inconsistencies=tuple(request.detected_inconsistencies),
            blocking_conditions=tuple(request.blocking_conditions),
            reasons=["workflow_validation_error_contained"],
            error=error,
            started=started,
            started_at=started_at,
        )

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(
            value,
            (
                WorkflowExecutionEngineResult,
                MultiStepExecutionControlResult,
                HumanCheckpointControlResult,
                WorkflowRecoveryControlResult,
            ),
        ):
            return value.to_dict()
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

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

    def _publish(self, result: WorkflowValidationResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_workflow_validation_result",
        ):
            self.status.mark_workflow_validation_result(result.to_dict())

    def _log_result(self, result: WorkflowValidationResult) -> None:
        if result.status == WORKFLOW_VALIDATION_STATUS_ERROR:
            logger.error(
                "workflow_validation: error validation_id=%s error=%s",
                result.validation_id,
                result.error,
            )
            return
        if result.status == WORKFLOW_VALIDATION_STATUS_BLOCKED:
            logger.warning(
                "workflow_validation: blocked validation_id=%s reasons=%s",
                result.validation_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "workflow_validation: validated validation_id=%s workflow_id=%s",
            result.validation_id,
            result.workflow_id,
        )
