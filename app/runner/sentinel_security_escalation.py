"""
SENTINEL security escalation hook for Hermes operational workflows.

This layer detects critical threats and prepares escalation to CENTINELA. It
does not resolve threats, unlock quarantine, replace security authority, or
modify runtime state.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.sentinel_audit_pipeline import SentinelAuditResult
from app.runner.sentinel_technical_validation import (
    SentinelTechnicalValidationResult,
)

logger = logging.getLogger(__name__)

ESCALATION_STATUS_CLEAR = "clear"
ESCALATION_STATUS_ESCALATED = "escalated"
ESCALATION_STATUS_BLOCKED = "blocked"
ESCALATION_STATUS_ERROR = "error"

SECURITY_CLEAR_STATUSES = {
    "clear",
    "none",
    "ok",
    "safe",
    "stable",
}

SECURITY_ESCALATION_STATUSES = {
    "critical",
    "escalate",
    "escalated",
    "quarantine",
    "security_risk",
    "unsafe",
}

QUARANTINE_STATUSES = {
    "active",
    "enabled",
    "quarantine",
    "quarantined",
}

CRITICAL_THREAT_HINTS = (
    "credential",
    "destructive",
    "filesystem danger",
    "leak",
    "malicious",
    "privilege escalation",
    "runtime compromise",
    "secret",
    "unauthorized execution",
)


@dataclass(frozen=True)
class SentinelSecurityEscalationRequest:
    escalation_id: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    execution_context: dict[str, Any] = field(default_factory=dict)
    threat_detection: Any | None = None
    security_observation: Any | None = None
    execution_analysis: dict[str, Any] = field(default_factory=dict)
    governance_impact: dict[str, Any] = field(default_factory=dict)
    technical_validation: (
        SentinelTechnicalValidationResult | dict[str, Any] | Any | None
    ) = None
    audit_pipeline: SentinelAuditResult | dict[str, Any] | Any | None = None
    threat_severity: str | None = None
    runtime_status: str | None = None
    quarantine_status: str | None = None
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    suspicious_modifications: tuple[str, ...] = field(default_factory=tuple)
    detected_threats: tuple[str, ...] = field(default_factory=tuple)
    auditor: str = "SENTINEL"
    target_authority: str = "CENTINELA"
    resolve_threat_requested: bool = False
    ignore_suspicious_behavior_requested: bool = False
    minimize_security_risk_requested: bool = False
    alter_governance_requested: bool = False
    replace_centinela_requested: bool = False
    unlock_quarantine_requested: bool = False
    falsify_severity_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SentinelSecurityEscalationResult:
    status: str
    success: bool
    escalation_id: str
    execution_id: str | None
    task_id: str | None
    auditor: str
    target_authority: str
    threat_detected: bool
    threat_severity: str | None
    security_observation: str | None
    escalation_required: bool
    centinela_escalation_prepared: bool
    continuation_blocked: bool
    quarantine_recommended: bool
    quarantine_status: str | None
    runtime_integrity_preserved: bool
    governance_consistency_preserved: bool
    security_integrity_preserved: bool
    operational_stability_preserved: bool
    execution_traceability_preserved: bool
    detected_threats: tuple[str, ...]
    suspicious_modifications: tuple[str, ...]
    blocking_conditions: tuple[str, ...]
    escalation_payload: dict[str, Any] = field(default_factory=dict)
    escalation_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "escalation_id": self.escalation_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "auditor": self.auditor,
            "target_authority": self.target_authority,
            "threat_detected": self.threat_detected,
            "threat_severity": self.threat_severity,
            "security_observation": self.security_observation,
            "escalation_required": self.escalation_required,
            "centinela_escalation_prepared": (
                self.centinela_escalation_prepared
            ),
            "continuation_blocked": self.continuation_blocked,
            "quarantine_recommended": self.quarantine_recommended,
            "quarantine_status": self.quarantine_status,
            "runtime_integrity_preserved": self.runtime_integrity_preserved,
            "governance_consistency_preserved": (
                self.governance_consistency_preserved
            ),
            "security_integrity_preserved": (
                self.security_integrity_preserved
            ),
            "operational_stability_preserved": (
                self.operational_stability_preserved
            ),
            "execution_traceability_preserved": (
                self.execution_traceability_preserved
            ),
            "detected_threats": list(self.detected_threats),
            "suspicious_modifications": list(self.suspicious_modifications),
            "blocking_conditions": list(self.blocking_conditions),
            "escalation_payload": dict(self.escalation_payload),
            "escalation_lifecycle": [
                dict(entry) for entry in self.escalation_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class SentinelSecurityEscalationHook:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def evaluate(
        self,
        request: SentinelSecurityEscalationRequest,
        escalation_permitted: bool = True,
    ) -> SentinelSecurityEscalationResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        escalation_id = request.escalation_id or str(uuid4())

        try:
            technical_validation = self._result_dict(request.technical_validation)
            audit_pipeline = self._result_dict(request.audit_pipeline)
            detected_threats = tuple(self._threats(request))
            suspicious_modifications = tuple(
                self._values(request.suspicious_modifications)
            )
            blocking_conditions = tuple(
                self._values(request.blocking_conditions)
            )
            severity = self._severity(
                request=request,
                detected_threats=detected_threats,
                technical_validation=technical_validation,
                audit_pipeline=audit_pipeline,
            )
            escalation_required = self._escalation_required(
                request=request,
                detected_threats=detected_threats,
                suspicious_modifications=suspicious_modifications,
                blocking_conditions=blocking_conditions,
                severity=severity,
                technical_validation=technical_validation,
                audit_pipeline=audit_pipeline,
            )
            reasons = self._validation_reasons(
                request=request,
                detected_threats=detected_threats,
                suspicious_modifications=suspicious_modifications,
                escalation_permitted=escalation_permitted,
            )
            blocked = bool(reasons)
            status = (
                ESCALATION_STATUS_BLOCKED
                if blocked
                else ESCALATION_STATUS_ESCALATED
                if escalation_required
                else ESCALATION_STATUS_CLEAR
            )
            result = self._result(
                status=status,
                success=not blocked,
                escalation_id=escalation_id,
                request=request,
                technical_validation=technical_validation,
                audit_pipeline=audit_pipeline,
                detected_threats=detected_threats,
                suspicious_modifications=suspicious_modifications,
                blocking_conditions=blocking_conditions,
                severity=severity,
                escalation_required=escalation_required and not blocked,
                reasons=reasons,
                error=";".join(reasons) if blocked else None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                escalation_id=escalation_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def escalate(
        self,
        request: SentinelSecurityEscalationRequest,
        escalation_permitted: bool = True,
    ) -> SentinelSecurityEscalationResult:
        return self.evaluate(
            request,
            escalation_permitted=escalation_permitted,
        )

    def _result(
        self,
        status: str,
        success: bool,
        escalation_id: str,
        request: SentinelSecurityEscalationRequest,
        technical_validation: dict[str, Any],
        audit_pipeline: dict[str, Any],
        detected_threats: tuple[str, ...],
        suspicious_modifications: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        severity: str | None,
        escalation_required: bool,
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> SentinelSecurityEscalationResult:
        finished_at = datetime.now(timezone.utc)
        quarantine_recommended = escalation_required or self._normalize(
            request.quarantine_status
        ) in QUARANTINE_STATUSES
        return SentinelSecurityEscalationResult(
            status=status,
            success=success,
            escalation_id=escalation_id,
            execution_id=request.execution_id,
            task_id=request.task_id,
            auditor=request.auditor,
            target_authority=request.target_authority,
            threat_detected=self._threat_detected(
                request,
                detected_threats,
                suspicious_modifications,
            ),
            threat_severity=severity,
            security_observation=self._normalize(request.security_observation),
            escalation_required=escalation_required,
            centinela_escalation_prepared=(
                escalation_required
                and request.target_authority.upper() == "CENTINELA"
                and success
            ),
            continuation_blocked=escalation_required or not success,
            quarantine_recommended=quarantine_recommended,
            quarantine_status=request.quarantine_status,
            runtime_integrity_preserved=not request.unlock_quarantine_requested,
            governance_consistency_preserved=not request.alter_governance_requested,
            security_integrity_preserved=not (
                request.replace_centinela_requested
                or request.resolve_threat_requested
            ),
            operational_stability_preserved=success,
            execution_traceability_preserved=bool(request.execution_context),
            detected_threats=detected_threats,
            suspicious_modifications=suspicious_modifications,
            blocking_conditions=blocking_conditions,
            escalation_payload=self._payload(
                escalation_id=escalation_id,
                request=request,
                technical_validation=technical_validation,
                audit_pipeline=audit_pipeline,
                detected_threats=detected_threats,
                suspicious_modifications=suspicious_modifications,
                blocking_conditions=blocking_conditions,
                severity=severity,
                reasons=reasons,
            ),
            escalation_lifecycle=(
                self._lifecycle("threat_detection"),
                self._lifecycle("security_validation"),
                self._lifecycle(status),
            ),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons or self._status_reasons(status)),
            error=error,
            metadata=dict(request.metadata),
        )

    def _validation_reasons(
        self,
        request: SentinelSecurityEscalationRequest,
        detected_threats: tuple[str, ...],
        suspicious_modifications: tuple[str, ...],
        escalation_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not escalation_permitted:
            reasons.append("sentinel_security_escalation_not_permitted")
        if request.auditor.upper() != "SENTINEL":
            reasons.append("invalid_sentinel_auditor")
        if request.target_authority.upper() != "CENTINELA":
            reasons.append("centinela_authority_required")
        if not request.execution_context:
            reasons.append("execution_context_required")
        if request.resolve_threat_requested:
            reasons.append("sentinel_self_resolution_blocked")
        if request.ignore_suspicious_behavior_requested and (
            detected_threats or suspicious_modifications
        ):
            reasons.append("suspicious_behavior_ignored_blocked")
        if request.minimize_security_risk_requested and detected_threats:
            reasons.append("security_risk_minimization_blocked")
        if request.alter_governance_requested:
            reasons.append("security_governance_alteration_blocked")
        if request.replace_centinela_requested:
            reasons.append("centinela_replacement_blocked")
        if request.unlock_quarantine_requested:
            reasons.append("quarantine_unlock_blocked")
        if request.falsify_severity_requested:
            reasons.append("security_severity_falsification_blocked")
        return self._unique(reasons)

    def _escalation_required(
        self,
        request: SentinelSecurityEscalationRequest,
        detected_threats: tuple[str, ...],
        suspicious_modifications: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        severity: str | None,
        technical_validation: dict[str, Any],
        audit_pipeline: dict[str, Any],
    ) -> bool:
        return bool(
            detected_threats
            or suspicious_modifications
            or blocking_conditions
            or severity in SECURITY_ESCALATION_STATUSES
            or self._normalize(request.runtime_status) in SECURITY_ESCALATION_STATUSES
            or self._normalize(request.quarantine_status) in QUARANTINE_STATUSES
            or technical_validation.get("security_escalation_recommended")
            or audit_pipeline.get("audit_decision") == "escalate"
        )

    def _severity(
        self,
        request: SentinelSecurityEscalationRequest,
        detected_threats: tuple[str, ...],
        technical_validation: dict[str, Any],
        audit_pipeline: dict[str, Any],
    ) -> str | None:
        explicit = self._normalize(request.threat_severity)
        if explicit and explicit not in SECURITY_CLEAR_STATUSES:
            return explicit
        observation = self._normalize(request.security_observation)
        if observation in SECURITY_ESCALATION_STATUSES:
            return observation
        if technical_validation.get("security_escalation_recommended"):
            return "critical"
        if audit_pipeline.get("audit_decision") == "escalate":
            return "critical"
        if self._threats_critical(detected_threats):
            return "critical"
        if detected_threats:
            return "elevated"
        return explicit or "clear"

    def _threats(self, request: SentinelSecurityEscalationRequest) -> list[str]:
        values = self._values(request.detected_threats)
        detection = self._normalize(request.threat_detection)
        observation = self._normalize(request.security_observation)
        if detection and detection not in SECURITY_CLEAR_STATUSES:
            values.append(detection)
        if observation and observation not in SECURITY_CLEAR_STATUSES:
            values.append(observation)
        return self._unique(values)

    def _threat_detected(
        self,
        request: SentinelSecurityEscalationRequest,
        detected_threats: tuple[str, ...],
        suspicious_modifications: tuple[str, ...],
    ) -> bool:
        return bool(
            detected_threats
            or suspicious_modifications
            or self._normalize(request.quarantine_status) in QUARANTINE_STATUSES
        )

    def _threats_critical(self, threats: tuple[str, ...]) -> bool:
        body = " ".join(threats).lower()
        return any(hint in body for hint in CRITICAL_THREAT_HINTS)

    def _payload(
        self,
        escalation_id: str,
        request: SentinelSecurityEscalationRequest,
        technical_validation: dict[str, Any],
        audit_pipeline: dict[str, Any],
        detected_threats: tuple[str, ...],
        suspicious_modifications: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        severity: str | None,
        reasons: list[str],
    ) -> dict[str, Any]:
        return {
            "escalation_id": escalation_id,
            "target_authority": request.target_authority,
            "execution_id": request.execution_id,
            "task_id": request.task_id,
            "execution_context": dict(request.execution_context),
            "threat_analysis": list(detected_threats),
            "suspicious_modifications": list(suspicious_modifications),
            "runtime_status": request.runtime_status,
            "governance_impact": dict(request.governance_impact),
            "security_severity": severity,
            "blocking_conditions": list(blocking_conditions),
            "technical_validation_id": technical_validation.get("validation_id"),
            "audit_id": audit_pipeline.get("audit_id"),
            "blocked_reasons": list(reasons),
        }

    def _status_reasons(self, status: str) -> list[str]:
        if status == ESCALATION_STATUS_ESCALATED:
            return ["centinela_security_escalation_prepared"]
        if status == ESCALATION_STATUS_CLEAR:
            return ["no_security_escalation_required"]
        return []

    def _result_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, (SentinelTechnicalValidationResult, SentinelAuditResult)):
            return value.to_dict()
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

    def _values(self, values: tuple[str, ...]) -> list[str]:
        return self._unique(
            [str(value).strip() for value in values if str(value).strip()]
        )

    def _error_result(
        self,
        escalation_id: str,
        request: SentinelSecurityEscalationRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> SentinelSecurityEscalationResult:
        finished_at = datetime.now(timezone.utc)
        return SentinelSecurityEscalationResult(
            status=ESCALATION_STATUS_ERROR,
            success=False,
            escalation_id=escalation_id,
            execution_id=request.execution_id,
            task_id=request.task_id,
            auditor=request.auditor,
            target_authority=request.target_authority,
            threat_detected=False,
            threat_severity=request.threat_severity,
            security_observation=self._normalize(request.security_observation),
            escalation_required=False,
            centinela_escalation_prepared=False,
            continuation_blocked=True,
            quarantine_recommended=False,
            quarantine_status=request.quarantine_status,
            runtime_integrity_preserved=False,
            governance_consistency_preserved=False,
            security_integrity_preserved=False,
            operational_stability_preserved=False,
            execution_traceability_preserved=bool(request.execution_context),
            detected_threats=tuple(request.detected_threats),
            suspicious_modifications=tuple(request.suspicious_modifications),
            blocking_conditions=tuple(request.blocking_conditions),
            escalation_payload={
                "escalation_id": escalation_id,
                "blocked_reasons": [
                    "sentinel_security_escalation_error_contained"
                ],
            },
            escalation_lifecycle=(self._lifecycle(ESCALATION_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("sentinel_security_escalation_error_contained",),
            error=error,
            metadata=dict(request.metadata),
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

    def _publish(self, result: SentinelSecurityEscalationResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_sentinel_security_escalation_result",
        ):
            self.status.mark_sentinel_security_escalation_result(
                result.to_dict()
            )

    def _log_result(self, result: SentinelSecurityEscalationResult) -> None:
        if result.status == ESCALATION_STATUS_ERROR:
            logger.error(
                "sentinel_security_escalation: error escalation_id=%s error=%s",
                result.escalation_id,
                result.error,
            )
            return
        if result.status == ESCALATION_STATUS_BLOCKED:
            logger.warning(
                "sentinel_security_escalation: blocked escalation_id=%s reasons=%s",
                result.escalation_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "sentinel_security_escalation: %s escalation_id=%s target=%s",
            result.status,
            result.escalation_id,
            result.target_authority,
        )
