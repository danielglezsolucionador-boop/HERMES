"""
Production hardening validation for Hermes operations.

This layer evaluates reported production readiness and applies no runtime
mutation. It is a passive guardrail used to expose hardening status, risks,
blocking conditions, and governance consistency without changing runtime core.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

PRODUCTION_HARDENING_STATUS_HARDENED = "hardened"
PRODUCTION_HARDENING_STATUS_BLOCKED = "blocked"
PRODUCTION_HARDENING_STATUS_ERROR = "error"

SAFE_RUNTIME_STATUSES = {"active", "online", "ready", "stable", "resumed", "ok"}
SAFE_EXECUTION_STATUSES = {
    "active",
    "ready",
    "stable",
    "validated",
    "completed",
    "running",
}
SAFE_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "governance_approved",
    "stable",
}
SAFE_SECURITY_STATUSES = {
    "protected",
    "stable",
    "aligned",
    "ok",
    "ready",
}
SAFE_RESILIENCE_STATUSES = {
    "resilient",
    "stable",
    "ready",
    "validated",
    "ok",
    "recovered",
}


@dataclass(frozen=True)
class ProductionHardeningRequest:
    hardening_id: str | None = None
    workflow_id: str | None = None
    runtime_status: dict[str, Any] = field(default_factory=dict)
    execution_status: dict[str, Any] = field(default_factory=dict)
    governance_status: dict[str, Any] = field(default_factory=dict)
    workflow_status: dict[str, Any] = field(default_factory=dict)
    security_status: dict[str, Any] = field(default_factory=dict)
    resilience_status: dict[str, Any] = field(default_factory=dict)
    stress_tests: dict[str, Any] | Any | None = None
    failure_recovery: dict[str, Any] | Any | None = None
    restart_persistence: dict[str, Any] | Any | None = None
    long_running_validation: dict[str, Any] | Any | None = None
    observability_base: dict[str, Any] | Any | None = None
    runtime_risks: tuple[str, ...] = field(default_factory=tuple)
    operational_vulnerabilities: tuple[str, ...] = field(default_factory=tuple)
    workflow_instability: tuple[str, ...] = field(default_factory=tuple)
    governance_exposure: tuple[str, ...] = field(default_factory=tuple)
    security_weaknesses: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    ignore_critical_risks_requested: bool = False
    minimize_instability_conditions_requested: bool = False
    overwrite_security_protections_requested: bool = False
    alter_governance_runtime_requested: bool = False
    invalidate_blocking_systems_requested: bool = False
    continue_unsafe_execution_requested: bool = False
    hide_runtime_vulnerabilities_requested: bool = False
    falsify_resilience_status_requested: bool = False
    ignore_governance_conflicts_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProductionHardeningResult:
    status: str
    success: bool
    hardening_id: str
    workflow_id: str | None
    runtime_protection_valid: bool
    execution_safety_valid: bool
    governance_protection_valid: bool
    failure_resistance_valid: bool
    security_stability_valid: bool
    operational_resilience_valid: bool
    workflow_integrity_valid: bool
    hardening_consistent: bool
    continuation_allowed: bool
    risks_detected: bool
    runtime_protected: bool
    governance_consistency_preserved: bool
    workflow_traceability_preserved: bool
    protections_applied: tuple[str, ...] = field(default_factory=tuple)
    risks_mitigated: tuple[str, ...] = field(default_factory=tuple)
    risk_conditions: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    hardening_report: dict[str, Any] = field(default_factory=dict)
    human_visibility_payload: dict[str, Any] = field(default_factory=dict)
    hardening_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "hardening_id": self.hardening_id,
            "workflow_id": self.workflow_id,
            "runtime_protection_valid": self.runtime_protection_valid,
            "execution_safety_valid": self.execution_safety_valid,
            "governance_protection_valid": self.governance_protection_valid,
            "failure_resistance_valid": self.failure_resistance_valid,
            "security_stability_valid": self.security_stability_valid,
            "operational_resilience_valid": (
                self.operational_resilience_valid
            ),
            "workflow_integrity_valid": self.workflow_integrity_valid,
            "hardening_consistent": self.hardening_consistent,
            "continuation_allowed": self.continuation_allowed,
            "risks_detected": self.risks_detected,
            "runtime_protected": self.runtime_protected,
            "governance_consistency_preserved": (
                self.governance_consistency_preserved
            ),
            "workflow_traceability_preserved": (
                self.workflow_traceability_preserved
            ),
            "protections_applied": list(self.protections_applied),
            "risks_mitigated": list(self.risks_mitigated),
            "risk_conditions": list(self.risk_conditions),
            "blocking_conditions": list(self.blocking_conditions),
            "hardening_report": dict(self.hardening_report),
            "human_visibility_payload": dict(self.human_visibility_payload),
            "hardening_lifecycle": [
                dict(entry) for entry in self.hardening_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class ProductionHardening:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def harden(
        self,
        request: ProductionHardeningRequest,
    ) -> ProductionHardeningResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        hardening_id = request.hardening_id or str(uuid4())

        try:
            context = self._context(request)
            checks = self._checks(request, context)
            risk_conditions = tuple(
                self._risk_conditions(request, context, checks)
            )
            blocking_conditions = tuple(
                self._blocking_conditions(request, checks, risk_conditions)
            )
            reasons = self._reasons(
                request,
                checks,
                risk_conditions,
                blocking_conditions,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    PRODUCTION_HARDENING_STATUS_BLOCKED
                    if blocked
                    else PRODUCTION_HARDENING_STATUS_HARDENED
                ),
                success=not blocked,
                hardening_id=hardening_id,
                request=request,
                context=context,
                checks=checks,
                risk_conditions=risk_conditions,
                blocking_conditions=blocking_conditions,
                reasons=reasons or ["production_hardening_completed"],
                error=";".join(reasons) if blocked else None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                hardening_id=hardening_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def _context(self, request: ProductionHardeningRequest) -> dict[str, Any]:
        return {
            "stress_tests": self._as_dict(request.stress_tests),
            "failure_recovery": self._as_dict(request.failure_recovery),
            "restart_persistence": self._as_dict(request.restart_persistence),
            "long_running_validation": self._as_dict(
                request.long_running_validation
            ),
            "observability_base": self._as_dict(request.observability_base),
        }

    def _checks(
        self,
        request: ProductionHardeningRequest,
        context: dict[str, Any],
    ) -> dict[str, bool]:
        return {
            "runtime_protection": bool(
                request.runtime_status
                and self._status_safe(
                    request.runtime_status,
                    SAFE_RUNTIME_STATUSES,
                )
            ),
            "execution_safety": bool(
                request.execution_status
                and self._status_safe(
                    request.execution_status,
                    SAFE_EXECUTION_STATUSES,
                )
            ),
            "governance_protection": bool(
                request.governance_status
                and self._status_safe(
                    request.governance_status,
                    SAFE_GOVERNANCE_STATUSES,
                )
            ),
            "failure_resistance": bool(
                not request.runtime_risks
                and not request.workflow_instability
                and not self._any_upstream_blocked(context)
            ),
            "security_stability": bool(
                request.security_status
                and self._status_safe(
                    request.security_status,
                    SAFE_SECURITY_STATUSES,
                )
                and not request.security_weaknesses
            ),
            "operational_resilience": bool(
                request.resilience_status
                and self._status_safe(
                    request.resilience_status,
                    SAFE_RESILIENCE_STATUSES,
                )
                and not request.operational_vulnerabilities
                and not request.governance_exposure
                and not request.blocking_conditions
            ),
            "workflow_integrity": bool(
                request.workflow_id
                and request.workflow_status
                and self._workflow_status_safe(request.workflow_status)
            ),
        }

    def _risk_conditions(
        self,
        request: ProductionHardeningRequest,
        context: dict[str, Any],
        checks: dict[str, bool],
    ) -> list[str]:
        risks = [
            *[str(item) for item in request.runtime_risks],
            *[str(item) for item in request.operational_vulnerabilities],
            *[str(item) for item in request.workflow_instability],
            *[str(item) for item in request.governance_exposure],
            *[str(item) for item in request.security_weaknesses],
        ]
        for name, valid in checks.items():
            if not valid:
                risks.append(f"{name}_failed")
        for name, result in context.items():
            if self._upstream_blocked(result):
                risks.append(f"{name}_{result.get('status')}")
            for key in (
                "failure_conditions",
                "anomaly_conditions",
                "restart_conditions",
                "blocking_conditions",
                "risk_conditions",
            ):
                risks.extend(str(item) for item in result.get(key, []))
        return self._unique(risks)

    def _blocking_conditions(
        self,
        request: ProductionHardeningRequest,
        checks: dict[str, bool],
        risk_conditions: tuple[str, ...],
    ) -> list[str]:
        blocking = [str(item) for item in request.blocking_conditions]
        for name, valid in checks.items():
            if not valid:
                blocking.append(f"{name}_required")
        if risk_conditions:
            blocking.append("production_hardening_risks_active")
        return self._unique(blocking)

    def _reasons(
        self,
        request: ProductionHardeningRequest,
        checks: dict[str, bool],
        risk_conditions: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
    ) -> list[str]:
        reasons: list[str] = []
        for name, valid in checks.items():
            if not valid:
                reasons.append(f"{name}_required")
        if risk_conditions:
            reasons.append("production_risks_detected")
        if blocking_conditions:
            reasons.append("production_blocking_conditions_active")
        if request.ignore_critical_risks_requested:
            reasons.append("critical_risk_ignore_blocked")
        if request.minimize_instability_conditions_requested:
            reasons.append("instability_condition_minimization_blocked")
        if request.overwrite_security_protections_requested:
            reasons.append("security_protection_overwrite_blocked")
        if request.alter_governance_runtime_requested:
            reasons.append("governance_runtime_alteration_blocked")
        if request.invalidate_blocking_systems_requested:
            reasons.append("blocking_system_invalidation_blocked")
        if request.continue_unsafe_execution_requested:
            reasons.append("unsafe_execution_continuation_blocked")
        if request.hide_runtime_vulnerabilities_requested:
            reasons.append("runtime_vulnerability_concealment_blocked")
        if request.falsify_resilience_status_requested:
            reasons.append("resilience_status_falsification_blocked")
        if request.ignore_governance_conflicts_requested:
            reasons.append("governance_conflict_ignore_blocked")
        return self._unique(reasons)

    def _result(
        self,
        status: str,
        success: bool,
        hardening_id: str,
        request: ProductionHardeningRequest,
        context: dict[str, Any],
        checks: dict[str, bool],
        risk_conditions: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> ProductionHardeningResult:
        finished_at = datetime.now(timezone.utc)
        hardening_consistent = success and all(checks.values())
        protections = tuple(self._protections_applied(checks))
        return ProductionHardeningResult(
            status=status,
            success=success,
            hardening_id=hardening_id,
            workflow_id=request.workflow_id,
            runtime_protection_valid=checks["runtime_protection"],
            execution_safety_valid=checks["execution_safety"],
            governance_protection_valid=checks["governance_protection"],
            failure_resistance_valid=checks["failure_resistance"],
            security_stability_valid=checks["security_stability"],
            operational_resilience_valid=checks["operational_resilience"],
            workflow_integrity_valid=checks["workflow_integrity"],
            hardening_consistent=hardening_consistent,
            continuation_allowed=hardening_consistent,
            risks_detected=bool(risk_conditions),
            runtime_protected=hardening_consistent
            and checks["runtime_protection"],
            governance_consistency_preserved=hardening_consistent
            and checks["governance_protection"],
            workflow_traceability_preserved=hardening_consistent
            and checks["workflow_integrity"],
            protections_applied=protections,
            risks_mitigated=protections if not risk_conditions else tuple(),
            risk_conditions=risk_conditions,
            blocking_conditions=blocking_conditions,
            hardening_report=self._report(
                checks,
                protections,
                risk_conditions,
                blocking_conditions,
            ),
            human_visibility_payload=self._visibility(
                request,
                checks,
                risk_conditions,
                blocking_conditions,
            ),
            hardening_lifecycle=(
                self._lifecycle("runtime_analysis"),
                self._lifecycle("hardening_validation"),
                self._lifecycle("hardening_application"),
                self._lifecycle("resilience_validation"),
                self._lifecycle("hardening_reporting"),
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
        protections: tuple[str, ...],
        risk_conditions: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "checks": dict(checks),
            "protections_applied": list(protections),
            "risks_detected": bool(risk_conditions),
            "risk_conditions": list(risk_conditions),
            "blocking_conditions": list(blocking_conditions),
            "hardening_status": (
                "applied"
                if all(checks.values()) and not blocking_conditions
                else "blocked"
            ),
        }

    def _visibility(
        self,
        request: ProductionHardeningRequest,
        checks: dict[str, bool],
        risk_conditions: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "protections_applied": self._protections_applied(checks),
            "runtime_stability": checks["runtime_protection"],
            "risks_mitigated": not risk_conditions,
            "blocking_conditions": list(blocking_conditions),
            "governance_consistency": checks["governance_protection"],
            "operational_resilience": checks["operational_resilience"],
            "workflow_id": request.workflow_id,
        }

    def _error_result(
        self,
        hardening_id: str,
        request: ProductionHardeningRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> ProductionHardeningResult:
        return self._result(
            status=PRODUCTION_HARDENING_STATUS_ERROR,
            success=False,
            hardening_id=hardening_id,
            request=request,
            context={},
            checks={
                "runtime_protection": False,
                "execution_safety": False,
                "governance_protection": False,
                "failure_resistance": False,
                "security_stability": False,
                "operational_resilience": False,
                "workflow_integrity": False,
            },
            risk_conditions=tuple(request.runtime_risks),
            blocking_conditions=tuple(request.blocking_conditions),
            reasons=["production_hardening_error_contained"],
            error=error,
            started=started,
            started_at=started_at,
        )

    def _protections_applied(self, checks: dict[str, bool]) -> list[str]:
        mapping = {
            "runtime_protection": "runtime_protection",
            "execution_safety": "execution_safeguards",
            "governance_protection": "governance_preservation",
            "failure_resistance": "failure_resistance",
            "security_stability": "security_stability",
            "operational_resilience": "operational_resilience",
            "workflow_integrity": "workflow_integrity",
        }
        return [
            protection
            for check, protection in mapping.items()
            if checks.get(check)
        ]

    def _workflow_status_safe(self, value: dict[str, Any]) -> bool:
        status = (
            value.get("status")
            or value.get("workflow_status")
            or value.get("continuation_status")
        )
        traceability = value.get("workflow_traceability_preserved", True)
        return (
            self._normalize(status)
            in SAFE_EXECUTION_STATUSES | SAFE_RESILIENCE_STATUSES
            and traceability is not False
        )

    def _status_safe(
        self,
        value: dict[str, Any],
        safe_statuses: set[str],
    ) -> bool:
        status = (
            value.get("status")
            or value.get("runner_status")
            or value.get("runtime_status")
            or value.get("execution_status")
            or value.get("governance_status")
            or value.get("security_status")
            or value.get("resilience_status")
            or value.get("state")
        )
        return self._normalize(status) in safe_statuses

    def _any_upstream_blocked(self, context: dict[str, Any]) -> bool:
        return any(self._upstream_blocked(value) for value in context.values())

    def _upstream_blocked(self, value: dict[str, Any]) -> bool:
        if not value:
            return False
        return self._normalize(value.get("status")) in {"blocked", "error"}

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

    def _publish(self, result: ProductionHardeningResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_production_hardening_result",
        ):
            self.status.mark_production_hardening_result(result.to_dict())

    def _log_result(self, result: ProductionHardeningResult) -> None:
        if result.status == PRODUCTION_HARDENING_STATUS_ERROR:
            logger.error(
                "production_hardening: error hardening_id=%s error=%s",
                result.hardening_id,
                result.error,
            )
            return
        if result.status == PRODUCTION_HARDENING_STATUS_BLOCKED:
            logger.warning(
                "production_hardening: blocked hardening_id=%s reasons=%s",
                result.hardening_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "production_hardening: hardened hardening_id=%s workflow_id=%s",
            result.hardening_id,
            result.workflow_id,
        )
