"""
Final operational validation for Hermes enterprise runtime readiness.

This layer aggregates reported runtime, workflow, governance, audit, security,
knowledge-core, and stability status into one final readiness decision. It does
not start execution, mutate runtime core, or approve unsafe production state.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

FINAL_VALIDATION_STATUS_READY = "ready"
FINAL_VALIDATION_STATUS_BLOCKED = "blocked"
FINAL_VALIDATION_STATUS_ERROR = "error"

SAFE_RUNTIME_STATUSES = {"active", "online", "ready", "stable", "resumed", "ok"}
SAFE_WORKFLOW_STATUSES = {"ready", "stable", "validated", "completed", "ok"}
SAFE_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "governance_approved",
    "stable",
}
SAFE_AUDIT_STATUSES = {"approved", "passed", "validated", "clean", "stable"}
SAFE_SECURITY_STATUSES = {
    "protected",
    "validated",
    "stable",
    "approved",
    "ok",
    "clear",
}
SAFE_KNOWLEDGE_CORE_STATUSES = {"validated", "loaded", "ready", "stable", "ok"}
SAFE_STABILITY_STATUSES = {
    "stable",
    "validated",
    "hardened",
    "resilient",
    "ready",
    "ok",
}
SAFE_UPSTREAM_STATUSES = {
    "approved",
    "clean",
    "hardened",
    "observed",
    "passed",
    "protected",
    "ready",
    "recovered",
    "resilient",
    "restored",
    "stable",
    "validated",
}


@dataclass(frozen=True)
class FinalOperationalValidationRequest:
    validation_id: str | None = None
    workflow_id: str | None = None
    runtime_status: dict[str, Any] = field(default_factory=dict)
    workflow_status: dict[str, Any] = field(default_factory=dict)
    governance_status: dict[str, Any] = field(default_factory=dict)
    audit_status: dict[str, Any] = field(default_factory=dict)
    security_status: dict[str, Any] = field(default_factory=dict)
    knowledge_core_status: dict[str, Any] = field(default_factory=dict)
    stability_status: dict[str, Any] = field(default_factory=dict)
    authority_status: dict[str, Any] = field(default_factory=dict)
    execution_status: dict[str, Any] = field(default_factory=dict)
    workflow_validation: dict[str, Any] | Any | None = None
    governance_validation: dict[str, Any] | Any | None = None
    audit_validation: dict[str, Any] | Any | None = None
    security_validation: dict[str, Any] | Any | None = None
    knowledge_core_validation: dict[str, Any] | Any | None = None
    stress_tests: dict[str, Any] | Any | None = None
    failure_recovery: dict[str, Any] | Any | None = None
    restart_persistence: dict[str, Any] | Any | None = None
    long_running_validation: dict[str, Any] | Any | None = None
    observability_base: dict[str, Any] | Any | None = None
    production_hardening: dict[str, Any] | Any | None = None
    risks: tuple[str, ...] = field(default_factory=tuple)
    blockers: tuple[str, ...] = field(default_factory=tuple)
    approve_unstable_runtime_requested: bool = False
    hide_critical_failures_requested: bool = False
    ignore_governance_conflicts_requested: bool = False
    falsify_readiness_requested: bool = False
    continue_unsafe_production_requested: bool = False
    override_authority_requested: bool = False
    skip_audit_requested: bool = False
    bypass_security_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FinalOperationalValidationResult:
    status: str
    success: bool
    validation_id: str
    workflow_id: str | None
    runtime_validation_valid: bool
    workflow_validation_valid: bool
    governance_validation_valid: bool
    audit_validation_valid: bool
    security_validation_valid: bool
    knowledge_core_validation_valid: bool
    stability_validation_valid: bool
    authority_validation_valid: bool
    execution_validation_valid: bool
    final_readiness_valid: bool
    production_safe: bool
    continuation_allowed: bool
    risks_detected: bool
    blockers_detected: bool
    validations_executed: tuple[str, ...] = field(default_factory=tuple)
    risks: tuple[str, ...] = field(default_factory=tuple)
    blockers: tuple[str, ...] = field(default_factory=tuple)
    final_report: dict[str, Any] = field(default_factory=dict)
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
            "runtime_validation_valid": self.runtime_validation_valid,
            "workflow_validation_valid": self.workflow_validation_valid,
            "governance_validation_valid": self.governance_validation_valid,
            "audit_validation_valid": self.audit_validation_valid,
            "security_validation_valid": self.security_validation_valid,
            "knowledge_core_validation_valid": (
                self.knowledge_core_validation_valid
            ),
            "stability_validation_valid": self.stability_validation_valid,
            "authority_validation_valid": self.authority_validation_valid,
            "execution_validation_valid": self.execution_validation_valid,
            "final_readiness_valid": self.final_readiness_valid,
            "production_safe": self.production_safe,
            "continuation_allowed": self.continuation_allowed,
            "risks_detected": self.risks_detected,
            "blockers_detected": self.blockers_detected,
            "validations_executed": list(self.validations_executed),
            "risks": list(self.risks),
            "blockers": list(self.blockers),
            "final_report": dict(self.final_report),
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


class FinalOperationalValidation:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def validate(
        self,
        request: FinalOperationalValidationRequest,
    ) -> FinalOperationalValidationResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        validation_id = request.validation_id or str(uuid4())

        try:
            context = self._context(request)
            checks = self._checks(request, context)
            risks = tuple(self._risks(request, context, checks))
            blockers = tuple(self._blockers(request, checks, risks))
            reasons = self._reasons(request, checks, risks, blockers)
            blocked = bool(reasons)
            result = self._result(
                status=(
                    FINAL_VALIDATION_STATUS_BLOCKED
                    if blocked
                    else FINAL_VALIDATION_STATUS_READY
                ),
                success=not blocked,
                validation_id=validation_id,
                request=request,
                context=context,
                checks=checks,
                risks=risks,
                blockers=blockers,
                reasons=reasons or ["final_operational_validation_completed"],
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

    def _context(
        self,
        request: FinalOperationalValidationRequest,
    ) -> dict[str, Any]:
        return {
            "workflow_validation": self._as_dict(request.workflow_validation),
            "governance_validation": self._as_dict(
                request.governance_validation
            ),
            "audit_validation": self._as_dict(request.audit_validation),
            "security_validation": self._as_dict(request.security_validation),
            "knowledge_core_validation": self._as_dict(
                request.knowledge_core_validation
            ),
            "stress_tests": self._as_dict(request.stress_tests),
            "failure_recovery": self._as_dict(request.failure_recovery),
            "restart_persistence": self._as_dict(request.restart_persistence),
            "long_running_validation": self._as_dict(
                request.long_running_validation
            ),
            "observability_base": self._as_dict(request.observability_base),
            "production_hardening": self._as_dict(
                request.production_hardening
            ),
        }

    def _checks(
        self,
        request: FinalOperationalValidationRequest,
        context: dict[str, Any],
    ) -> dict[str, bool]:
        return {
            "runtime_validation": bool(
                request.runtime_status
                and self._status_safe(
                    request.runtime_status,
                    SAFE_RUNTIME_STATUSES,
                )
            ),
            "workflow_validation": bool(
                request.workflow_status
                and self._status_safe(
                    request.workflow_status,
                    SAFE_WORKFLOW_STATUSES,
                )
                and self._upstream_safe(context["workflow_validation"])
            ),
            "governance_validation": bool(
                request.governance_status
                and self._status_safe(
                    request.governance_status,
                    SAFE_GOVERNANCE_STATUSES,
                )
                and self._upstream_safe(context["governance_validation"])
            ),
            "audit_validation": bool(
                request.audit_status
                and self._status_safe(request.audit_status, SAFE_AUDIT_STATUSES)
                and self._upstream_safe(context["audit_validation"])
            ),
            "security_validation": bool(
                request.security_status
                and self._status_safe(
                    request.security_status,
                    SAFE_SECURITY_STATUSES,
                )
                and self._upstream_safe(context["security_validation"])
            ),
            "knowledge_core_validation": bool(
                request.knowledge_core_status
                and self._status_safe(
                    request.knowledge_core_status,
                    SAFE_KNOWLEDGE_CORE_STATUSES,
                )
                and self._upstream_safe(context["knowledge_core_validation"])
            ),
            "stability_validation": bool(
                request.stability_status
                and self._status_safe(
                    request.stability_status,
                    SAFE_STABILITY_STATUSES,
                )
                and self._stability_context_safe(context)
            ),
            "authority_validation": self._authority_safe(
                request.authority_status
            ),
            "execution_validation": bool(
                request.execution_status
                and self._status_safe(
                    request.execution_status,
                    SAFE_WORKFLOW_STATUSES | SAFE_RUNTIME_STATUSES,
                )
            ),
        }

    def _risks(
        self,
        request: FinalOperationalValidationRequest,
        context: dict[str, Any],
        checks: dict[str, bool],
    ) -> list[str]:
        risks = [str(item) for item in request.risks]
        for name, valid in checks.items():
            if not valid:
                risks.append(f"{name}_failed")
        for name, result in context.items():
            if result and not self._upstream_safe(result):
                risks.append(f"{name}_{result.get('status')}")
            for key in (
                "risks",
                "risk_conditions",
                "failure_conditions",
                "anomaly_conditions",
                "blocking_conditions",
            ):
                risks.extend(str(item) for item in result.get(key, []))
        return self._unique(risks)

    def _blockers(
        self,
        request: FinalOperationalValidationRequest,
        checks: dict[str, bool],
        risks: tuple[str, ...],
    ) -> list[str]:
        blockers = [str(item) for item in request.blockers]
        for name, valid in checks.items():
            if not valid:
                blockers.append(f"{name}_required")
        if risks:
            blockers.append("final_validation_risks_active")
        return self._unique(blockers)

    def _reasons(
        self,
        request: FinalOperationalValidationRequest,
        checks: dict[str, bool],
        risks: tuple[str, ...],
        blockers: tuple[str, ...],
    ) -> list[str]:
        reasons: list[str] = []
        for name, valid in checks.items():
            if not valid:
                reasons.append(f"{name}_required")
        if risks:
            reasons.append("final_validation_risks_detected")
        if blockers:
            reasons.append("final_validation_blockers_active")
        if request.approve_unstable_runtime_requested:
            reasons.append("unstable_runtime_approval_blocked")
        if request.hide_critical_failures_requested:
            reasons.append("critical_failure_concealment_blocked")
        if request.ignore_governance_conflicts_requested:
            reasons.append("governance_conflict_ignore_blocked")
        if request.falsify_readiness_requested:
            reasons.append("readiness_falsification_blocked")
        if request.continue_unsafe_production_requested:
            reasons.append("unsafe_production_continuation_blocked")
        if request.override_authority_requested:
            reasons.append("authority_override_blocked")
        if request.skip_audit_requested:
            reasons.append("audit_skip_blocked")
        if request.bypass_security_requested:
            reasons.append("security_bypass_blocked")
        return self._unique(reasons)

    def _result(
        self,
        status: str,
        success: bool,
        validation_id: str,
        request: FinalOperationalValidationRequest,
        context: dict[str, Any],
        checks: dict[str, bool],
        risks: tuple[str, ...],
        blockers: tuple[str, ...],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> FinalOperationalValidationResult:
        finished_at = datetime.now(timezone.utc)
        final_readiness = success and all(checks.values())
        validations = tuple(self._validations_executed(checks))
        return FinalOperationalValidationResult(
            status=status,
            success=success,
            validation_id=validation_id,
            workflow_id=request.workflow_id,
            runtime_validation_valid=checks["runtime_validation"],
            workflow_validation_valid=checks["workflow_validation"],
            governance_validation_valid=checks["governance_validation"],
            audit_validation_valid=checks["audit_validation"],
            security_validation_valid=checks["security_validation"],
            knowledge_core_validation_valid=checks["knowledge_core_validation"],
            stability_validation_valid=checks["stability_validation"],
            authority_validation_valid=checks["authority_validation"],
            execution_validation_valid=checks["execution_validation"],
            final_readiness_valid=final_readiness,
            production_safe=final_readiness,
            continuation_allowed=final_readiness,
            risks_detected=bool(risks),
            blockers_detected=bool(blockers),
            validations_executed=validations,
            risks=risks,
            blockers=blockers,
            final_report=self._final_report(
                status,
                checks,
                risks,
                blockers,
            ),
            human_visibility_payload=self._visibility(
                request,
                checks,
                risks,
                blockers,
            ),
            validation_lifecycle=(
                self._lifecycle("full_system_check"),
                self._lifecycle("authority_check"),
                self._lifecycle("execution_check"),
                self._lifecycle("stability_check"),
                self._lifecycle("final_readiness_report"),
            ),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons),
            error=error,
            metadata=dict(request.metadata),
        )

    def _final_report(
        self,
        status: str,
        checks: dict[str, bool],
        risks: tuple[str, ...],
        blockers: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "FINAL STATUS": status,
            "RUNTIME STATUS": self._status_label(checks["runtime_validation"]),
            "WORKFLOW STATUS": self._status_label(checks["workflow_validation"]),
            "GOVERNANCE STATUS": self._status_label(
                checks["governance_validation"]
                and checks["authority_validation"]
            ),
            "AUDIT STATUS": self._status_label(checks["audit_validation"]),
            "SECURITY STATUS": self._status_label(checks["security_validation"]),
            "KNOWLEDGE CORE STATUS": self._status_label(
                checks["knowledge_core_validation"]
            ),
            "STABILITY STATUS": self._status_label(
                checks["stability_validation"]
            ),
            "RISKS": list(risks),
            "BLOCKERS": list(blockers),
            "FINAL DECISION": (
                "production_ready"
                if status == FINAL_VALIDATION_STATUS_READY
                else "blocked"
            ),
        }

    def _visibility(
        self,
        request: FinalOperationalValidationRequest,
        checks: dict[str, bool],
        risks: tuple[str, ...],
        blockers: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "runtime_status": dict(request.runtime_status),
            "workflow_status": dict(request.workflow_status),
            "governance_status": dict(request.governance_status),
            "audit_status": dict(request.audit_status),
            "security_status": dict(request.security_status),
            "knowledge_core_status": dict(request.knowledge_core_status),
            "stability_status": dict(request.stability_status),
            "validations": dict(checks),
            "risks": list(risks),
            "blockers": list(blockers),
        }

    def _error_result(
        self,
        validation_id: str,
        request: FinalOperationalValidationRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> FinalOperationalValidationResult:
        return self._result(
            status=FINAL_VALIDATION_STATUS_ERROR,
            success=False,
            validation_id=validation_id,
            request=request,
            context={},
            checks={
                "runtime_validation": False,
                "workflow_validation": False,
                "governance_validation": False,
                "audit_validation": False,
                "security_validation": False,
                "knowledge_core_validation": False,
                "stability_validation": False,
                "authority_validation": False,
                "execution_validation": False,
            },
            risks=tuple(request.risks),
            blockers=tuple(request.blockers),
            reasons=["final_operational_validation_error_contained"],
            error=error,
            started=started,
            started_at=started_at,
        )

    def _validations_executed(self, checks: dict[str, bool]) -> list[str]:
        return [name for name in checks]

    def _status_label(self, valid: bool) -> str:
        return "valid" if valid else "blocked"

    def _authority_safe(self, value: dict[str, Any]) -> bool:
        if not value:
            return False
        required = (
            "ceo_authority_valid",
            "cerebro_communication_valid",
            "sentinel_audit_authority_valid",
            "centinela_security_authority_valid",
        )
        return all(value.get(key) is True for key in required) and not bool(
            value.get("authority_override_detected")
        )

    def _stability_context_safe(self, context: dict[str, Any]) -> bool:
        required = (
            "stress_tests",
            "failure_recovery",
            "restart_persistence",
            "long_running_validation",
            "observability_base",
            "production_hardening",
        )
        return all(self._upstream_safe(context[key]) for key in required)

    def _status_safe(
        self,
        value: dict[str, Any],
        safe_statuses: set[str],
    ) -> bool:
        status = (
            value.get("status")
            or value.get("runtime_status")
            or value.get("workflow_status")
            or value.get("governance_status")
            or value.get("audit_status")
            or value.get("security_status")
            or value.get("knowledge_core_status")
            or value.get("stability_status")
            or value.get("execution_status")
            or value.get("state")
        )
        return self._normalize(status) in safe_statuses

    def _upstream_safe(self, value: dict[str, Any]) -> bool:
        if not value:
            return False
        return self._normalize(value.get("status")) in SAFE_UPSTREAM_STATUSES

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

    def _publish(self, result: FinalOperationalValidationResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_final_operational_validation_result",
        ):
            self.status.mark_final_operational_validation_result(
                result.to_dict()
            )

    def _log_result(self, result: FinalOperationalValidationResult) -> None:
        if result.status == FINAL_VALIDATION_STATUS_ERROR:
            logger.error(
                "final_operational_validation: error validation_id=%s error=%s",
                result.validation_id,
                result.error,
            )
            return
        if result.status == FINAL_VALIDATION_STATUS_BLOCKED:
            logger.warning(
                "final_operational_validation: blocked validation_id=%s "
                "reasons=%s",
                result.validation_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "final_operational_validation: ready validation_id=%s "
            "workflow_id=%s",
            result.validation_id,
            result.workflow_id,
        )
