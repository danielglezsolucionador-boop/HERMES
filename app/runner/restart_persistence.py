"""
Restart persistence validation for Hermes operational continuity.

This layer validates that execution state, workflow state, runtime context, and
governance alignment survive a runtime restart before continuation is allowed.
It does not write persistence storage or resume execution directly.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

RESTART_PERSISTENCE_STATUS_RESTORED = "restored"
RESTART_PERSISTENCE_STATUS_BLOCKED = "blocked"
RESTART_PERSISTENCE_STATUS_ERROR = "error"

SAFE_RUNTIME_STATUSES = {"active", "online", "ready", "stable", "resumed"}
SAFE_RESTART_STATUSES = {
    "restored",
    "persistent",
    "recovered",
    "restart_validated",
}
SAFE_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "governance_approved",
    "stable",
}
SAFE_RECOVERY_STATUSES = {
    "recovered",
    "restored",
    "recovery_validated",
    "not_required",
}
SAFE_EXECUTION_STATUSES = {"ready", "stable", "resumed", "recovered"}
SAFE_CONTINUATION_STATUSES = {
    "ready",
    "active",
    "continued",
    "resumed",
    "authorized_by_human",
    "recovery_validated",
}


@dataclass(frozen=True)
class RestartPersistenceRequest:
    restart_id: str | None = None
    workflow_id: str | None = None
    runtime_restart_detected: bool = False
    execution_interruption_detected: bool = False
    execution_state: dict[str, Any] = field(default_factory=dict)
    workflow_state: dict[str, Any] = field(default_factory=dict)
    restored_state: dict[str, Any] = field(default_factory=dict)
    runtime_context: dict[str, Any] = field(default_factory=dict)
    restart_status: str | None = "restored"
    continuation_status: str | None = "recovery_validated"
    governance_status: str | None = "approved"
    recovery_status: str | None = "recovered"
    execution_status: str | None = "resumed"
    operational_status: str | None = "stable"
    checkpoint_recovery: dict[str, Any] | Any | None = None
    execution_resume: dict[str, Any] | Any | None = None
    failure_recovery: dict[str, Any] | Any | None = None
    recovery_conditions: tuple[str, ...] = field(default_factory=tuple)
    restart_inconsistencies: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    ignore_restart_inconsistencies_requested: bool = False
    overwrite_workflow_history_requested: bool = False
    alter_governance_state_requested: bool = False
    continue_corrupt_runtime_requested: bool = False
    restore_corrupt_runtime_requested: bool = False
    hide_restart_failures_requested: bool = False
    minimize_corruption_risks_requested: bool = False
    falsify_continuation_status_requested: bool = False
    ignore_blocking_conditions_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RestartPersistenceResult:
    status: str
    success: bool
    restart_id: str
    workflow_id: str | None
    restart_detected: bool
    restart_status: str | None
    continuation_status: str | None
    governance_status: str | None
    recovery_status: str | None
    execution_status: str | None
    execution_state_valid: bool
    workflow_continuity_valid: bool
    runtime_context_valid: bool
    restart_status_valid: bool
    governance_alignment_valid: bool
    recovery_status_valid: bool
    execution_consistency_valid: bool
    operational_stability_valid: bool
    persistence_valid: bool
    continuation_allowed: bool
    execution_state_restored: bool
    workflow_traceability_preserved: bool
    workflow_history_preserved: bool
    governance_state_preserved: bool
    restart_conditions: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    persistence_report: dict[str, Any] = field(default_factory=dict)
    human_visibility_payload: dict[str, Any] = field(default_factory=dict)
    persistence_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "restart_id": self.restart_id,
            "workflow_id": self.workflow_id,
            "restart_detected": self.restart_detected,
            "restart_status": self.restart_status,
            "continuation_status": self.continuation_status,
            "governance_status": self.governance_status,
            "recovery_status": self.recovery_status,
            "execution_status": self.execution_status,
            "execution_state_valid": self.execution_state_valid,
            "workflow_continuity_valid": self.workflow_continuity_valid,
            "runtime_context_valid": self.runtime_context_valid,
            "restart_status_valid": self.restart_status_valid,
            "governance_alignment_valid": self.governance_alignment_valid,
            "recovery_status_valid": self.recovery_status_valid,
            "execution_consistency_valid": self.execution_consistency_valid,
            "operational_stability_valid": self.operational_stability_valid,
            "persistence_valid": self.persistence_valid,
            "continuation_allowed": self.continuation_allowed,
            "execution_state_restored": self.execution_state_restored,
            "workflow_traceability_preserved": (
                self.workflow_traceability_preserved
            ),
            "workflow_history_preserved": self.workflow_history_preserved,
            "governance_state_preserved": self.governance_state_preserved,
            "restart_conditions": list(self.restart_conditions),
            "blocking_conditions": list(self.blocking_conditions),
            "persistence_report": dict(self.persistence_report),
            "human_visibility_payload": dict(self.human_visibility_payload),
            "persistence_lifecycle": [
                dict(entry) for entry in self.persistence_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class RestartPersistence:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def restore(
        self,
        request: RestartPersistenceRequest,
        continuation_permitted: bool = True,
    ) -> RestartPersistenceResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        restart_id = request.restart_id or str(uuid4())

        try:
            context = self._context(request)
            restart_detected = self._restart_detected(request, context)
            checks = self._checks(
                request=request,
                context=context,
                continuation_permitted=continuation_permitted,
            )
            restart_conditions = tuple(
                self._restart_conditions(request, context, checks)
            )
            blocking_conditions = tuple(
                self._blocking_conditions(request, checks)
            )
            reasons = self._reasons(
                request=request,
                checks=checks,
                blocking_conditions=blocking_conditions,
                continuation_permitted=continuation_permitted,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    RESTART_PERSISTENCE_STATUS_BLOCKED
                    if blocked
                    else RESTART_PERSISTENCE_STATUS_RESTORED
                ),
                success=not blocked,
                restart_id=restart_id,
                request=request,
                context=context,
                restart_detected=restart_detected,
                checks=checks,
                restart_conditions=restart_conditions,
                blocking_conditions=blocking_conditions,
                reasons=reasons or ["restart_persistence_completed"],
                error=";".join(reasons) if blocked else None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                restart_id=restart_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def _context(self, request: RestartPersistenceRequest) -> dict[str, Any]:
        checkpoint = self._as_dict(request.checkpoint_recovery)
        resume = self._as_dict(request.execution_resume)
        failure_recovery = self._as_dict(request.failure_recovery)
        return {
            "workflow_id": (
                request.workflow_id
                or checkpoint.get("workflow_id")
                or resume.get("workflow_id")
                or failure_recovery.get("workflow_id")
            ),
            "restart_status": request.restart_status,
            "continuation_status": (
                request.continuation_status
                or resume.get("continuation_status")
                or failure_recovery.get("continuation_status")
            ),
            "governance_status": (
                request.governance_status
                or resume.get("governance_status")
                or failure_recovery.get("governance_status")
            ),
            "recovery_status": (
                request.recovery_status
                or checkpoint.get("recovery_status")
                or failure_recovery.get("recovery_status")
            ),
            "execution_status": request.execution_status or resume.get("status"),
            "checkpoint": checkpoint,
            "resume": resume,
            "failure_recovery": failure_recovery,
        }

    def _checks(
        self,
        request: RestartPersistenceRequest,
        context: dict[str, Any],
        continuation_permitted: bool,
    ) -> dict[str, bool]:
        return {
            "execution_state": bool(
                continuation_permitted
                and self._execution_state_present(request, context)
            ),
            "workflow_continuity": bool(
                context["workflow_id"]
                and self._workflow_state_present(request, context)
            ),
            "runtime_context": bool(
                self._runtime_context_safe(request.runtime_context)
                and not self._upstream_blocked(context["failure_recovery"])
            ),
            "restart_status": (
                self._normalize(context["restart_status"])
                in SAFE_RESTART_STATUSES
            ),
            "governance_alignment": (
                self._normalize(context["governance_status"])
                in SAFE_GOVERNANCE_STATUSES
            ),
            "recovery_status": (
                self._normalize(context["recovery_status"])
                in SAFE_RECOVERY_STATUSES
            ),
            "execution_consistency": bool(
                self._normalize(context["execution_status"])
                in SAFE_EXECUTION_STATUSES
                and self._normalize(context["continuation_status"])
                in SAFE_CONTINUATION_STATUSES
            ),
            "operational_stability": bool(
                self._normalize(request.operational_status) == "stable"
                and not request.restart_inconsistencies
                and not request.blocking_conditions
            ),
        }

    def _restart_detected(
        self,
        request: RestartPersistenceRequest,
        context: dict[str, Any],
    ) -> bool:
        failure_recovery = context["failure_recovery"]
        return bool(
            request.runtime_restart_detected
            or request.execution_interruption_detected
            or failure_recovery.get("failure_detected")
        )

    def _restart_conditions(
        self,
        request: RestartPersistenceRequest,
        context: dict[str, Any],
        checks: dict[str, bool],
    ) -> list[str]:
        conditions = [
            *[str(item) for item in request.recovery_conditions],
            *[str(item) for item in request.restart_inconsistencies],
        ]
        if self._upstream_blocked(context["failure_recovery"]):
            conditions.append("failure_recovery_blocked")
        for name, valid in checks.items():
            if not valid:
                conditions.append(f"{name}_failed")
        return self._unique(conditions)

    def _blocking_conditions(
        self,
        request: RestartPersistenceRequest,
        checks: dict[str, bool],
    ) -> list[str]:
        blocking = [
            *[str(item) for item in request.blocking_conditions],
            *[str(item) for item in request.restart_inconsistencies],
        ]
        for name, valid in checks.items():
            if not valid:
                blocking.append(f"{name}_required")
        return self._unique(blocking)

    def _reasons(
        self,
        request: RestartPersistenceRequest,
        checks: dict[str, bool],
        blocking_conditions: tuple[str, ...],
        continuation_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not continuation_permitted:
            reasons.append("restart_continuation_not_permitted")
        for name, valid in checks.items():
            if not valid:
                reasons.append(f"{name}_required")
        if blocking_conditions:
            reasons.append("restart_blocking_conditions_active")
        if request.ignore_restart_inconsistencies_requested:
            reasons.append("restart_inconsistency_ignore_blocked")
        if request.overwrite_workflow_history_requested:
            reasons.append("workflow_history_overwrite_blocked")
        if request.alter_governance_state_requested:
            reasons.append("governance_state_alteration_blocked")
        if request.continue_corrupt_runtime_requested:
            reasons.append("corrupt_runtime_continuation_blocked")
        if request.restore_corrupt_runtime_requested:
            reasons.append("corrupt_runtime_restoration_blocked")
        if request.hide_restart_failures_requested:
            reasons.append("restart_failure_concealment_blocked")
        if request.minimize_corruption_risks_requested:
            reasons.append("corruption_risk_minimization_blocked")
        if request.falsify_continuation_status_requested:
            reasons.append("continuation_status_falsification_blocked")
        if (
            request.ignore_blocking_conditions_requested
            and blocking_conditions
        ):
            reasons.append("blocking_condition_ignore_blocked")
        return self._unique(reasons)

    def _result(
        self,
        status: str,
        success: bool,
        restart_id: str,
        request: RestartPersistenceRequest,
        context: dict[str, Any],
        restart_detected: bool,
        checks: dict[str, bool],
        restart_conditions: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> RestartPersistenceResult:
        finished_at = datetime.now(timezone.utc)
        persistence_valid = success and all(checks.values())
        return RestartPersistenceResult(
            status=status,
            success=success,
            restart_id=restart_id,
            workflow_id=context["workflow_id"],
            restart_detected=restart_detected,
            restart_status=context["restart_status"],
            continuation_status=context["continuation_status"],
            governance_status=context["governance_status"],
            recovery_status=context["recovery_status"],
            execution_status=context["execution_status"],
            execution_state_valid=checks["execution_state"],
            workflow_continuity_valid=checks["workflow_continuity"],
            runtime_context_valid=checks["runtime_context"],
            restart_status_valid=checks["restart_status"],
            governance_alignment_valid=checks["governance_alignment"],
            recovery_status_valid=checks["recovery_status"],
            execution_consistency_valid=checks["execution_consistency"],
            operational_stability_valid=checks["operational_stability"],
            persistence_valid=persistence_valid,
            continuation_allowed=persistence_valid,
            execution_state_restored=persistence_valid,
            workflow_traceability_preserved=success,
            workflow_history_preserved=success
            and not request.overwrite_workflow_history_requested,
            governance_state_preserved=success
            and not request.alter_governance_state_requested,
            restart_conditions=restart_conditions,
            blocking_conditions=blocking_conditions,
            persistence_report=self._report(
                checks,
                restart_conditions,
                blocking_conditions,
            ),
            human_visibility_payload=self._visibility(
                context,
                checks,
                restart_conditions,
                blocking_conditions,
            ),
            persistence_lifecycle=(
                self._lifecycle("restart_detection"),
                self._lifecycle("state_restoration"),
                self._lifecycle("persistence_validation"),
                self._lifecycle("controlled_continuation"),
                self._lifecycle("restart_reporting"),
            ),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons),
            error=error,
            metadata=dict(request.metadata),
        )

    def _report(
        self,
        checks: dict[str, bool],
        restart_conditions: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "checks": dict(checks),
            "restart_conditions": list(restart_conditions),
            "blocking_conditions": list(blocking_conditions),
            "continuation_status": (
                "allowed"
                if all(checks.values()) and not blocking_conditions
                else "blocked"
            ),
        }

    def _visibility(
        self,
        context: dict[str, Any],
        checks: dict[str, bool],
        restart_conditions: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "restart_status": context["restart_status"],
            "workflow_continuity": checks["workflow_continuity"],
            "runtime_integrity": checks["runtime_context"],
            "recovery_conditions": list(restart_conditions),
            "blocking_conditions": list(blocking_conditions),
            "governance_alignment": checks["governance_alignment"],
            "operational_stability": checks["operational_stability"],
        }

    def _error_result(
        self,
        restart_id: str,
        request: RestartPersistenceRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> RestartPersistenceResult:
        return self._result(
            status=RESTART_PERSISTENCE_STATUS_ERROR,
            success=False,
            restart_id=restart_id,
            request=request,
            context={
                "workflow_id": request.workflow_id,
                "restart_status": request.restart_status,
                "continuation_status": request.continuation_status,
                "governance_status": request.governance_status,
                "recovery_status": request.recovery_status,
                "execution_status": request.execution_status,
            },
            restart_detected=True,
            checks={
                "execution_state": False,
                "workflow_continuity": False,
                "runtime_context": False,
                "restart_status": False,
                "governance_alignment": False,
                "recovery_status": False,
                "execution_consistency": False,
                "operational_stability": False,
            },
            restart_conditions=tuple(request.restart_inconsistencies),
            blocking_conditions=tuple(request.blocking_conditions),
            reasons=["restart_persistence_error_contained"],
            error=error,
            started=started,
            started_at=started_at,
        )

    def _execution_state_present(
        self,
        request: RestartPersistenceRequest,
        context: dict[str, Any],
    ) -> bool:
        resume = context["resume"]
        checkpoint = context["checkpoint"]
        return bool(
            request.execution_state
            or request.restored_state
            or resume.get("restored_state")
            or resume.get("execution_context")
            or checkpoint.get("execution_context")
        )

    def _workflow_state_present(
        self,
        request: RestartPersistenceRequest,
        context: dict[str, Any],
    ) -> bool:
        resume = context["resume"]
        checkpoint = context["checkpoint"]
        return bool(
            request.workflow_state
            or request.restored_state
            or resume.get("restored_state")
            or checkpoint.get("restored_state")
        )

    def _runtime_context_safe(self, runtime_context: dict[str, Any]) -> bool:
        if not runtime_context:
            return True
        values = (
            runtime_context.get("state"),
            runtime_context.get("status"),
            runtime_context.get("loop_state"),
        )
        return any(
            self._normalize(value) in SAFE_RUNTIME_STATUSES
            for value in values
        )

    def _upstream_blocked(self, result: dict[str, Any]) -> bool:
        if not result:
            return False
        return self._normalize(result.get("status")) in {"blocked", "error"}

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

    def _publish(self, result: RestartPersistenceResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_restart_persistence_result",
        ):
            self.status.mark_restart_persistence_result(result.to_dict())

    def _log_result(self, result: RestartPersistenceResult) -> None:
        if result.status == RESTART_PERSISTENCE_STATUS_ERROR:
            logger.error(
                "restart_persistence: error restart_id=%s error=%s",
                result.restart_id,
                result.error,
            )
            return
        if result.status == RESTART_PERSISTENCE_STATUS_BLOCKED:
            logger.warning(
                "restart_persistence: blocked restart_id=%s reasons=%s",
                result.restart_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "restart_persistence: restored restart_id=%s workflow_id=%s",
            result.restart_id,
            result.workflow_id,
        )
