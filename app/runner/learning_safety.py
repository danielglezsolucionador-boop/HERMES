"""
Learning safety guardrails for Hermes runtime.

This layer validates learned patterns, adaptations, and optimizations before
they can be applied. It preserves governance, blocks unsafe autonomy expansion,
and keeps critical security authority with CENTINELA.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

LEARNING_TYPE_GOVERNANCE = "governance"
LEARNING_TYPE_SECURITY = "security"
LEARNING_TYPE_ARCHITECTURE = "architecture"
LEARNING_TYPE_AUTONOMY = "autonomy"
LEARNING_TYPE_MEMORY = "memory"
LEARNING_TYPE_EXECUTION = "execution"
SUPPORTED_LEARNING_TYPES = {
    LEARNING_TYPE_GOVERNANCE,
    LEARNING_TYPE_SECURITY,
    LEARNING_TYPE_ARCHITECTURE,
    LEARNING_TYPE_AUTONOMY,
    LEARNING_TYPE_MEMORY,
    LEARNING_TYPE_EXECUTION,
}

DECISION_SAFE = "safe_learning"
DECISION_WARNING = "warning_learning"
DECISION_BLOCKED = "blocked_learning"
DECISION_CRITICAL = "critical_learning"
DECISION_ERROR = "error"

APPROVED_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "authorized_by_human",
    "governance_approved",
}
APPROVED_AUDIT_STATUSES = {"approved", "approved_with_warnings"}
VALIDATION_STATUSES = {"validated", "approved", "safe", "approved_with_warnings"}
SAFE_RUNTIME_STATES = {"active", "online", "ready", "stable"}
BLOCKING_SECURITY_STATUSES = {"critical", "threat", "blocked", "compromised"}


@dataclass(frozen=True)
class LearningSafetyRequest:
    learning_id: str | None = None
    learning_type: str = LEARNING_TYPE_EXECUTION
    risk_level: str | None = None
    governance_status: str | None = None
    security_status: str | None = None
    validation_status: str | None = None
    audit_status: str | None = None
    application_requested: bool = False
    learning_candidate: Any | None = None
    adaptation_candidate: Any | None = None
    optimization_candidate: Any | None = None
    workflow_improvement: Any | None = None
    execution_adjustment: Any | None = None
    memory_records: tuple[Any, ...] = field(default_factory=tuple)
    runtime_state: dict[str, Any] = field(default_factory=dict)
    sentinel_status: str | None = None
    centinela_status: str | None = None
    governance_modification: bool = False
    architecture_mutation: bool = False
    autonomy_expansion: bool = False
    blocking_rule_modification: bool = False
    authority_modification: bool = False
    corrupt_memory_reuse: bool = False
    unsafe_optimization: bool = False
    runtime_instability: bool = False
    security_risk: bool = False
    detected_risks: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LearningSafetyResult:
    status: str
    success: bool
    learning_id: str
    learning_type: str | None
    risk_level: str | None
    governance_status: str | None
    security_status: str | None
    validation_status: str | None
    audit_status: str | None
    application_status: str
    safety_decision: str
    governance_compliant: bool
    audit_consistent: bool
    runtime_stable: bool
    security_safe: bool
    architecture_integrity: bool
    autonomy_limited: bool
    memory_safe: bool
    execution_safe: bool
    human_authority_preserved: bool
    sentinel_escalation_required: bool
    centinela_escalation_required: bool
    traceability_preserved: bool
    learning_control: str
    learning_candidate: dict[str, Any] = field(default_factory=dict)
    adaptation_candidate: dict[str, Any] = field(default_factory=dict)
    optimization_candidate: dict[str, Any] = field(default_factory=dict)
    workflow_improvement: dict[str, Any] = field(default_factory=dict)
    execution_adjustment: dict[str, Any] = field(default_factory=dict)
    memory_records: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    detected_risks: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    safety_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "learning_id": self.learning_id,
            "learning_type": self.learning_type,
            "risk_level": self.risk_level,
            "governance_status": self.governance_status,
            "security_status": self.security_status,
            "validation_status": self.validation_status,
            "audit_status": self.audit_status,
            "application_status": self.application_status,
            "safety_decision": self.safety_decision,
            "governance_compliant": self.governance_compliant,
            "audit_consistent": self.audit_consistent,
            "runtime_stable": self.runtime_stable,
            "security_safe": self.security_safe,
            "architecture_integrity": self.architecture_integrity,
            "autonomy_limited": self.autonomy_limited,
            "memory_safe": self.memory_safe,
            "execution_safe": self.execution_safe,
            "human_authority_preserved": self.human_authority_preserved,
            "sentinel_escalation_required": self.sentinel_escalation_required,
            "centinela_escalation_required": self.centinela_escalation_required,
            "traceability_preserved": self.traceability_preserved,
            "learning_control": self.learning_control,
            "learning_candidate": dict(self.learning_candidate),
            "adaptation_candidate": dict(self.adaptation_candidate),
            "optimization_candidate": dict(self.optimization_candidate),
            "workflow_improvement": dict(self.workflow_improvement),
            "execution_adjustment": dict(self.execution_adjustment),
            "memory_records": [dict(record) for record in self.memory_records],
            "detected_risks": list(self.detected_risks),
            "warnings": list(self.warnings),
            "safety_lifecycle": [
                dict(entry) for entry in self.safety_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class LearningSafety:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def validate(
        self,
        request: LearningSafetyRequest,
        safety_permitted: bool = True,
    ) -> LearningSafetyResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        learning_id = request.learning_id or str(uuid4())

        try:
            learning_type = self._normalize(request.learning_type)
            checks = self._checks(request)
            decision, reasons = self._decision(
                request=request,
                learning_type=learning_type,
                checks=checks,
                safety_permitted=safety_permitted,
            )
            result = self._result(
                status=decision,
                success=decision in {DECISION_SAFE, DECISION_WARNING},
                learning_id=learning_id,
                request=request,
                learning_type=learning_type,
                checks=checks,
                reasons=reasons,
                error=None if decision != DECISION_ERROR else ";".join(reasons),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                learning_id=learning_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def check(
        self,
        request: LearningSafetyRequest,
        safety_permitted: bool = True,
    ) -> LearningSafetyResult:
        return self.validate(request, safety_permitted=safety_permitted)

    def _result(
        self,
        status: str,
        success: bool,
        learning_id: str,
        request: LearningSafetyRequest,
        learning_type: str | None,
        checks: dict[str, bool],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> LearningSafetyResult:
        finished_at = datetime.now(timezone.utc)
        application_status = self._application_status(status)
        return LearningSafetyResult(
            status=status,
            success=success,
            learning_id=learning_id,
            learning_type=learning_type,
            risk_level=self._risk_level(request),
            governance_status=self._normalize(request.governance_status),
            security_status=self._normalize(request.security_status),
            validation_status=self._normalize(request.validation_status),
            audit_status=self._normalize(request.audit_status),
            application_status=application_status,
            safety_decision=status,
            governance_compliant=checks["governance_compliant"],
            audit_consistent=checks["audit_consistent"],
            runtime_stable=checks["runtime_stable"],
            security_safe=checks["security_safe"],
            architecture_integrity=checks["architecture_integrity"],
            autonomy_limited=checks["autonomy_limited"],
            memory_safe=checks["memory_safe"],
            execution_safe=checks["execution_safe"],
            human_authority_preserved=checks["human_authority_preserved"],
            sentinel_escalation_required=status in {DECISION_BLOCKED, DECISION_CRITICAL},
            centinela_escalation_required=status == DECISION_CRITICAL,
            traceability_preserved=True,
            learning_control=self._learning_control(status),
            learning_candidate=self._as_dict(request.learning_candidate),
            adaptation_candidate=self._as_dict(request.adaptation_candidate),
            optimization_candidate=self._as_dict(request.optimization_candidate),
            workflow_improvement=self._as_dict(request.workflow_improvement),
            execution_adjustment=self._as_dict(request.execution_adjustment),
            memory_records=tuple(
                self._as_dict(record) for record in request.memory_records
            ),
            detected_risks=tuple(request.detected_risks),
            warnings=tuple(request.warnings),
            safety_lifecycle=(
                self._lifecycle("learning_detection_completed"),
                self._lifecycle("safety_validation_completed"),
                self._lifecycle(status),
            ),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons),
            error=error,
            metadata=dict(request.metadata),
        )

    def _checks(self, request: LearningSafetyRequest) -> dict[str, bool]:
        return {
            "governance_compliant": self._governance_compliant(request),
            "audit_consistent": self._audit_consistent(request),
            "runtime_stable": self._runtime_stable(request),
            "security_safe": self._security_safe(request),
            "architecture_integrity": not request.architecture_mutation,
            "autonomy_limited": not request.autonomy_expansion,
            "memory_safe": not (
                request.corrupt_memory_reuse or self._corrupt_memory(request)
            ),
            "execution_safe": not request.unsafe_optimization,
            "human_authority_preserved": not (
                request.authority_modification
                or request.blocking_rule_modification
                or request.governance_modification
            ),
        }

    def _decision(
        self,
        request: LearningSafetyRequest,
        learning_type: str | None,
        checks: dict[str, bool],
        safety_permitted: bool,
    ) -> tuple[str, list[str]]:
        reasons: list[str] = []
        if not safety_permitted:
            reasons.append("learning_safety_not_permitted")
        if learning_type not in SUPPORTED_LEARNING_TYPES:
            reasons.append("unsupported_learning_type")
        reasons.extend(self._risk_reasons(request, checks))
        reasons = self._unique(reasons)

        if "security_escalation_required" in reasons:
            return DECISION_CRITICAL, reasons
        if any(
            reason in reasons
            for reason in (
                "governance_learning_blocked",
                "architecture_learning_blocked",
                "autonomy_learning_blocked",
                "authority_modification_blocked",
                "blocking_rule_modification_blocked",
                "corrupt_memory_reuse_blocked",
                "unsafe_execution_optimization_blocked",
                "unsupported_learning_type",
                "learning_safety_not_permitted",
            )
        ):
            return DECISION_BLOCKED, reasons
        if any(
            reason in reasons
            for reason in (
                "runtime_instability_warning",
                "audit_warning",
                "elevated_risk_warning",
            )
        ):
            return DECISION_WARNING, reasons
        return DECISION_SAFE, reasons

    def _risk_reasons(
        self,
        request: LearningSafetyRequest,
        checks: dict[str, bool],
    ) -> list[str]:
        reasons: list[str] = []
        if request.governance_modification or not checks["governance_compliant"]:
            reasons.append("governance_learning_blocked")
        if not checks["audit_consistent"]:
            reasons.append("audit_warning")
        if request.security_risk or not checks["security_safe"]:
            reasons.append("security_escalation_required")
        if request.architecture_mutation or not checks["architecture_integrity"]:
            reasons.append("architecture_learning_blocked")
        if request.autonomy_expansion or not checks["autonomy_limited"]:
            reasons.append("autonomy_learning_blocked")
        if request.authority_modification:
            reasons.append("authority_modification_blocked")
        if request.blocking_rule_modification:
            reasons.append("blocking_rule_modification_blocked")
        if not checks["memory_safe"]:
            reasons.append("corrupt_memory_reuse_blocked")
        if not checks["execution_safe"]:
            reasons.append("unsafe_execution_optimization_blocked")
        if request.runtime_instability or not checks["runtime_stable"]:
            reasons.append("runtime_instability_warning")
        if self._risk_level(request) in {"high", "elevated"}:
            reasons.append("elevated_risk_warning")
        return reasons

    def _governance_compliant(self, request: LearningSafetyRequest) -> bool:
        if request.governance_modification:
            return False
        if request.application_requested:
            return (
                self._normalize(request.governance_status)
                in APPROVED_GOVERNANCE_STATUSES
            )
        return True

    def _audit_consistent(self, request: LearningSafetyRequest) -> bool:
        status = self._normalize(request.audit_status)
        if status is None:
            return True
        return status in APPROVED_AUDIT_STATUSES

    def _runtime_stable(self, request: LearningSafetyRequest) -> bool:
        if request.runtime_instability:
            return False
        if not request.runtime_state:
            return not request.application_requested
        values = (
            request.runtime_state.get("state"),
            request.runtime_state.get("status"),
            request.runtime_state.get("loop_state"),
        )
        return any(self._normalize(value) in SAFE_RUNTIME_STATES for value in values)

    def _security_safe(self, request: LearningSafetyRequest) -> bool:
        if request.security_risk:
            return False
        status = self._normalize(request.security_status)
        centinela = self._normalize(request.centinela_status)
        if status in BLOCKING_SECURITY_STATUSES:
            return False
        if centinela in {"blocked", "critical", "escalated"}:
            return False
        return True

    def _corrupt_memory(self, request: LearningSafetyRequest) -> bool:
        for record in request.memory_records:
            data = self._as_dict(record)
            if data and not (
                data.get("memory_id")
                and data.get("memory_type")
                and data.get("timestamp")
            ):
                return True
        return False

    def _risk_level(self, request: LearningSafetyRequest) -> str | None:
        value = self._normalize(request.risk_level)
        if value:
            return value
        if request.security_risk:
            return "critical"
        if request.autonomy_expansion or request.architecture_mutation:
            return "high"
        if request.runtime_instability or request.unsafe_optimization:
            return "elevated"
        return "low"

    def _application_status(self, status: str) -> str:
        if status == DECISION_SAFE:
            return "allowed"
        if status == DECISION_WARNING:
            return "limited"
        if status == DECISION_CRITICAL:
            return "escalation_required"
        if status == DECISION_BLOCKED:
            return "blocked"
        return "error"

    def _learning_control(self, status: str) -> str:
        if status == DECISION_SAFE:
            return "learning_allowed"
        if status == DECISION_WARNING:
            return "learning_limited"
        if status == DECISION_CRITICAL:
            return "centinela_escalation_required"
        if status == DECISION_BLOCKED:
            return "learning_blocked"
        return "learning_error_contained"

    def _normalize(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower().replace("-", "_").replace(" ", "_")

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {"value": str(value)}
        return {"value": str(value)}

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

    def _error_result(
        self,
        learning_id: str,
        request: LearningSafetyRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> LearningSafetyResult:
        finished_at = datetime.now(timezone.utc)
        return LearningSafetyResult(
            status=DECISION_ERROR,
            success=False,
            learning_id=learning_id,
            learning_type=self._normalize(request.learning_type),
            risk_level="unknown",
            governance_status=self._normalize(request.governance_status),
            security_status=self._normalize(request.security_status),
            validation_status=self._normalize(request.validation_status),
            audit_status=self._normalize(request.audit_status),
            application_status="error",
            safety_decision=DECISION_ERROR,
            governance_compliant=False,
            audit_consistent=False,
            runtime_stable=False,
            security_safe=False,
            architecture_integrity=False,
            autonomy_limited=False,
            memory_safe=False,
            execution_safe=False,
            human_authority_preserved=False,
            sentinel_escalation_required=True,
            centinela_escalation_required=False,
            traceability_preserved=True,
            learning_control="learning_error_contained",
            safety_lifecycle=(self._lifecycle(DECISION_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("learning_safety_error_contained",),
            error=error,
            metadata=dict(request.metadata),
        )

    def _publish(self, result: LearningSafetyResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_learning_safety_result",
        ):
            self.status.mark_learning_safety_result(result.to_dict())

    def _log_result(self, result: LearningSafetyResult) -> None:
        if result.status == DECISION_ERROR:
            logger.error(
                "learning_safety: error learning_id=%s error=%s",
                result.learning_id,
                result.error,
            )
            return
        if result.status in {DECISION_BLOCKED, DECISION_CRITICAL}:
            logger.warning(
                "learning_safety: %s learning_id=%s reasons=%s",
                result.status,
                result.learning_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "learning_safety: %s learning_id=%s type=%s",
            result.status,
            result.learning_id,
            result.learning_type,
        )
