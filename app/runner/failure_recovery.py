"""
Controlled failure recovery validation for Hermes operations.

This layer detects runtime failure context and validates whether recovery is
safe before continuation. It does not mutate runtime core, alter workflow
history, or resume execution directly.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

FAILURE_RECOVERY_STATUS_RECOVERED = "recovered"
FAILURE_RECOVERY_STATUS_BLOCKED = "blocked"
FAILURE_RECOVERY_STATUS_ERROR = "error"

SAFE_RUNTIME_STATUSES = {"active", "online", "ready", "stable", "resumed"}
SAFE_RECOVERY_STATUSES = {
    "ready",
    "restored",
    "recovered",
    "recovery_validated",
    "not_required",
}
SAFE_CONTINUATION_STATUSES = {
    "ready",
    "active",
    "continued",
    "resumed",
    "authorized_by_human",
    "recovery_validated",
}
SAFE_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "governance_approved",
    "stable",
}
SAFE_EXECUTION_STATUSES = {"ready", "stable", "resumed", "recovered"}


@dataclass(frozen=True)
class FailureRecoveryRequest:
    recovery_id: str | None = None
    workflow_id: str | None = None
    failure_type: str | None = None
    failure_detected: bool = False
    runtime_failures: tuple[str, ...] = field(default_factory=tuple)
    workflow_interruptions: tuple[str, ...] = field(default_factory=tuple)
    instability_conditions: tuple[str, ...] = field(default_factory=tuple)
    recovery_requirements: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    workflow_state: dict[str, Any] = field(default_factory=dict)
    restored_state: dict[str, Any] = field(default_factory=dict)
    runtime_state: dict[str, Any] = field(default_factory=dict)
    runtime_status: str | None = "online"
    recovery_status: str | None = "recovered"
    continuation_status: str | None = "recovery_validated"
    governance_status: str | None = "approved"
    execution_status: str | None = "recovered"
    operational_status: str | None = "stable"
    stress_test: dict[str, Any] | Any | None = None
    workflow_recovery_control: dict[str, Any] | Any | None = None
    checkpoint_recovery: dict[str, Any] | Any | None = None
    execution_resume: dict[str, Any] | Any | None = None
    ignore_runtime_failures_requested: bool = False
    minimize_corruption_risks_requested: bool = False
    overwrite_recovery_integrity_requested: bool = False
    alter_workflow_history_requested: bool = False
    continue_unsafe_execution_requested: bool = False
    recover_corrupt_runtime_requested: bool = False
    ignore_instability_conditions_requested: bool = False
    alter_governance_state_requested: bool = False
    hide_recovery_failures_requested: bool = False
    falsify_continuation_status_requested: bool = False
    ignore_blocking_conditions_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FailureRecoveryResult:
    status: str
    success: bool
    recovery_id: str
    workflow_id: str | None
    failure_type: str | None
    failure_detected: bool
    recovery_required: bool
    runtime_status: str | None
    recovery_status: str | None
    continuation_status: str | None
    governance_status: str | None
    execution_status: str | None
    workflow_integrity_valid: bool
    runtime_integrity_valid: bool
    recovery_status_valid: bool
    execution_continuity_valid: bool
    governance_consistency_valid: bool
    operational_stability_valid: bool
    recovery_safe: bool
    continuation_allowed: bool
    runtime_restored: bool
    workflow_traceability_preserved: bool
    workflow_history_preserved: bool
    governance_state_preserved: bool
    failure_conditions: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    recovery_report: dict[str, Any] = field(default_factory=dict)
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
            "recovery_id": self.recovery_id,
            "workflow_id": self.workflow_id,
            "failure_type": self.failure_type,
            "failure_detected": self.failure_detected,
            "recovery_required": self.recovery_required,
            "runtime_status": self.runtime_status,
            "recovery_status": self.recovery_status,
            "continuation_status": self.continuation_status,
            "governance_status": self.governance_status,
            "execution_status": self.execution_status,
            "workflow_integrity_valid": self.workflow_integrity_valid,
            "runtime_integrity_valid": self.runtime_integrity_valid,
            "recovery_status_valid": self.recovery_status_valid,
            "execution_continuity_valid": self.execution_continuity_valid,
            "governance_consistency_valid": self.governance_consistency_valid,
            "operational_stability_valid": self.operational_stability_valid,
            "recovery_safe": self.recovery_safe,
            "continuation_allowed": self.continuation_allowed,
            "runtime_restored": self.runtime_restored,
            "workflow_traceability_preserved": (
                self.workflow_traceability_preserved
            ),
            "workflow_history_preserved": self.workflow_history_preserved,
            "governance_state_preserved": self.governance_state_preserved,
            "failure_conditions": list(self.failure_conditions),
            "blocking_conditions": list(self.blocking_conditions),
            "recovery_report": dict(self.recovery_report),
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


class FailureRecovery:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def recover(
        self,
        request: FailureRecoveryRequest,
        recovery_permitted: bool = True,
    ) -> FailureRecoveryResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        recovery_id = request.recovery_id or str(uuid4())

        try:
            context = self._context(request)
            failure_detected = self._failure_detected(request, context)
            checks = self._checks(
                request=request,
                context=context,
                failure_detected=failure_detected,
                recovery_permitted=recovery_permitted,
            )
            failure_conditions = tuple(
                self._failure_conditions(request, context, checks)
            )
            blocking_conditions = tuple(
                self._blocking_conditions(request, checks)
            )
            reasons = self._reasons(
                request=request,
                checks=checks,
                blocking_conditions=blocking_conditions,
                recovery_permitted=recovery_permitted,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    FAILURE_RECOVERY_STATUS_BLOCKED
                    if blocked
                    else FAILURE_RECOVERY_STATUS_RECOVERED
                ),
                success=not blocked,
                recovery_id=recovery_id,
                request=request,
                context=context,
                failure_detected=failure_detected,
                checks=checks,
                failure_conditions=failure_conditions,
                blocking_conditions=blocking_conditions,
                reasons=reasons or ["failure_recovery_completed"],
                error=";".join(reasons) if blocked else None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                recovery_id=recovery_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def _context(self, request: FailureRecoveryRequest) -> dict[str, Any]:
        stress_test = self._as_dict(request.stress_test)
        workflow_recovery = self._as_dict(request.workflow_recovery_control)
        checkpoint_recovery = self._as_dict(request.checkpoint_recovery)
        execution_resume = self._as_dict(request.execution_resume)
        return {
            "workflow_id": (
                request.workflow_id
                or workflow_recovery.get("workflow_id")
                or checkpoint_recovery.get("workflow_id")
                or execution_resume.get("workflow_id")
                or stress_test.get("workflow_id")
            ),
            "runtime_status": request.runtime_status,
            "recovery_status": (
                request.recovery_status
                or workflow_recovery.get("status")
                or workflow_recovery.get("recovery_status")
                or checkpoint_recovery.get("recovery_status")
            ),
            "continuation_status": (
                request.continuation_status
                or workflow_recovery.get("continuation_status")
                or execution_resume.get("continuation_status")
            ),
            "governance_status": (
                request.governance_status
                or workflow_recovery.get("governance_status")
                or execution_resume.get("governance_status")
            ),
            "execution_status": (
                request.execution_status
                or execution_resume.get("status")
                or execution_resume.get("resume_status")
            ),
            "stress_test": stress_test,
            "workflow_recovery": workflow_recovery,
            "checkpoint_recovery": checkpoint_recovery,
            "execution_resume": execution_resume,
        }

    def _checks(
        self,
        request: FailureRecoveryRequest,
        context: dict[str, Any],
        failure_detected: bool,
        recovery_permitted: bool,
    ) -> dict[str, bool]:
        return {
            "workflow_integrity": bool(
                recovery_permitted
                and context["workflow_id"]
                and self._workflow_state_present(request, context)
            ),
            "runtime_integrity": bool(
                self._normalize(context["runtime_status"])
                in SAFE_RUNTIME_STATUSES
                and self._runtime_state_safe(request.runtime_state)
                and not self._upstream_blocked(context["stress_test"])
            ),
            "recovery_status": bool(
                self._normalize(context["recovery_status"])
                in SAFE_RECOVERY_STATUSES
                and not self._upstream_blocked(context["workflow_recovery"])
            ),
            "execution_continuity": bool(
                self._normalize(context["continuation_status"])
                in SAFE_CONTINUATION_STATUSES
                and self._normalize(context["execution_status"])
                in SAFE_EXECUTION_STATUSES
            ),
            "governance_consistency": (
                self._normalize(context["governance_status"])
                in SAFE_GOVERNANCE_STATUSES
            ),
            "operational_stability": bool(
                not request.instability_conditions
                and not request.blocking_conditions
                and (
                    failure_detected
                    or self._normalize(request.operational_status) == "stable"
                )
            ),
        }

    def _failure_detected(
        self,
        request: FailureRecoveryRequest,
        context: dict[str, Any],
    ) -> bool:
        stress_test = context["stress_test"]
        return bool(
            request.failure_detected
            or request.runtime_failures
            or request.workflow_interruptions
            or stress_test.get("degradation_detected")
            or self._normalize(stress_test.get("status")) in {"blocked", "error"}
        )

    def _failure_conditions(
        self,
        request: FailureRecoveryRequest,
        context: dict[str, Any],
        checks: dict[str, bool],
    ) -> list[str]:
        failures = [
            *[str(item) for item in request.runtime_failures],
            *[str(item) for item in request.workflow_interruptions],
            *[str(item) for item in request.recovery_requirements],
        ]
        stress_test = context["stress_test"]
        workflow_recovery = context["workflow_recovery"]
        if self._normalize(stress_test.get("status")) in {"blocked", "error"}:
            failures.append(f"stress_test_{stress_test.get('status')}")
        if stress_test.get("degradation_detected"):
            failures.extend(
                str(item) for item in stress_test.get("failure_conditions", [])
            )
        if self._normalize(workflow_recovery.get("status")) in {
            "blocked",
            "error",
        }:
            failures.append(
                f"workflow_recovery_control_{workflow_recovery.get('status')}"
            )
        for name, valid in checks.items():
            if not valid:
                failures.append(f"{name}_failed")
        return self._unique(failures)

    def _blocking_conditions(
        self,
        request: FailureRecoveryRequest,
        checks: dict[str, bool],
    ) -> list[str]:
        blocking = [
            *[str(item) for item in request.blocking_conditions],
            *[str(item) for item in request.instability_conditions],
        ]
        for name, valid in checks.items():
            if not valid:
                blocking.append(f"{name}_required")
        return self._unique(blocking)

    def _reasons(
        self,
        request: FailureRecoveryRequest,
        checks: dict[str, bool],
        blocking_conditions: tuple[str, ...],
        recovery_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not recovery_permitted:
            reasons.append("failure_recovery_not_permitted")
        for name, valid in checks.items():
            if not valid:
                reasons.append(f"{name}_required")
        if blocking_conditions:
            reasons.append("failure_recovery_blocking_conditions_active")
        if request.ignore_runtime_failures_requested:
            reasons.append("runtime_failure_ignore_blocked")
        if request.minimize_corruption_risks_requested:
            reasons.append("corruption_risk_minimization_blocked")
        if request.overwrite_recovery_integrity_requested:
            reasons.append("recovery_integrity_overwrite_blocked")
        if request.alter_workflow_history_requested:
            reasons.append("workflow_history_alteration_blocked")
        if request.continue_unsafe_execution_requested:
            reasons.append("unsafe_execution_continuation_blocked")
        if request.recover_corrupt_runtime_requested:
            reasons.append("corrupt_runtime_recovery_blocked")
        if request.ignore_instability_conditions_requested:
            reasons.append("instability_condition_ignore_blocked")
        if request.alter_governance_state_requested:
            reasons.append("governance_state_alteration_blocked")
        if request.hide_recovery_failures_requested:
            reasons.append("recovery_failure_concealment_blocked")
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
        recovery_id: str,
        request: FailureRecoveryRequest,
        context: dict[str, Any],
        failure_detected: bool,
        checks: dict[str, bool],
        failure_conditions: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> FailureRecoveryResult:
        finished_at = datetime.now(timezone.utc)
        recovery_safe = success and all(checks.values())
        return FailureRecoveryResult(
            status=status,
            success=success,
            recovery_id=recovery_id,
            workflow_id=context["workflow_id"],
            failure_type=request.failure_type,
            failure_detected=failure_detected,
            recovery_required=failure_detected or bool(request.recovery_requirements),
            runtime_status=context["runtime_status"],
            recovery_status=context["recovery_status"],
            continuation_status=context["continuation_status"],
            governance_status=context["governance_status"],
            execution_status=context["execution_status"],
            workflow_integrity_valid=checks["workflow_integrity"],
            runtime_integrity_valid=checks["runtime_integrity"],
            recovery_status_valid=checks["recovery_status"],
            execution_continuity_valid=checks["execution_continuity"],
            governance_consistency_valid=checks["governance_consistency"],
            operational_stability_valid=checks["operational_stability"],
            recovery_safe=recovery_safe,
            continuation_allowed=recovery_safe,
            runtime_restored=recovery_safe and checks["runtime_integrity"],
            workflow_traceability_preserved=success,
            workflow_history_preserved=success
            and not request.alter_workflow_history_requested,
            governance_state_preserved=success
            and not request.alter_governance_state_requested,
            failure_conditions=failure_conditions,
            blocking_conditions=blocking_conditions,
            recovery_report=self._report(
                checks,
                failure_conditions,
                blocking_conditions,
            ),
            human_visibility_payload=self._visibility(
                context,
                checks,
                failure_conditions,
                blocking_conditions,
            ),
            recovery_lifecycle=(
                self._lifecycle("failure_detection"),
                self._lifecycle("recovery_initialization"),
                self._lifecycle("controlled_recovery"),
                self._lifecycle("recovery_validation"),
                self._lifecycle("recovery_reporting"),
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
        failure_conditions: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "checks": dict(checks),
            "failure_conditions": list(failure_conditions),
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
        failure_conditions: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "recovery_status": context["recovery_status"],
            "runtime_integrity": checks["runtime_integrity"],
            "execution_continuity": checks["execution_continuity"],
            "blocking_conditions": list(blocking_conditions),
            "failure_conditions": list(failure_conditions),
            "governance_alignment": checks["governance_consistency"],
            "operational_stability": checks["operational_stability"],
        }

    def _error_result(
        self,
        recovery_id: str,
        request: FailureRecoveryRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> FailureRecoveryResult:
        return self._result(
            status=FAILURE_RECOVERY_STATUS_ERROR,
            success=False,
            recovery_id=recovery_id,
            request=request,
            context={
                "workflow_id": request.workflow_id,
                "runtime_status": request.runtime_status,
                "recovery_status": request.recovery_status,
                "continuation_status": request.continuation_status,
                "governance_status": request.governance_status,
                "execution_status": request.execution_status,
            },
            failure_detected=True,
            checks={
                "workflow_integrity": False,
                "runtime_integrity": False,
                "recovery_status": False,
                "execution_continuity": False,
                "governance_consistency": False,
                "operational_stability": False,
            },
            failure_conditions=tuple(request.runtime_failures),
            blocking_conditions=tuple(request.blocking_conditions),
            reasons=["failure_recovery_error_contained"],
            error=error,
            started=started,
            started_at=started_at,
        )

    def _workflow_state_present(
        self,
        request: FailureRecoveryRequest,
        context: dict[str, Any],
    ) -> bool:
        restored_state = dict(request.restored_state)
        restored_state.update(
            dict(context["workflow_recovery"].get("restored_state") or {})
        )
        workflow_state = dict(request.workflow_state)
        workflow_state.update(
            dict(context["workflow_recovery"].get("workflow_state") or {})
        )
        return bool(restored_state or workflow_state)

    def _runtime_state_safe(self, runtime_state: dict[str, Any]) -> bool:
        if not runtime_state:
            return True
        values = (
            runtime_state.get("state"),
            runtime_state.get("status"),
            runtime_state.get("loop_state"),
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

    def _publish(self, result: FailureRecoveryResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_failure_recovery_result",
        ):
            self.status.mark_failure_recovery_result(result.to_dict())

    def _log_result(self, result: FailureRecoveryResult) -> None:
        if result.status == FAILURE_RECOVERY_STATUS_ERROR:
            logger.error(
                "failure_recovery: error recovery_id=%s error=%s",
                result.recovery_id,
                result.error,
            )
            return
        if result.status == FAILURE_RECOVERY_STATUS_BLOCKED:
            logger.warning(
                "failure_recovery: blocked recovery_id=%s reasons=%s",
                result.recovery_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "failure_recovery: recovered recovery_id=%s workflow_id=%s",
            result.recovery_id,
            result.workflow_id,
        )
