"""
Workflow recovery control for Hermes operational workflows.

This layer validates interrupted workflow recovery, restored execution state,
runtime continuity, governance alignment, and operational stability. It does not
restart workflows directly, overwrite governance state, or mutate history.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.checkpoint_recovery import CheckpointRecoveryResult
from app.runner.execution_resume import ExecutionResumeResult
from app.runner.human_checkpoint_control import HumanCheckpointControlResult

logger = logging.getLogger(__name__)

WORKFLOW_RECOVERY_STATUS_RECOVERED = "recovered"
WORKFLOW_RECOVERY_STATUS_BLOCKED = "blocked"
WORKFLOW_RECOVERY_STATUS_ERROR = "error"

VALID_RECOVERY_STATUSES = {
    "ready",
    "recovered",
    "recovery_prepared",
    "resumed",
}
VALID_CONTINUATION_STATUSES = {
    "ready",
    "resumed",
    "workflow_reactivated_under_resume_control",
    "recovery_validated",
}
VALID_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "governance_approved",
    "authorized_by_human",
}
VALID_CHECKPOINT_STATUSES = {"valid", "approved", "not_required", "ready"}
SAFE_RUNTIME_STATES = {"active", "online", "ready", "stable", "resumed"}


@dataclass(frozen=True)
class WorkflowRecoveryControlRequest:
    recovery_id: str | None = None
    workflow_id: str | None = None
    workflow_state: dict[str, Any] = field(default_factory=dict)
    execution_context: dict[str, Any] = field(default_factory=dict)
    continuation_status: str | None = None
    recovery_status: str | None = None
    governance_status: str | None = None
    checkpoint_status: str | None = None
    runtime_state: dict[str, Any] = field(default_factory=dict)
    checkpoint_recovery: (
        CheckpointRecoveryResult | dict[str, Any] | Any | None
    ) = None
    execution_resume: ExecutionResumeResult | dict[str, Any] | Any | None = None
    human_checkpoint_control: (
        HumanCheckpointControlResult | dict[str, Any] | Any | None
    ) = None
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    interruption_detected: bool = True
    runtime_integrity_valid: bool = True
    workflow_consistency_valid: bool = True
    governance_consistency_valid: bool = True
    execution_consistency_valid: bool = True
    operational_stability_valid: bool = True
    recover_corrupt_workflow_requested: bool = False
    ignore_runtime_inconsistencies_requested: bool = False
    overwrite_governance_state_requested: bool = False
    alter_workflow_history_requested: bool = False
    unsafe_continuation_requested: bool = False
    hide_recovery_failures_requested: bool = False
    minimize_runtime_corruption_requested: bool = False
    falsify_continuation_status_requested: bool = False
    ignore_blocking_conditions_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowRecoveryControlResult:
    status: str
    success: bool
    control_id: str
    recovery_id: str | None
    workflow_id: str | None
    continuation_status: str | None
    recovery_status: str | None
    governance_status: str | None
    checkpoint_status: str | None
    interruption_detected: bool
    state_restored: bool
    recovery_valid: bool
    continuation_allowed: bool
    workflow_integrity_valid: bool
    runtime_continuity_valid: bool
    governance_alignment_valid: bool
    execution_consistency_valid: bool
    operational_stability_valid: bool
    workflow_history_preserved: bool
    execution_traceability_preserved: bool
    workflow_state: dict[str, Any] = field(default_factory=dict)
    execution_context: dict[str, Any] = field(default_factory=dict)
    restored_state: dict[str, Any] = field(default_factory=dict)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    human_visibility_payload: dict[str, Any] = field(default_factory=dict)
    recovery_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "recovery_id": self.recovery_id,
            "workflow_id": self.workflow_id,
            "continuation_status": self.continuation_status,
            "recovery_status": self.recovery_status,
            "governance_status": self.governance_status,
            "checkpoint_status": self.checkpoint_status,
            "interruption_detected": self.interruption_detected,
            "state_restored": self.state_restored,
            "recovery_valid": self.recovery_valid,
            "continuation_allowed": self.continuation_allowed,
            "workflow_integrity_valid": self.workflow_integrity_valid,
            "runtime_continuity_valid": self.runtime_continuity_valid,
            "governance_alignment_valid": self.governance_alignment_valid,
            "execution_consistency_valid": self.execution_consistency_valid,
            "operational_stability_valid": self.operational_stability_valid,
            "workflow_history_preserved": self.workflow_history_preserved,
            "execution_traceability_preserved": (
                self.execution_traceability_preserved
            ),
            "workflow_state": dict(self.workflow_state),
            "execution_context": dict(self.execution_context),
            "restored_state": dict(self.restored_state),
            "blocking_conditions": list(self.blocking_conditions),
            "human_visibility_payload": dict(self.human_visibility_payload),
            "recovery_lifecycle": [
                dict(entry) for entry in self.recovery_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class WorkflowRecoveryControl:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def recover(
        self,
        request: WorkflowRecoveryControlRequest,
        recovery_permitted: bool = True,
    ) -> WorkflowRecoveryControlResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        control_id = str(uuid4())

        try:
            checkpoint_recovery = self._as_dict(request.checkpoint_recovery)
            execution_resume = self._as_dict(request.execution_resume)
            human_checkpoint = self._as_dict(request.human_checkpoint_control)
            context = self._context(
                request,
                checkpoint_recovery,
                execution_resume,
                human_checkpoint,
            )
            restored_state = self._restored_state(
                request,
                checkpoint_recovery,
                execution_resume,
            )
            checks = self._checks(
                request=request,
                context=context,
                restored_state=restored_state,
                recovery_permitted=recovery_permitted,
            )
            reasons = self._reasons(
                request=request,
                checks=checks,
                recovery_permitted=recovery_permitted,
            )
            if reasons:
                result = self._result(
                    status=WORKFLOW_RECOVERY_STATUS_BLOCKED,
                    success=False,
                    control_id=control_id,
                    request=request,
                    context=context,
                    restored_state=restored_state,
                    checks=checks,
                    continuation_allowed=False,
                    lifecycle=(
                        self._lifecycle("interruption_detection"),
                        self._lifecycle(WORKFLOW_RECOVERY_STATUS_BLOCKED),
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
                status=WORKFLOW_RECOVERY_STATUS_RECOVERED,
                success=True,
                control_id=control_id,
                request=request,
                context=context,
                restored_state=restored_state,
                checks=checks,
                continuation_allowed=True,
                lifecycle=(
                    self._lifecycle("interruption_detection"),
                    self._lifecycle("state_restoration"),
                    self._lifecycle("recovery_validation"),
                    self._lifecycle("controlled_continuation"),
                    self._lifecycle("recovery_reporting"),
                ),
                reasons=["workflow_recovery_validated"],
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
        request: WorkflowRecoveryControlRequest,
        recovery_permitted: bool = True,
    ) -> WorkflowRecoveryControlResult:
        return self.recover(request, recovery_permitted=recovery_permitted)

    def _result(
        self,
        status: str,
        success: bool,
        control_id: str,
        request: WorkflowRecoveryControlRequest,
        context: dict[str, Any],
        restored_state: dict[str, Any],
        checks: dict[str, bool],
        continuation_allowed: bool,
        lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> WorkflowRecoveryControlResult:
        finished_at = datetime.now(timezone.utc)
        return WorkflowRecoveryControlResult(
            status=status,
            success=success,
            control_id=control_id,
            recovery_id=context["recovery_id"],
            workflow_id=context["workflow_id"],
            continuation_status=context["continuation_status"],
            recovery_status=context["recovery_status"],
            governance_status=context["governance_status"],
            checkpoint_status=context["checkpoint_status"],
            interruption_detected=checks["interruption_detected"],
            state_restored=checks["state_restored"],
            recovery_valid=checks["recovery_valid"],
            continuation_allowed=continuation_allowed,
            workflow_integrity_valid=checks["workflow_integrity"],
            runtime_continuity_valid=checks["runtime_continuity"],
            governance_alignment_valid=checks["governance_alignment"],
            execution_consistency_valid=checks["execution_consistency"],
            operational_stability_valid=checks["operational_stability"],
            workflow_history_preserved=success,
            execution_traceability_preserved=success,
            workflow_state=dict(request.workflow_state),
            execution_context=dict(request.execution_context),
            restored_state=restored_state,
            blocking_conditions=tuple(request.blocking_conditions),
            human_visibility_payload=self._visibility(
                status=status,
                checks=checks,
                blocking_conditions=tuple(request.blocking_conditions),
                continuation_allowed=continuation_allowed,
            ),
            recovery_lifecycle=lifecycle,
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons),
            error=error,
            metadata=dict(request.metadata),
        )

    def _context(
        self,
        request: WorkflowRecoveryControlRequest,
        checkpoint_recovery: dict[str, Any],
        execution_resume: dict[str, Any],
        human_checkpoint: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "recovery_id": (
                request.recovery_id
                or checkpoint_recovery.get("recovery_id")
                or execution_resume.get("resume_id")
            ),
            "workflow_id": (
                request.workflow_id
                or request.workflow_state.get("workflow_id")
                or execution_resume.get("workflow_id")
                or human_checkpoint.get("workflow_id")
            ),
            "continuation_status": (
                request.continuation_status
                or execution_resume.get("continuation_status")
                or checkpoint_recovery.get("continuation_status")
            ),
            "recovery_status": (
                request.recovery_status
                or checkpoint_recovery.get("recovery_status")
                or execution_resume.get("resume_status")
                or execution_resume.get("status")
            ),
            "governance_status": (
                request.governance_status
                or execution_resume.get("governance_status")
                or human_checkpoint.get("governance_status")
            ),
            "checkpoint_status": (
                request.checkpoint_status
                or checkpoint_recovery.get("checkpoint_status")
                or ("valid" if checkpoint_recovery.get("checkpoint_valid") else None)
            ),
        }

    def _checks(
        self,
        request: WorkflowRecoveryControlRequest,
        context: dict[str, Any],
        restored_state: dict[str, Any],
        recovery_permitted: bool,
    ) -> dict[str, bool]:
        return {
            "interruption_detected": bool(request.interruption_detected),
            "state_restored": bool(restored_state),
            "recovery_valid": bool(
                recovery_permitted
                and self._normalize(context["recovery_status"])
                in VALID_RECOVERY_STATUSES
            ),
            "workflow_integrity": bool(
                request.workflow_consistency_valid and context["workflow_id"]
            ),
            "runtime_continuity": bool(
                request.runtime_integrity_valid
                and self._runtime_safe(request.runtime_state)
            ),
            "governance_alignment": bool(
                request.governance_consistency_valid
                and self._normalize(context["governance_status"])
                in VALID_GOVERNANCE_STATUSES
            ),
            "execution_consistency": bool(
                request.execution_consistency_valid
                and self._normalize(context["continuation_status"])
                in VALID_CONTINUATION_STATUSES
            ),
            "operational_stability": bool(
                request.operational_stability_valid
                and self._normalize(context["checkpoint_status"])
                in VALID_CHECKPOINT_STATUSES
                and not request.blocking_conditions
            ),
        }

    def _reasons(
        self,
        request: WorkflowRecoveryControlRequest,
        checks: dict[str, bool],
        recovery_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not recovery_permitted:
            reasons.append("workflow_recovery_not_permitted")
        if not checks["interruption_detected"]:
            reasons.append("workflow_interruption_required")
        if not checks["state_restored"]:
            reasons.append("restored_state_required")
        if not checks["recovery_valid"]:
            reasons.append("recovery_status_invalid")
        if not checks["workflow_integrity"]:
            reasons.append("workflow_integrity_required")
        if not checks["runtime_continuity"]:
            reasons.append("runtime_continuity_required")
        if not checks["governance_alignment"]:
            reasons.append("governance_alignment_required")
        if not checks["execution_consistency"]:
            reasons.append("execution_consistency_required")
        if not checks["operational_stability"]:
            reasons.append("operational_stability_required")
        reasons.extend(str(item) for item in request.blocking_conditions if item)
        if request.recover_corrupt_workflow_requested:
            reasons.append("corrupt_workflow_recovery_blocked")
        if request.ignore_runtime_inconsistencies_requested:
            reasons.append("runtime_inconsistency_ignore_blocked")
        if request.overwrite_governance_state_requested:
            reasons.append("governance_state_overwrite_blocked")
        if request.alter_workflow_history_requested:
            reasons.append("workflow_history_alteration_blocked")
        if request.unsafe_continuation_requested:
            reasons.append("unsafe_continuation_blocked")
        if request.hide_recovery_failures_requested:
            reasons.append("recovery_failure_concealment_blocked")
        if request.minimize_runtime_corruption_requested:
            reasons.append("runtime_corruption_minimization_blocked")
        if request.falsify_continuation_status_requested:
            reasons.append("continuation_status_falsification_blocked")
        if (
            request.ignore_blocking_conditions_requested
            and request.blocking_conditions
        ):
            reasons.append("blocking_condition_ignore_blocked")
        return self._unique(reasons)

    def _restored_state(
        self,
        request: WorkflowRecoveryControlRequest,
        checkpoint_recovery: dict[str, Any],
        execution_resume: dict[str, Any],
    ) -> dict[str, Any]:
        restored: dict[str, Any] = {}
        restored.update(dict(request.workflow_state or {}))
        restored.update(dict(checkpoint_recovery.get("restored_state") or {}))
        restored.update(dict(execution_resume.get("restored_state") or {}))
        return restored

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
        checks: dict[str, bool],
        blocking_conditions: tuple[str, ...],
        continuation_allowed: bool,
    ) -> dict[str, Any]:
        return {
            "recovery_status": status,
            "workflow_continuity": checks["execution_consistency"],
            "runtime_integrity": checks["runtime_continuity"],
            "blocking_conditions": list(blocking_conditions),
            "governance_alignment": checks["governance_alignment"],
            "operational_stability": checks["operational_stability"],
            "continuation_allowed": continuation_allowed,
        }

    def _error_result(
        self,
        control_id: str,
        request: WorkflowRecoveryControlRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> WorkflowRecoveryControlResult:
        return self._result(
            status=WORKFLOW_RECOVERY_STATUS_ERROR,
            success=False,
            control_id=control_id,
            request=request,
            context={
                "recovery_id": request.recovery_id,
                "workflow_id": request.workflow_id,
                "continuation_status": request.continuation_status,
                "recovery_status": request.recovery_status,
                "governance_status": request.governance_status,
                "checkpoint_status": request.checkpoint_status,
            },
            restored_state={},
            checks={
                "interruption_detected": False,
                "state_restored": False,
                "recovery_valid": False,
                "workflow_integrity": False,
                "runtime_continuity": False,
                "governance_alignment": False,
                "execution_consistency": False,
                "operational_stability": False,
            },
            continuation_allowed=False,
            lifecycle=(self._lifecycle(WORKFLOW_RECOVERY_STATUS_ERROR),),
            reasons=["workflow_recovery_control_error_contained"],
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
                CheckpointRecoveryResult,
                ExecutionResumeResult,
                HumanCheckpointControlResult,
            ),
        ):
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

    def _publish(self, result: WorkflowRecoveryControlResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_workflow_recovery_control_result",
        ):
            self.status.mark_workflow_recovery_control_result(result.to_dict())

    def _log_result(self, result: WorkflowRecoveryControlResult) -> None:
        if result.status == WORKFLOW_RECOVERY_STATUS_ERROR:
            logger.error(
                "workflow_recovery_control: error control_id=%s error=%s",
                result.control_id,
                result.error,
            )
            return
        if result.status == WORKFLOW_RECOVERY_STATUS_BLOCKED:
            logger.warning(
                "workflow_recovery_control: blocked control_id=%s reasons=%s",
                result.control_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "workflow_recovery_control: recovered control_id=%s workflow_id=%s",
            result.control_id,
            result.workflow_id,
        )
