"""
SENTINEL audit pipeline for Hermes operational workflows.

This layer receives execution context and validation evidence, then produces an
official audit decision. It does not modify workflows, execute production code,
alter governance, or replace CENTINELA security authority.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.vulcan_operational_validation import (
    VulcanOperationalValidationResult,
)

logger = logging.getLogger(__name__)

AUDIT_DECISION_APPROVE = "approve"
AUDIT_DECISION_CONDITIONAL_APPROVE = "conditional_approve"
AUDIT_DECISION_REJECT = "reject"
AUDIT_DECISION_ESCALATE = "escalate"

AUDIT_STATUS_APPROVED = "approved"
AUDIT_STATUS_CONDITIONAL_APPROVED = "conditional_approved"
AUDIT_STATUS_REJECTED = "rejected"
AUDIT_STATUS_ESCALATED = "escalated"
AUDIT_STATUS_BLOCKED = "blocked"
AUDIT_STATUS_ERROR = "error"

PASSING_STATUSES = {
    "active",
    "approved",
    "clear",
    "ok",
    "online",
    "passed",
    "safe",
    "stable",
    "valid",
    "validated",
}

FAILING_STATUSES = {
    "blocked",
    "broken",
    "corrupt",
    "critical",
    "error",
    "failed",
    "invalid",
    "rejected",
    "unsafe",
}

SECURITY_ESCALATION_STATUSES = {
    "critical",
    "escalate",
    "escalated",
    "quarantine",
    "security_risk",
}

CLEAR_BLOCKING_CONDITIONS = {
    "clear",
    "none",
    "no_blockers",
    "no_blocking_conditions",
}

CLEAR_RISKS = {
    "clear",
    "none",
    "no_known_risks",
    "no_known_risks_declared",
}


@dataclass(frozen=True)
class SentinelAuditRequest:
    audit_id: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    execution_context: dict[str, Any] = field(default_factory=dict)
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    runtime_validation: Any | None = None
    import_validation: Any | None = None
    architecture_validation: Any | None = None
    governance_validation: Any | None = None
    security_observation: Any | None = None
    validation_results: dict[str, Any] = field(default_factory=dict)
    governance_context: dict[str, Any] = field(default_factory=dict)
    operational_validation: (
        VulcanOperationalValidationResult | dict[str, Any] | Any | None
    ) = None
    requested_decision: str | None = None
    risks_detected: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    auditor: str = "SENTINEL"
    modify_workflow_requested: bool = False
    alter_governance_requested: bool = False
    execute_productive_code_requested: bool = False
    replace_centinela_requested: bool = False
    falsify_audit_status_requested: bool = False
    approve_corrupt_workflow_requested: bool = False
    ignore_runtime_failures_requested: bool = False
    minimize_risks_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SentinelAuditResult:
    status: str
    success: bool
    audit_id: str
    execution_id: str | None
    task_id: str | None
    auditor: str
    audit_decision: str | None
    execution_context: dict[str, Any]
    modified_files: tuple[str, ...]
    runtime_valid: bool
    imports_valid: bool
    architecture_valid: bool
    governance_valid: bool
    security_observation_clear: bool
    runtime_integrity_preserved: bool
    execution_consistency_preserved: bool
    governance_audit_preserved: bool
    operational_stability_preserved: bool
    security_escalation_required: bool
    continuation_authorized: bool
    audit_completed: bool
    risks_detected: tuple[str, ...]
    blocking_conditions: tuple[str, ...]
    report_payload: dict[str, Any] = field(default_factory=dict)
    audit_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "audit_id": self.audit_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "auditor": self.auditor,
            "audit_decision": self.audit_decision,
            "execution_context": dict(self.execution_context),
            "modified_files": list(self.modified_files),
            "runtime_valid": self.runtime_valid,
            "imports_valid": self.imports_valid,
            "architecture_valid": self.architecture_valid,
            "governance_valid": self.governance_valid,
            "security_observation_clear": self.security_observation_clear,
            "runtime_integrity_preserved": self.runtime_integrity_preserved,
            "execution_consistency_preserved": (
                self.execution_consistency_preserved
            ),
            "governance_audit_preserved": self.governance_audit_preserved,
            "operational_stability_preserved": (
                self.operational_stability_preserved
            ),
            "security_escalation_required": self.security_escalation_required,
            "continuation_authorized": self.continuation_authorized,
            "audit_completed": self.audit_completed,
            "risks_detected": list(self.risks_detected),
            "blocking_conditions": list(self.blocking_conditions),
            "report_payload": dict(self.report_payload),
            "audit_lifecycle": [
                dict(entry) for entry in self.audit_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class SentinelAuditPipeline:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def audit(
        self,
        request: SentinelAuditRequest,
        audit_permitted: bool = True,
    ) -> SentinelAuditResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        audit_id = request.audit_id or str(uuid4())

        try:
            operational_validation = self._result_dict(
                request.operational_validation
            )
            modified_files = tuple(self._values(request.modified_files))
            risks = tuple(self._risks(request.risks_detected))
            blocking_conditions = tuple(
                self._values(request.blocking_conditions)
            )
            validation_states = self._validation_states(
                request,
                operational_validation,
            )
            reasons = self._validation_reasons(
                request=request,
                operational_validation=operational_validation,
                modified_files=modified_files,
                validation_states=validation_states,
                risks=risks,
                blocking_conditions=blocking_conditions,
                audit_permitted=audit_permitted,
            )
            if reasons:
                result = self._result(
                    status=AUDIT_STATUS_BLOCKED,
                    success=False,
                    audit_id=audit_id,
                    request=request,
                    modified_files=modified_files,
                    validation_states=validation_states,
                    risks=risks,
                    blocking_conditions=blocking_conditions,
                    decision=None,
                    reasons=reasons,
                    error=";".join(reasons),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            decision = self._decision(
                request=request,
                validation_states=validation_states,
                risks=risks,
                blocking_conditions=blocking_conditions,
            )
            status = self._status_for_decision(decision)
            result = self._result(
                status=status,
                success=True,
                audit_id=audit_id,
                request=request,
                modified_files=modified_files,
                validation_states=validation_states,
                risks=risks,
                blocking_conditions=blocking_conditions,
                decision=decision,
                reasons=self._decision_reasons(
                    decision,
                    validation_states,
                    risks,
                    blocking_conditions,
                ),
                error=None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                audit_id=audit_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def review(
        self,
        request: SentinelAuditRequest,
        audit_permitted: bool = True,
    ) -> SentinelAuditResult:
        return self.audit(request, audit_permitted=audit_permitted)

    def _result(
        self,
        status: str,
        success: bool,
        audit_id: str,
        request: SentinelAuditRequest,
        modified_files: tuple[str, ...],
        validation_states: dict[str, bool],
        risks: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        decision: str | None,
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> SentinelAuditResult:
        finished_at = datetime.now(timezone.utc)
        security_escalation = decision == AUDIT_DECISION_ESCALATE
        continuation_authorized = decision in {
            AUDIT_DECISION_APPROVE,
            AUDIT_DECISION_CONDITIONAL_APPROVE,
        }
        return SentinelAuditResult(
            status=status,
            success=success,
            audit_id=audit_id,
            execution_id=request.execution_id,
            task_id=request.task_id,
            auditor=request.auditor,
            audit_decision=decision,
            execution_context=dict(request.execution_context),
            modified_files=modified_files,
            runtime_valid=validation_states["runtime"],
            imports_valid=validation_states["imports"],
            architecture_valid=validation_states["architecture"],
            governance_valid=validation_states["governance"],
            security_observation_clear=validation_states["security"],
            runtime_integrity_preserved=validation_states["runtime"],
            execution_consistency_preserved=validation_states["imports"],
            governance_audit_preserved=not request.alter_governance_requested,
            operational_stability_preserved=(
                validation_states["runtime"]
                and validation_states["imports"]
                and validation_states["architecture"]
            ),
            security_escalation_required=security_escalation,
            continuation_authorized=continuation_authorized,
            audit_completed=success,
            risks_detected=risks,
            blocking_conditions=blocking_conditions,
            report_payload=self._report_payload(
                audit_id=audit_id,
                request=request,
                validation_states=validation_states,
                risks=risks,
                blocking_conditions=blocking_conditions,
                decision=decision,
                reasons=reasons,
            ),
            audit_lifecycle=(
                self._lifecycle("execution_reception"),
                self._lifecycle("technical_validation"),
                self._lifecycle("risk_detection"),
                self._lifecycle(status),
            ),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons),
            error=error,
            metadata=dict(request.metadata),
        )

    def _validation_reasons(
        self,
        request: SentinelAuditRequest,
        operational_validation: dict[str, Any],
        modified_files: tuple[str, ...],
        validation_states: dict[str, bool],
        risks: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        audit_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not audit_permitted:
            reasons.append("sentinel_audit_not_permitted")
        if request.auditor.upper() != "SENTINEL":
            reasons.append("invalid_sentinel_auditor")
        if not request.execution_context:
            reasons.append("execution_context_required")
        if not modified_files:
            reasons.append("modified_files_required")
        if operational_validation and operational_validation.get("status") not in {
            "validated",
            "blocked",
        }:
            reasons.append("operational_validation_status_invalid")
        if request.modify_workflow_requested:
            reasons.append("sentinel_execution_authority_blocked")
        if request.execute_productive_code_requested:
            reasons.append("sentinel_productive_execution_blocked")
        if request.alter_governance_requested:
            reasons.append("sentinel_governance_alteration_blocked")
        if request.replace_centinela_requested:
            reasons.append("centinela_replacement_blocked")
        if request.falsify_audit_status_requested:
            reasons.append("audit_status_falsification_blocked")
        if request.approve_corrupt_workflow_requested:
            reasons.append("corrupt_workflow_approval_blocked")
        if request.ignore_runtime_failures_requested:
            reasons.append("runtime_failure_ignored_blocked")
        if request.minimize_risks_requested and self._risks_active(risks):
            reasons.append("risk_minimization_blocked")
        return self._unique(reasons)

    def _decision(
        self,
        request: SentinelAuditRequest,
        validation_states: dict[str, bool],
        risks: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
    ) -> str:
        requested = self._normalize(request.requested_decision)
        if self._security_escalation_required(request):
            return AUDIT_DECISION_ESCALATE
        if (
            requested == AUDIT_DECISION_REJECT
            or self._blocking_active(blocking_conditions)
            or not all(validation_states.values())
        ):
            return AUDIT_DECISION_REJECT
        if requested == AUDIT_DECISION_ESCALATE:
            return AUDIT_DECISION_ESCALATE
        if (
            requested == AUDIT_DECISION_CONDITIONAL_APPROVE
            or self._risks_active(risks)
        ):
            return AUDIT_DECISION_CONDITIONAL_APPROVE
        return AUDIT_DECISION_APPROVE

    def _decision_reasons(
        self,
        decision: str,
        validation_states: dict[str, bool],
        risks: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
    ) -> list[str]:
        if decision == AUDIT_DECISION_APPROVE:
            return ["sentinel_audit_approved"]
        if decision == AUDIT_DECISION_CONDITIONAL_APPROVE:
            return self._unique(["sentinel_conditional_approval", *risks])
        if decision == AUDIT_DECISION_ESCALATE:
            return ["security_escalation_to_centinela"]
        reasons: list[str] = []
        for key, valid in validation_states.items():
            if not valid:
                reasons.append(f"{key}_validation_failed")
        if self._blocking_active(blocking_conditions):
            reasons.append("blocking_conditions_active")
        return self._unique(reasons or ["sentinel_audit_rejected"])

    def _status_for_decision(self, decision: str) -> str:
        if decision == AUDIT_DECISION_APPROVE:
            return AUDIT_STATUS_APPROVED
        if decision == AUDIT_DECISION_CONDITIONAL_APPROVE:
            return AUDIT_STATUS_CONDITIONAL_APPROVED
        if decision == AUDIT_DECISION_ESCALATE:
            return AUDIT_STATUS_ESCALATED
        return AUDIT_STATUS_REJECTED

    def _validation_states(
        self,
        request: SentinelAuditRequest,
        operational_validation: dict[str, Any],
    ) -> dict[str, bool]:
        return {
            "runtime": self._passed(
                request.runtime_validation
                if request.runtime_validation is not None
                else operational_validation.get("runtime_valid")
            ),
            "imports": self._passed(
                request.import_validation
                if request.import_validation is not None
                else operational_validation.get("imports_valid")
            ),
            "architecture": self._passed(
                request.architecture_validation
                if request.architecture_validation is not None
                else operational_validation.get("architecture_valid")
            ),
            "governance": self._passed(
                request.governance_validation
                if request.governance_validation is not None
                else operational_validation.get("governance_compliant")
            ),
            "security": self._security_clear(request.security_observation),
        }

    def _security_escalation_required(self, request: SentinelAuditRequest) -> bool:
        return self._normalize(request.security_observation) in (
            SECURITY_ESCALATION_STATUSES
        )

    def _security_clear(self, value: Any) -> bool:
        normalized = self._normalize(value)
        if normalized in SECURITY_ESCALATION_STATUSES:
            return False
        return normalized in PASSING_STATUSES or value is True

    def _passed(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, dict):
            for key in ("status", "validation_status", "state", "result"):
                if key in value:
                    return self._passed(value[key])
            return False
        normalized = self._normalize(value)
        if normalized in PASSING_STATUSES:
            return True
        if normalized in FAILING_STATUSES:
            return False
        return False

    def _blocking_active(self, blocking_conditions: tuple[str, ...]) -> bool:
        if not blocking_conditions:
            return False
        return any(
            (self._normalize(condition) or "") not in CLEAR_BLOCKING_CONDITIONS
            for condition in blocking_conditions
        )

    def _risks_active(self, risks: tuple[str, ...]) -> bool:
        if not risks:
            return False
        return any((self._normalize(risk) or "") not in CLEAR_RISKS for risk in risks)

    def _risks(self, values: tuple[str, ...]) -> list[str]:
        risks = [str(value).strip() for value in values if str(value).strip()]
        return self._unique(risks or ["no_known_risks"])

    def _report_payload(
        self,
        audit_id: str,
        request: SentinelAuditRequest,
        validation_states: dict[str, bool],
        risks: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        decision: str | None,
        reasons: list[str],
    ) -> dict[str, Any]:
        return {
            "audit_id": audit_id,
            "execution_id": request.execution_id,
            "task_id": request.task_id,
            "auditor": request.auditor,
            "audit_decision": decision,
            "validation_states": dict(validation_states),
            "risks_detected": list(risks),
            "blocking_conditions": list(blocking_conditions),
            "governance_context": dict(request.governance_context),
            "blocked_reasons": list(reasons),
        }

    def _result_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, VulcanOperationalValidationResult):
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
        audit_id: str,
        request: SentinelAuditRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> SentinelAuditResult:
        finished_at = datetime.now(timezone.utc)
        return SentinelAuditResult(
            status=AUDIT_STATUS_ERROR,
            success=False,
            audit_id=audit_id,
            execution_id=request.execution_id,
            task_id=request.task_id,
            auditor=request.auditor,
            audit_decision=None,
            execution_context=dict(request.execution_context),
            modified_files=tuple(request.modified_files),
            runtime_valid=False,
            imports_valid=False,
            architecture_valid=False,
            governance_valid=False,
            security_observation_clear=False,
            runtime_integrity_preserved=False,
            execution_consistency_preserved=False,
            governance_audit_preserved=False,
            operational_stability_preserved=False,
            security_escalation_required=False,
            continuation_authorized=False,
            audit_completed=False,
            risks_detected=tuple(request.risks_detected),
            blocking_conditions=tuple(request.blocking_conditions),
            report_payload={
                "audit_id": audit_id,
                "blocked_reasons": ["sentinel_audit_pipeline_error_contained"],
            },
            audit_lifecycle=(self._lifecycle(AUDIT_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("sentinel_audit_pipeline_error_contained",),
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

    def _publish(self, result: SentinelAuditResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_sentinel_audit_pipeline_result",
        ):
            self.status.mark_sentinel_audit_pipeline_result(result.to_dict())

    def _log_result(self, result: SentinelAuditResult) -> None:
        if result.status == AUDIT_STATUS_ERROR:
            logger.error(
                "sentinel_audit_pipeline: error audit_id=%s error=%s",
                result.audit_id,
                result.error,
            )
            return
        if result.status == AUDIT_STATUS_BLOCKED:
            logger.warning(
                "sentinel_audit_pipeline: blocked audit_id=%s reasons=%s",
                result.audit_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "sentinel_audit_pipeline: %s audit_id=%s decision=%s",
            result.status,
            result.audit_id,
            result.audit_decision,
        )
