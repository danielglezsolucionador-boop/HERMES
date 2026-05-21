"""
SENTINEL official audit reporting for Hermes operational workflows.

This layer structures technical audit evidence into an official report. It is
read-only: it does not approve unsafe execution, alter governance, hide risks,
or modify runtime behavior.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.sentinel_audit_pipeline import SentinelAuditResult
from app.runner.sentinel_security_escalation import (
    SentinelSecurityEscalationResult,
)
from app.runner.sentinel_technical_validation import (
    SentinelTechnicalValidationResult,
)

logger = logging.getLogger(__name__)

REPORT_STATUS_GENERATED = "generated"
REPORT_STATUS_BLOCKED = "blocked"
REPORT_STATUS_ERROR = "error"

CLEAR_VALUES = {
    "clear",
    "none",
    "no_blockers",
    "no_blocking_conditions",
    "no_known_risks",
    "no_known_risks_declared",
}

UNSAFE_VALUES = {
    "blocked",
    "broken",
    "corrupt",
    "critical",
    "error",
    "failed",
    "invalid",
    "quarantine",
    "rejected",
    "security_risk",
    "unsafe",
}

REQUIRED_REPORT_SECTIONS = (
    "AUDIT STATUS",
    "EXECUTION CONTEXT",
    "VALIDATIONS",
    "RUNTIME STATUS",
    "RISKS DETECTED",
    "BLOCKING CONDITIONS",
    "GOVERNANCE STATUS",
    "SECURITY STATUS",
    "FINAL DECISION",
    "CONTINUIDAD",
)


@dataclass(frozen=True)
class SentinelAuditReportingRequest:
    report_id: str | None = None
    audit_id: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    audit_status: str | None = None
    execution_context: dict[str, Any] = field(default_factory=dict)
    validations_executed: tuple[str, ...] = field(default_factory=tuple)
    runtime_status: str | None = None
    risks_detected: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    governance_status: str | None = None
    security_status: str | None = None
    final_decision: str | None = None
    continuity_status: str | None = None
    audit_pipeline: SentinelAuditResult | dict[str, Any] | Any | None = None
    technical_validation: (
        SentinelTechnicalValidationResult | dict[str, Any] | Any | None
    ) = None
    security_escalation: (
        SentinelSecurityEscalationResult | dict[str, Any] | Any | None
    ) = None
    auditor: str = "SENTINEL"
    hide_inconsistencies_requested: bool = False
    minimize_runtime_risks_requested: bool = False
    falsify_audit_status_requested: bool = False
    approve_unsafe_execution_requested: bool = False
    alter_governance_reporting_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SentinelAuditReportingResult:
    status: str
    success: bool
    report_id: str
    audit_id: str | None
    execution_id: str | None
    task_id: str | None
    auditor: str
    audit_status: str | None
    execution_context: dict[str, Any]
    validations_executed: tuple[str, ...]
    runtime_status: str | None
    risks_detected: tuple[str, ...]
    blocking_conditions: tuple[str, ...]
    governance_status: str | None
    security_status: str | None
    final_decision: str | None
    continuity_status: str | None
    audit_transparency_preserved: bool
    runtime_visibility_preserved: bool
    execution_integrity_reported: bool
    technical_traceability_preserved: bool
    governance_consistency_preserved: bool
    risks_reported: bool
    blocking_conditions_reported: bool
    report_complete: bool
    report_text: str
    report_payload: dict[str, Any] = field(default_factory=dict)
    report_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "report_id": self.report_id,
            "audit_id": self.audit_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "auditor": self.auditor,
            "audit_status": self.audit_status,
            "execution_context": dict(self.execution_context),
            "validations_executed": list(self.validations_executed),
            "runtime_status": self.runtime_status,
            "risks_detected": list(self.risks_detected),
            "blocking_conditions": list(self.blocking_conditions),
            "governance_status": self.governance_status,
            "security_status": self.security_status,
            "final_decision": self.final_decision,
            "continuity_status": self.continuity_status,
            "audit_transparency_preserved": (
                self.audit_transparency_preserved
            ),
            "runtime_visibility_preserved": self.runtime_visibility_preserved,
            "execution_integrity_reported": self.execution_integrity_reported,
            "technical_traceability_preserved": (
                self.technical_traceability_preserved
            ),
            "governance_consistency_preserved": (
                self.governance_consistency_preserved
            ),
            "risks_reported": self.risks_reported,
            "blocking_conditions_reported": (
                self.blocking_conditions_reported
            ),
            "report_complete": self.report_complete,
            "report_text": self.report_text,
            "report_payload": dict(self.report_payload),
            "report_lifecycle": [
                dict(entry) for entry in self.report_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class SentinelAuditReporting:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def generate(
        self,
        request: SentinelAuditReportingRequest,
        reporting_permitted: bool = True,
    ) -> SentinelAuditReportingResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        report_id = request.report_id or str(uuid4())

        try:
            audit_pipeline = self._result_dict(request.audit_pipeline)
            technical_validation = self._result_dict(
                request.technical_validation
            )
            security_escalation = self._result_dict(
                request.security_escalation
            )
            report_data = self._report_data(
                request=request,
                audit_pipeline=audit_pipeline,
                technical_validation=technical_validation,
                security_escalation=security_escalation,
            )
            reasons = self._validation_reasons(
                request=request,
                report_data=report_data,
                reporting_permitted=reporting_permitted,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    REPORT_STATUS_BLOCKED
                    if blocked
                    else REPORT_STATUS_GENERATED
                ),
                success=not blocked,
                report_id=report_id,
                request=request,
                report_data=report_data,
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
                report_id=report_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def report(
        self,
        request: SentinelAuditReportingRequest,
        reporting_permitted: bool = True,
    ) -> SentinelAuditReportingResult:
        return self.generate(
            request,
            reporting_permitted=reporting_permitted,
        )

    def _result(
        self,
        status: str,
        success: bool,
        report_id: str,
        request: SentinelAuditReportingRequest,
        report_data: dict[str, Any],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> SentinelAuditReportingResult:
        finished_at = datetime.now(timezone.utc)
        report_text = self._report_text(report_data)
        report_complete = self._report_complete(report_data, report_text)
        risks = tuple(report_data["risks_detected"])
        blockers = tuple(report_data["blocking_conditions"])
        return SentinelAuditReportingResult(
            status=status,
            success=success,
            report_id=report_id,
            audit_id=report_data["audit_id"],
            execution_id=report_data["execution_id"],
            task_id=report_data["task_id"],
            auditor=request.auditor,
            audit_status=report_data["audit_status"],
            execution_context=dict(report_data["execution_context"]),
            validations_executed=tuple(report_data["validations_executed"]),
            runtime_status=report_data["runtime_status"],
            risks_detected=risks,
            blocking_conditions=blockers,
            governance_status=report_data["governance_status"],
            security_status=report_data["security_status"],
            final_decision=report_data["final_decision"],
            continuity_status=report_data["continuity_status"],
            audit_transparency_preserved=not (
                request.hide_inconsistencies_requested
                or request.falsify_audit_status_requested
            ),
            runtime_visibility_preserved=bool(report_data["runtime_status"]),
            execution_integrity_reported=bool(
                report_data["validations_executed"]
            ),
            technical_traceability_preserved=bool(
                report_data["execution_context"]
            ),
            governance_consistency_preserved=not (
                request.alter_governance_reporting_requested
            ),
            risks_reported=bool(risks),
            blocking_conditions_reported=bool(blockers),
            report_complete=report_complete and success,
            report_text=report_text,
            report_payload=self._payload(report_id, report_data, reasons),
            report_lifecycle=(
                self._lifecycle("audit_evidence_collection"),
                self._lifecycle("report_structuring"),
                self._lifecycle(status),
            ),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons or ["sentinel_audit_report_generated"]),
            error=error,
            metadata=dict(request.metadata),
        )

    def _validation_reasons(
        self,
        request: SentinelAuditReportingRequest,
        report_data: dict[str, Any],
        reporting_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not reporting_permitted:
            reasons.append("sentinel_audit_reporting_not_permitted")
        if request.auditor.upper() != "SENTINEL":
            reasons.append("invalid_sentinel_auditor")
        if not report_data["audit_status"]:
            reasons.append("audit_status_required")
        if not report_data["execution_context"]:
            reasons.append("execution_context_required")
        if not report_data["validations_executed"]:
            reasons.append("validations_executed_required")
        if not report_data["runtime_status"]:
            reasons.append("runtime_status_required")
        if not report_data["governance_status"]:
            reasons.append("governance_status_required")
        if not report_data["security_status"]:
            reasons.append("security_status_required")
        if not report_data["final_decision"]:
            reasons.append("final_decision_required")
        if not report_data["continuity_status"]:
            reasons.append("continuity_status_required")
        if request.hide_inconsistencies_requested:
            reasons.append("technical_inconsistency_concealment_blocked")
        if request.minimize_runtime_risks_requested and self._active(
            report_data["risks_detected"]
        ):
            reasons.append("runtime_risk_minimization_blocked")
        if request.falsify_audit_status_requested:
            reasons.append("audit_status_falsification_blocked")
        if request.approve_unsafe_execution_requested:
            reasons.append("unsafe_execution_approval_blocked")
        if request.alter_governance_reporting_requested:
            reasons.append("governance_reporting_alteration_blocked")
        if (
            self._unsafe(report_data["runtime_status"])
            and self._normalize(report_data["final_decision"]) == "approve"
        ):
            reasons.append("unsafe_runtime_approval_report_blocked")
        return self._unique(reasons)

    def _report_data(
        self,
        request: SentinelAuditReportingRequest,
        audit_pipeline: dict[str, Any],
        technical_validation: dict[str, Any],
        security_escalation: dict[str, Any],
    ) -> dict[str, Any]:
        technical_payload = dict(
            technical_validation.get("report_payload") or {}
        )
        audit_payload = dict(audit_pipeline.get("report_payload") or {})
        return {
            "audit_id": (
                request.audit_id
                or audit_pipeline.get("audit_id")
                or technical_payload.get("audit_id")
            ),
            "execution_id": (
                request.execution_id
                or audit_pipeline.get("execution_id")
                or technical_validation.get("execution_id")
                or security_escalation.get("execution_id")
            ),
            "task_id": (
                request.task_id
                or audit_pipeline.get("task_id")
                or technical_validation.get("task_id")
                or security_escalation.get("task_id")
            ),
            "audit_status": (
                request.audit_status
                or audit_pipeline.get("status")
                or technical_validation.get("status")
            ),
            "execution_context": (
                dict(request.execution_context)
                or dict(audit_pipeline.get("execution_context") or {})
            ),
            "validations_executed": self._unique(
                [
                    *self._values(request.validations_executed),
                    *self._values(
                        tuple(
                            technical_validation.get("validation_commands")
                            or ()
                        )
                    ),
                ]
            ),
            "runtime_status": (
                request.runtime_status
                or technical_payload.get("runtime_status")
                or audit_payload.get("runtime_status")
            ),
            "risks_detected": self._unique(
                [
                    *self._values(request.risks_detected),
                    *self._values(tuple(audit_pipeline.get("risks_detected") or ())),
                    *self._values(
                        tuple(technical_validation.get("risks_detected") or ())
                    ),
                ]
                or ["no_known_risks"]
            ),
            "blocking_conditions": self._unique(
                [
                    *self._values(request.blocking_conditions),
                    *self._values(
                        tuple(audit_pipeline.get("blocking_conditions") or ())
                    ),
                    *self._values(
                        tuple(
                            technical_validation.get("blocking_conditions")
                            or ()
                        )
                    ),
                ]
                or ["none"]
            ),
            "governance_status": (
                request.governance_status
                or technical_payload.get("governance_status")
                or self._governance_status(audit_pipeline, technical_validation)
            ),
            "security_status": (
                request.security_status
                or security_escalation.get("status")
                or self._security_status(audit_pipeline, technical_validation)
            ),
            "final_decision": (
                request.final_decision
                or audit_pipeline.get("audit_decision")
                or technical_validation.get("audit_decision_recommendation")
            ),
            "continuity_status": (
                request.continuity_status
                or self._continuity_status(audit_pipeline, technical_validation)
            ),
        }

    def _payload(
        self,
        report_id: str,
        report_data: dict[str, Any],
        reasons: list[str],
    ) -> dict[str, Any]:
        return {
            "report_id": report_id,
            "required_sections": list(REQUIRED_REPORT_SECTIONS),
            "audit_id": report_data["audit_id"],
            "execution_id": report_data["execution_id"],
            "task_id": report_data["task_id"],
            "audit_status": report_data["audit_status"],
            "runtime_status": report_data["runtime_status"],
            "governance_status": report_data["governance_status"],
            "security_status": report_data["security_status"],
            "final_decision": report_data["final_decision"],
            "continuity_status": report_data["continuity_status"],
            "blocked_reasons": list(reasons),
        }

    def _report_text(self, report_data: dict[str, Any]) -> str:
        return "\n".join(
            [
                f"AUDIT STATUS: {self._format(report_data['audit_status'])}",
                "EXECUTION CONTEXT: "
                f"{self._format(report_data['execution_context'])}",
                "VALIDATIONS: "
                f"{self._format(report_data['validations_executed'])}",
                "RUNTIME STATUS: "
                f"{self._format(report_data['runtime_status'])}",
                "RISKS DETECTED: "
                f"{self._format(report_data['risks_detected'])}",
                "BLOCKING CONDITIONS: "
                f"{self._format(report_data['blocking_conditions'])}",
                "GOVERNANCE STATUS: "
                f"{self._format(report_data['governance_status'])}",
                "SECURITY STATUS: "
                f"{self._format(report_data['security_status'])}",
                "FINAL DECISION: "
                f"{self._format(report_data['final_decision'])}",
                "CONTINUIDAD: "
                f"{self._format(report_data['continuity_status'])}",
            ]
        )

    def _report_complete(
        self,
        report_data: dict[str, Any],
        report_text: str,
    ) -> bool:
        sections_present = all(
            f"{section}:" in report_text for section in REQUIRED_REPORT_SECTIONS
        )
        fields_present = all(
            bool(report_data[key])
            for key in (
                "audit_status",
                "execution_context",
                "validations_executed",
                "runtime_status",
                "risks_detected",
                "blocking_conditions",
                "governance_status",
                "security_status",
                "final_decision",
                "continuity_status",
            )
        )
        return sections_present and fields_present

    def _governance_status(
        self,
        audit_pipeline: dict[str, Any],
        technical_validation: dict[str, Any],
    ) -> str | None:
        if audit_pipeline.get("governance_valid") is True:
            return "approved"
        if audit_pipeline.get("governance_valid") is False:
            return "blocked"
        if technical_validation.get("governance_compliant") is True:
            return "approved"
        if technical_validation.get("governance_compliant") is False:
            return "blocked"
        return None

    def _security_status(
        self,
        audit_pipeline: dict[str, Any],
        technical_validation: dict[str, Any],
    ) -> str | None:
        if audit_pipeline.get("security_escalation_required"):
            return "escalated"
        if technical_validation.get("security_escalation_recommended"):
            return "escalated"
        if audit_pipeline.get("security_observation_clear") is True:
            return "clear"
        if technical_validation.get("security_observation_clear") is True:
            return "clear"
        if audit_pipeline.get("security_observation_clear") is False:
            return "blocked"
        if technical_validation.get("security_observation_clear") is False:
            return "blocked"
        return None

    def _continuity_status(
        self,
        audit_pipeline: dict[str, Any],
        technical_validation: dict[str, Any],
    ) -> str | None:
        if audit_pipeline.get("continuation_authorized") is True:
            return "authorized"
        if audit_pipeline.get("continuation_authorized") is False:
            return "blocked"
        if technical_validation.get("workflow_safe") is True:
            return "authorized"
        if technical_validation.get("workflow_safe") is False:
            return "blocked"
        return None

    def _result_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(
            value,
            (
                SentinelAuditResult,
                SentinelSecurityEscalationResult,
                SentinelTechnicalValidationResult,
            ),
        ):
            return value.to_dict()
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

    def _values(self, values: tuple[Any, ...]) -> list[str]:
        return self._unique(
            [str(value).strip() for value in values if str(value).strip()]
        )

    def _format(self, value: Any) -> str:
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, sort_keys=True, ensure_ascii=True)
        return str(value)

    def _active(self, values: list[str]) -> bool:
        return any((self._normalize(value) or "") not in CLEAR_VALUES for value in values)

    def _unsafe(self, value: Any) -> bool:
        return (self._normalize(value) or "") in UNSAFE_VALUES

    def _error_result(
        self,
        report_id: str,
        request: SentinelAuditReportingRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> SentinelAuditReportingResult:
        finished_at = datetime.now(timezone.utc)
        return SentinelAuditReportingResult(
            status=REPORT_STATUS_ERROR,
            success=False,
            report_id=report_id,
            audit_id=request.audit_id,
            execution_id=request.execution_id,
            task_id=request.task_id,
            auditor=request.auditor,
            audit_status=request.audit_status,
            execution_context=dict(request.execution_context),
            validations_executed=tuple(request.validations_executed),
            runtime_status=request.runtime_status,
            risks_detected=tuple(request.risks_detected),
            blocking_conditions=tuple(request.blocking_conditions),
            governance_status=request.governance_status,
            security_status=request.security_status,
            final_decision=request.final_decision,
            continuity_status=request.continuity_status,
            audit_transparency_preserved=False,
            runtime_visibility_preserved=False,
            execution_integrity_reported=False,
            technical_traceability_preserved=bool(request.execution_context),
            governance_consistency_preserved=False,
            risks_reported=bool(request.risks_detected),
            blocking_conditions_reported=bool(request.blocking_conditions),
            report_complete=False,
            report_text="",
            report_payload={
                "report_id": report_id,
                "blocked_reasons": [
                    "sentinel_audit_reporting_error_contained"
                ],
            },
            report_lifecycle=(self._lifecycle(REPORT_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("sentinel_audit_reporting_error_contained",),
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

    def _publish(self, result: SentinelAuditReportingResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_sentinel_audit_reporting_result",
        ):
            self.status.mark_sentinel_audit_reporting_result(result.to_dict())

    def _log_result(self, result: SentinelAuditReportingResult) -> None:
        if result.status == REPORT_STATUS_ERROR:
            logger.error(
                "sentinel_audit_reporting: error report_id=%s error=%s",
                result.report_id,
                result.error,
            )
            return
        if result.status == REPORT_STATUS_BLOCKED:
            logger.warning(
                "sentinel_audit_reporting: blocked report_id=%s reasons=%s",
                result.report_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "sentinel_audit_reporting: generated report_id=%s decision=%s",
            result.report_id,
            result.final_decision,
        )
