"""
Human checkpoint control for Hermes workflow execution.

This layer detects official human checkpoints, pauses continuation safely, and
validates human approval before workflow continuation. It does not override
human authority, mutate runtime loop behavior, or continue blocked workflows.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.approval_gate import ApprovalGateResult
from app.runner.multi_step_execution_control import (
    MultiStepExecutionControlResult,
)

logger = logging.getLogger(__name__)

CHECKPOINT_STATUS_WAITING = "waiting"
CHECKPOINT_STATUS_APPROVED = "approved"
CHECKPOINT_STATUS_BLOCKED = "blocked"
CHECKPOINT_STATUS_CHANGES_REQUESTED = "changes_requested"
CHECKPOINT_STATUS_ESCALATED = "escalated"
CHECKPOINT_STATUS_ERROR = "error"

APPROVED_STATUSES = {"approved", "human_approved", "authorized_by_human"}
PENDING_STATUSES = {"pending", "waiting", "waiting_human_authority", "requested"}
REJECTED_STATUSES = {"rejected", "human_rejected", "blocked"}
CHANGE_STATUSES = {"needs_changes", "changes_requested"}
ESCALATED_STATUSES = {"escalated", "escalate"}
VALID_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "authorized_by_human",
    "waiting_human_authority",
}
VALID_CONTINUATION_STATUSES = {
    "ready",
    "paused",
    "frozen_waiting_human_approval",
    "authorized_by_human",
}
SAFE_RUNTIME_STATES = {"active", "online", "ready", "stable", "paused"}


@dataclass(frozen=True)
class HumanCheckpointControlRequest:
    checkpoint_id: str | None = None
    workflow_id: str | None = None
    approval_status: str | None = None
    execution_status: str | None = None
    governance_status: str | None = None
    continuation_status: str | None = None
    authority_status: str | None = None
    checkpoint_required: bool = True
    approval_gate: ApprovalGateResult | dict[str, Any] | Any | None = None
    multi_step_control: (
        MultiStepExecutionControlResult | dict[str, Any] | Any | None
    ) = None
    runtime_state: dict[str, Any] = field(default_factory=dict)
    approval_conditions: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    human_authority_valid: bool = True
    runtime_integrity_valid: bool = True
    operational_stability_valid: bool = True
    governance_consistency_valid: bool = True
    ignore_human_checkpoint_requested: bool = False
    continue_blocked_workflow_requested: bool = False
    overwrite_human_approval_requested: bool = False
    alter_governance_authority_requested: bool = False
    unauthorized_continuation_requested: bool = False
    falsify_approval_requested: bool = False
    hide_blocking_conditions_requested: bool = False
    minimize_governance_conflicts_requested: bool = False
    alter_execution_history_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HumanCheckpointControlResult:
    status: str
    success: bool
    control_id: str
    checkpoint_id: str | None
    workflow_id: str | None
    approval_status: str | None
    execution_status: str | None
    governance_status: str | None
    continuation_status: str | None
    authority_status: str | None
    checkpoint_detected: bool
    execution_paused: bool
    continuation_allowed: bool
    approval_legitimate: bool
    governance_alignment_valid: bool
    execution_continuity_valid: bool
    runtime_integrity_valid: bool
    workflow_consistency_valid: bool
    operational_stability_valid: bool
    human_authority_preserved: bool
    workflow_integrity_preserved: bool
    execution_traceability_preserved: bool
    approval_conditions: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    human_visibility_payload: dict[str, Any] = field(default_factory=dict)
    checkpoint_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "checkpoint_id": self.checkpoint_id,
            "workflow_id": self.workflow_id,
            "approval_status": self.approval_status,
            "execution_status": self.execution_status,
            "governance_status": self.governance_status,
            "continuation_status": self.continuation_status,
            "authority_status": self.authority_status,
            "checkpoint_detected": self.checkpoint_detected,
            "execution_paused": self.execution_paused,
            "continuation_allowed": self.continuation_allowed,
            "approval_legitimate": self.approval_legitimate,
            "governance_alignment_valid": self.governance_alignment_valid,
            "execution_continuity_valid": self.execution_continuity_valid,
            "runtime_integrity_valid": self.runtime_integrity_valid,
            "workflow_consistency_valid": self.workflow_consistency_valid,
            "operational_stability_valid": self.operational_stability_valid,
            "human_authority_preserved": self.human_authority_preserved,
            "workflow_integrity_preserved": self.workflow_integrity_preserved,
            "execution_traceability_preserved": (
                self.execution_traceability_preserved
            ),
            "approval_conditions": list(self.approval_conditions),
            "blocking_conditions": list(self.blocking_conditions),
            "human_visibility_payload": dict(self.human_visibility_payload),
            "checkpoint_lifecycle": [
                dict(entry) for entry in self.checkpoint_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class HumanCheckpointControl:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def control(
        self,
        request: HumanCheckpointControlRequest,
        checkpoint_permitted: bool = True,
    ) -> HumanCheckpointControlResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        control_id = str(uuid4())

        try:
            approval_gate = self._as_dict(request.approval_gate)
            multi_step = self._as_dict(request.multi_step_control)
            context = self._context(request, approval_gate, multi_step)
            checks = self._checks(
                request=request,
                context=context,
                checkpoint_permitted=checkpoint_permitted,
            )
            reasons = self._reasons(
                request=request,
                context=context,
                checks=checks,
                checkpoint_permitted=checkpoint_permitted,
            )
            if reasons:
                status = self._blocked_status(context)
                result = self._result(
                    status=status,
                    success=False,
                    control_id=control_id,
                    request=request,
                    context=context,
                    checks=checks,
                    execution_paused=True,
                    continuation_allowed=False,
                    lifecycle=(
                        self._lifecycle("checkpoint_detection"),
                        self._lifecycle("execution_pause"),
                        self._lifecycle(status),
                    ),
                    reasons=reasons,
                    error=";".join(reasons),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            approved = self._normalize(context["approval_status"]) in APPROVED_STATUSES
            status = (
                CHECKPOINT_STATUS_APPROVED
                if approved
                else CHECKPOINT_STATUS_WAITING
            )
            result = self._result(
                status=status,
                success=True,
                control_id=control_id,
                request=request,
                context=context,
                checks=checks,
                execution_paused=not approved,
                continuation_allowed=approved,
                lifecycle=(
                    self._lifecycle("checkpoint_detection"),
                    self._lifecycle("execution_pause"),
                    self._lifecycle("human_validation"),
                    self._lifecycle("continuation_control"),
                    self._lifecycle("checkpoint_reporting"),
                ),
                reasons=[
                    "human_checkpoint_approved"
                    if approved
                    else "waiting_human_approval"
                ],
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
        request: HumanCheckpointControlRequest,
        checkpoint_permitted: bool = True,
    ) -> HumanCheckpointControlResult:
        return self.control(
            request,
            checkpoint_permitted=checkpoint_permitted,
        )

    def _result(
        self,
        status: str,
        success: bool,
        control_id: str,
        request: HumanCheckpointControlRequest,
        context: dict[str, Any],
        checks: dict[str, bool],
        execution_paused: bool,
        continuation_allowed: bool,
        lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> HumanCheckpointControlResult:
        finished_at = datetime.now(timezone.utc)
        visibility = self._visibility(
            status=status,
            context=context,
            checks=checks,
            blocking_conditions=tuple(request.blocking_conditions),
            continuation_allowed=continuation_allowed,
        )
        return HumanCheckpointControlResult(
            status=status,
            success=success,
            control_id=control_id,
            checkpoint_id=context["checkpoint_id"],
            workflow_id=context["workflow_id"],
            approval_status=context["approval_status"],
            execution_status=context["execution_status"],
            governance_status=context["governance_status"],
            continuation_status=context["continuation_status"],
            authority_status=context["authority_status"],
            checkpoint_detected=checks["checkpoint_detected"],
            execution_paused=execution_paused,
            continuation_allowed=continuation_allowed,
            approval_legitimate=checks["approval_legitimate"],
            governance_alignment_valid=checks["governance_alignment"],
            execution_continuity_valid=checks["execution_continuity"],
            runtime_integrity_valid=checks["runtime_integrity"],
            workflow_consistency_valid=checks["workflow_consistency"],
            operational_stability_valid=checks["operational_stability"],
            human_authority_preserved=checks["human_authority"],
            workflow_integrity_preserved=success
            and checks["workflow_consistency"],
            execution_traceability_preserved=success,
            approval_conditions=tuple(request.approval_conditions),
            blocking_conditions=tuple(request.blocking_conditions),
            human_visibility_payload=visibility,
            checkpoint_lifecycle=lifecycle,
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons),
            error=error,
            metadata=dict(request.metadata),
        )

    def _context(
        self,
        request: HumanCheckpointControlRequest,
        approval_gate: dict[str, Any],
        multi_step: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "checkpoint_id": (
                request.checkpoint_id
                or approval_gate.get("approval_id")
                or approval_gate.get("checkpoint_id")
            ),
            "workflow_id": request.workflow_id or multi_step.get("workflow_id"),
            "approval_status": (
                request.approval_status
                or approval_gate.get("approval_status")
                or approval_gate.get("status")
            ),
            "execution_status": (
                request.execution_status
                or multi_step.get("status")
                or approval_gate.get("execution_status")
            ),
            "governance_status": (
                request.governance_status
                or approval_gate.get("governance_status")
            ),
            "continuation_status": (
                request.continuation_status
                or approval_gate.get("continuation_status")
                or multi_step.get("continuation_status")
            ),
            "authority_status": (
                request.authority_status
                or approval_gate.get("decided_by")
                or approval_gate.get("authority_status")
            ),
        }

    def _checks(
        self,
        request: HumanCheckpointControlRequest,
        context: dict[str, Any],
        checkpoint_permitted: bool,
    ) -> dict[str, bool]:
        approval_status = self._normalize(context["approval_status"])
        checkpoint_detected = bool(
            request.checkpoint_required or context["checkpoint_id"]
        )
        approval_legitimate = bool(
            approval_status in APPROVED_STATUSES
            or approval_status in PENDING_STATUSES
            or approval_status in CHANGE_STATUSES
            or approval_status in ESCALATED_STATUSES
            or approval_status in REJECTED_STATUSES
        )
        return {
            "checkpoint_detected": checkpoint_detected,
            "approval_legitimate": approval_legitimate
            and request.human_authority_valid,
            "governance_alignment": bool(
                request.governance_consistency_valid
                and self._normalize(context["governance_status"])
                in VALID_GOVERNANCE_STATUSES
            ),
            "execution_continuity": bool(
                self._normalize(context["continuation_status"])
                in VALID_CONTINUATION_STATUSES
            ),
            "runtime_integrity": bool(
                request.runtime_integrity_valid
                and self._runtime_safe(request.runtime_state)
            ),
            "workflow_consistency": bool(context["workflow_id"]),
            "operational_stability": bool(
                request.operational_stability_valid
                and not request.blocking_conditions
            ),
            "human_authority": bool(
                checkpoint_permitted and request.human_authority_valid
            ),
        }

    def _reasons(
        self,
        request: HumanCheckpointControlRequest,
        context: dict[str, Any],
        checks: dict[str, bool],
        checkpoint_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        approval_status = self._normalize(context["approval_status"])
        if not checkpoint_permitted:
            reasons.append("human_checkpoint_control_not_permitted")
        if not checks["checkpoint_detected"]:
            reasons.append("human_checkpoint_required")
        if not checks["approval_legitimate"]:
            reasons.append("approval_legitimacy_required")
        if approval_status in REJECTED_STATUSES:
            reasons.append("human_rejection_blocks_continuation")
        if approval_status in CHANGE_STATUSES:
            reasons.append("human_requested_changes")
        if approval_status in ESCALATED_STATUSES:
            reasons.append("human_escalation_requested")
        if not checks["governance_alignment"]:
            reasons.append("governance_alignment_required")
        if not checks["execution_continuity"]:
            reasons.append("execution_continuity_required")
        if not checks["runtime_integrity"]:
            reasons.append("runtime_integrity_required")
        if not checks["workflow_consistency"]:
            reasons.append("workflow_consistency_required")
        if not checks["operational_stability"]:
            reasons.append("operational_stability_required")
        if not checks["human_authority"]:
            reasons.append("human_authority_required")
        reasons.extend(str(item) for item in request.blocking_conditions if item)
        if request.ignore_human_checkpoint_requested:
            reasons.append("human_checkpoint_ignore_blocked")
        if request.continue_blocked_workflow_requested:
            reasons.append("blocked_workflow_continuation_blocked")
        if request.overwrite_human_approval_requested:
            reasons.append("human_approval_overwrite_blocked")
        if request.alter_governance_authority_requested:
            reasons.append("governance_authority_alteration_blocked")
        if request.unauthorized_continuation_requested:
            reasons.append("unauthorized_continuation_blocked")
        if request.falsify_approval_requested:
            reasons.append("approval_falsification_blocked")
        if (
            request.hide_blocking_conditions_requested
            and request.blocking_conditions
        ):
            reasons.append("blocking_condition_concealment_blocked")
        if request.minimize_governance_conflicts_requested:
            reasons.append("governance_conflict_minimization_blocked")
        if request.alter_execution_history_requested:
            reasons.append("execution_history_alteration_blocked")
        return self._unique(reasons)

    def _blocked_status(self, context: dict[str, Any]) -> str:
        approval_status = self._normalize(context["approval_status"])
        if approval_status in CHANGE_STATUSES:
            return CHECKPOINT_STATUS_CHANGES_REQUESTED
        if approval_status in ESCALATED_STATUSES:
            return CHECKPOINT_STATUS_ESCALATED
        return CHECKPOINT_STATUS_BLOCKED

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
        context: dict[str, Any],
        checks: dict[str, bool],
        blocking_conditions: tuple[str, ...],
        continuation_allowed: bool,
    ) -> dict[str, Any]:
        return {
            "checkpoint_status": status,
            "approval_conditions": list(context.values()),
            "execution_continuity": checks["execution_continuity"],
            "runtime_integrity": checks["runtime_integrity"],
            "blocking_conditions": list(blocking_conditions),
            "governance_alignment": checks["governance_alignment"],
            "continuation_allowed": continuation_allowed,
        }

    def _error_result(
        self,
        control_id: str,
        request: HumanCheckpointControlRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> HumanCheckpointControlResult:
        return self._result(
            status=CHECKPOINT_STATUS_ERROR,
            success=False,
            control_id=control_id,
            request=request,
            context={
                "checkpoint_id": request.checkpoint_id,
                "workflow_id": request.workflow_id,
                "approval_status": request.approval_status,
                "execution_status": request.execution_status,
                "governance_status": request.governance_status,
                "continuation_status": request.continuation_status,
                "authority_status": request.authority_status,
            },
            checks={
                "checkpoint_detected": False,
                "approval_legitimate": False,
                "governance_alignment": False,
                "execution_continuity": False,
                "runtime_integrity": False,
                "workflow_consistency": False,
                "operational_stability": False,
                "human_authority": False,
            },
            execution_paused=True,
            continuation_allowed=False,
            lifecycle=(self._lifecycle(CHECKPOINT_STATUS_ERROR),),
            reasons=["human_checkpoint_control_error_contained"],
            error=error,
            started=started,
            started_at=started_at,
        )

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, (ApprovalGateResult, MultiStepExecutionControlResult)):
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

    def _publish(self, result: HumanCheckpointControlResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_human_checkpoint_control_result",
        ):
            self.status.mark_human_checkpoint_control_result(result.to_dict())

    def _log_result(self, result: HumanCheckpointControlResult) -> None:
        if result.status == CHECKPOINT_STATUS_ERROR:
            logger.error(
                "human_checkpoint_control: error control_id=%s error=%s",
                result.control_id,
                result.error,
            )
            return
        if result.status in {
            CHECKPOINT_STATUS_BLOCKED,
            CHECKPOINT_STATUS_CHANGES_REQUESTED,
            CHECKPOINT_STATUS_ESCALATED,
        }:
            logger.warning(
                "human_checkpoint_control: %s control_id=%s reasons=%s",
                result.status,
                result.control_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "human_checkpoint_control: %s control_id=%s workflow_id=%s",
            result.status,
            result.control_id,
            result.workflow_id,
        )
