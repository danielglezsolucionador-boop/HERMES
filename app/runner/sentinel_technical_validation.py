"""
SENTINEL technical validation for Hermes operational workflows.

This layer validates technical evidence for imports, syntax, runtime startup,
architecture, execution integrity, governance, and security observations. It is
read-only and does not execute production workflows or alter runtime.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.sentinel_audit_pipeline import SentinelAuditResult

logger = logging.getLogger(__name__)

TECHNICAL_STATUS_VALIDATED = "validated"
TECHNICAL_STATUS_BLOCKED = "blocked"
TECHNICAL_STATUS_ERROR = "error"

RECOMMEND_APPROVE = "approve"
RECOMMEND_CONDITIONAL = "conditional_approve"
RECOMMEND_REJECT = "reject"
RECOMMEND_ESCALATE = "escalate"

PASSING_STATUSES = {
    "active",
    "approved",
    "clear",
    "clean",
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
class SentinelTechnicalValidationRequest:
    validation_id: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    import_validation: Any | None = None
    syntax_validation: Any | None = None
    runtime_validation: Any | None = None
    architecture_validation: Any | None = None
    execution_validation: Any | None = None
    governance_validation: Any | None = None
    security_observation: Any | None = None
    validation_commands: tuple[str, ...] = field(default_factory=tuple)
    runtime_status: str | None = None
    architecture_status: str | None = None
    governance_status: str | None = None
    risks_detected: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    audit_pipeline: SentinelAuditResult | dict[str, Any] | Any | None = None
    falsify_validations_requested: bool = False
    ignore_runtime_failures_requested: bool = False
    hide_inconsistencies_requested: bool = False
    minimize_risks_requested: bool = False
    approve_corrupt_workflow_requested: bool = False
    alter_execution_runtime_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SentinelTechnicalValidationResult:
    status: str
    success: bool
    validation_id: str
    execution_id: str | None
    task_id: str | None
    modified_files: tuple[str, ...]
    validation_commands: tuple[str, ...]
    import_valid: bool
    syntax_valid: bool
    runtime_valid: bool
    architecture_valid: bool
    execution_integrity_valid: bool
    governance_compliant: bool
    security_observation_clear: bool
    blocking_conditions_clear: bool
    runtime_integrity_preserved: bool
    architecture_integrity_preserved: bool
    execution_stability_preserved: bool
    governance_consistency_preserved: bool
    operational_stability_preserved: bool
    workflow_safe: bool
    security_escalation_recommended: bool
    audit_decision_recommendation: str
    risks_detected: tuple[str, ...]
    blocking_conditions: tuple[str, ...]
    report_payload: dict[str, Any] = field(default_factory=dict)
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
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "modified_files": list(self.modified_files),
            "validation_commands": list(self.validation_commands),
            "import_valid": self.import_valid,
            "syntax_valid": self.syntax_valid,
            "runtime_valid": self.runtime_valid,
            "architecture_valid": self.architecture_valid,
            "execution_integrity_valid": self.execution_integrity_valid,
            "governance_compliant": self.governance_compliant,
            "security_observation_clear": self.security_observation_clear,
            "blocking_conditions_clear": self.blocking_conditions_clear,
            "runtime_integrity_preserved": self.runtime_integrity_preserved,
            "architecture_integrity_preserved": (
                self.architecture_integrity_preserved
            ),
            "execution_stability_preserved": (
                self.execution_stability_preserved
            ),
            "governance_consistency_preserved": (
                self.governance_consistency_preserved
            ),
            "operational_stability_preserved": (
                self.operational_stability_preserved
            ),
            "workflow_safe": self.workflow_safe,
            "security_escalation_recommended": (
                self.security_escalation_recommended
            ),
            "audit_decision_recommendation": (
                self.audit_decision_recommendation
            ),
            "risks_detected": list(self.risks_detected),
            "blocking_conditions": list(self.blocking_conditions),
            "report_payload": dict(self.report_payload),
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


class SentinelTechnicalValidation:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def validate(
        self,
        request: SentinelTechnicalValidationRequest,
        validation_permitted: bool = True,
    ) -> SentinelTechnicalValidationResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        validation_id = request.validation_id or str(uuid4())

        try:
            audit_pipeline = self._result_dict(request.audit_pipeline)
            modified_files = tuple(self._values(request.modified_files))
            validation_commands = tuple(self._values(request.validation_commands))
            risks = tuple(self._risks(request.risks_detected))
            blocking_conditions = tuple(
                self._values(request.blocking_conditions)
            )
            validation_states = self._validation_states(request)
            recommendation = self._recommendation(
                request=request,
                validation_states=validation_states,
                risks=risks,
                blocking_conditions=blocking_conditions,
                audit_pipeline=audit_pipeline,
            )
            reasons = self._validation_reasons(
                request=request,
                audit_pipeline=audit_pipeline,
                modified_files=modified_files,
                validation_commands=validation_commands,
                validation_states=validation_states,
                risks=risks,
                blocking_conditions=blocking_conditions,
                validation_permitted=validation_permitted,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    TECHNICAL_STATUS_BLOCKED
                    if blocked
                    else TECHNICAL_STATUS_VALIDATED
                ),
                success=not blocked,
                validation_id=validation_id,
                request=request,
                audit_pipeline=audit_pipeline,
                modified_files=modified_files,
                validation_commands=validation_commands,
                risks=risks,
                blocking_conditions=blocking_conditions,
                validation_states=validation_states,
                recommendation=recommendation,
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
                validation_id=validation_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def inspect(
        self,
        request: SentinelTechnicalValidationRequest,
        validation_permitted: bool = True,
    ) -> SentinelTechnicalValidationResult:
        return self.validate(
            request,
            validation_permitted=validation_permitted,
        )

    def _result(
        self,
        status: str,
        success: bool,
        validation_id: str,
        request: SentinelTechnicalValidationRequest,
        audit_pipeline: dict[str, Any],
        modified_files: tuple[str, ...],
        validation_commands: tuple[str, ...],
        risks: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        validation_states: dict[str, bool],
        recommendation: str,
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> SentinelTechnicalValidationResult:
        finished_at = datetime.now(timezone.utc)
        blocking_clear = not self._blocking_active(blocking_conditions)
        security_escalation = recommendation == RECOMMEND_ESCALATE
        workflow_safe = (
            success
            and all(validation_states.values())
            and blocking_clear
            and not security_escalation
        )
        return SentinelTechnicalValidationResult(
            status=status,
            success=success,
            validation_id=validation_id,
            execution_id=request.execution_id,
            task_id=request.task_id,
            modified_files=modified_files,
            validation_commands=validation_commands,
            import_valid=validation_states["import"],
            syntax_valid=validation_states["syntax"],
            runtime_valid=validation_states["runtime"],
            architecture_valid=validation_states["architecture"],
            execution_integrity_valid=validation_states["execution"],
            governance_compliant=validation_states["governance"],
            security_observation_clear=validation_states["security"],
            blocking_conditions_clear=blocking_clear,
            runtime_integrity_preserved=validation_states["runtime"],
            architecture_integrity_preserved=validation_states["architecture"],
            execution_stability_preserved=validation_states["execution"],
            governance_consistency_preserved=validation_states["governance"],
            operational_stability_preserved=(
                validation_states["runtime"]
                and validation_states["import"]
                and validation_states["syntax"]
                and validation_states["execution"]
            ),
            workflow_safe=workflow_safe,
            security_escalation_recommended=security_escalation,
            audit_decision_recommendation=recommendation,
            risks_detected=risks,
            blocking_conditions=blocking_conditions,
            report_payload=self._report_payload(
                validation_id=validation_id,
                request=request,
                audit_pipeline=audit_pipeline,
                validation_states=validation_states,
                risks=risks,
                blocking_conditions=blocking_conditions,
                recommendation=recommendation,
                reasons=reasons,
            ),
            validation_lifecycle=(
                self._lifecycle("execution_analysis"),
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
        request: SentinelTechnicalValidationRequest,
        audit_pipeline: dict[str, Any],
        modified_files: tuple[str, ...],
        validation_commands: tuple[str, ...],
        validation_states: dict[str, bool],
        risks: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        validation_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not validation_permitted:
            reasons.append("sentinel_technical_validation_not_permitted")
        if audit_pipeline and audit_pipeline.get("status") in {
            "rejected",
            "escalated",
            "blocked",
            "error",
        }:
            reasons.append("sentinel_audit_pipeline_blocks_validation")
        if not modified_files:
            reasons.append("modified_files_required")
        if not validation_commands:
            reasons.append("validation_commands_required")
        for key, valid in validation_states.items():
            if not valid:
                reasons.append(f"{key}_validation_failed")
        if self._blocking_active(blocking_conditions):
            reasons.append("blocking_conditions_active")
        if self._normalize(request.runtime_status) in FAILING_STATUSES:
            reasons.append("runtime_status_unsafe")
        if self._normalize(request.architecture_status) in FAILING_STATUSES:
            reasons.append("architecture_status_unsafe")
        if self._normalize(request.governance_status) in FAILING_STATUSES:
            reasons.append("governance_status_blocked")
        if request.falsify_validations_requested:
            reasons.append("false_validation_blocked")
        if request.ignore_runtime_failures_requested:
            reasons.append("runtime_failure_ignored_blocked")
        if request.hide_inconsistencies_requested:
            reasons.append("inconsistency_concealment_blocked")
        if request.minimize_risks_requested and self._risks_active(risks):
            reasons.append("risk_minimization_blocked")
        if request.approve_corrupt_workflow_requested:
            reasons.append("corrupt_workflow_approval_blocked")
        if request.alter_execution_runtime_requested:
            reasons.append("execution_runtime_alteration_blocked")
        return self._unique(reasons)

    def _recommendation(
        self,
        request: SentinelTechnicalValidationRequest,
        validation_states: dict[str, bool],
        risks: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        audit_pipeline: dict[str, Any],
    ) -> str:
        if self._security_escalation_required(request):
            return RECOMMEND_ESCALATE
        if audit_pipeline.get("audit_decision") == RECOMMEND_ESCALATE:
            return RECOMMEND_ESCALATE
        if (
            self._blocking_active(blocking_conditions)
            or not all(validation_states.values())
            or audit_pipeline.get("audit_decision") == RECOMMEND_REJECT
        ):
            return RECOMMEND_REJECT
        if self._risks_active(risks):
            return RECOMMEND_CONDITIONAL
        return RECOMMEND_APPROVE

    def _validation_states(
        self,
        request: SentinelTechnicalValidationRequest,
    ) -> dict[str, bool]:
        return {
            "import": self._passed(request.import_validation),
            "syntax": self._passed(request.syntax_validation),
            "runtime": self._passed(request.runtime_validation),
            "architecture": self._passed(request.architecture_validation),
            "execution": self._passed(request.execution_validation),
            "governance": self._passed(request.governance_validation),
            "security": self._security_clear(request.security_observation),
        }

    def _security_escalation_required(
        self,
        request: SentinelTechnicalValidationRequest,
    ) -> bool:
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
        return normalized in PASSING_STATUSES

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
        validation_id: str,
        request: SentinelTechnicalValidationRequest,
        audit_pipeline: dict[str, Any],
        validation_states: dict[str, bool],
        risks: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        recommendation: str,
        reasons: list[str],
    ) -> dict[str, Any]:
        return {
            "validation_id": validation_id,
            "execution_id": request.execution_id,
            "task_id": request.task_id,
            "audit_id": audit_pipeline.get("audit_id"),
            "validation_states": dict(validation_states),
            "runtime_status": request.runtime_status,
            "architecture_status": request.architecture_status,
            "governance_status": request.governance_status,
            "risks_detected": list(risks),
            "blocking_conditions": list(blocking_conditions),
            "audit_decision_recommendation": recommendation,
            "blocked_reasons": list(reasons),
        }

    def _result_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, SentinelAuditResult):
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
        validation_id: str,
        request: SentinelTechnicalValidationRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> SentinelTechnicalValidationResult:
        finished_at = datetime.now(timezone.utc)
        return SentinelTechnicalValidationResult(
            status=TECHNICAL_STATUS_ERROR,
            success=False,
            validation_id=validation_id,
            execution_id=request.execution_id,
            task_id=request.task_id,
            modified_files=tuple(request.modified_files),
            validation_commands=tuple(request.validation_commands),
            import_valid=False,
            syntax_valid=False,
            runtime_valid=False,
            architecture_valid=False,
            execution_integrity_valid=False,
            governance_compliant=False,
            security_observation_clear=False,
            blocking_conditions_clear=False,
            runtime_integrity_preserved=False,
            architecture_integrity_preserved=False,
            execution_stability_preserved=False,
            governance_consistency_preserved=False,
            operational_stability_preserved=False,
            workflow_safe=False,
            security_escalation_recommended=False,
            audit_decision_recommendation=RECOMMEND_REJECT,
            risks_detected=tuple(request.risks_detected),
            blocking_conditions=tuple(request.blocking_conditions),
            report_payload={
                "validation_id": validation_id,
                "blocked_reasons": [
                    "sentinel_technical_validation_error_contained"
                ],
            },
            validation_lifecycle=(self._lifecycle(TECHNICAL_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("sentinel_technical_validation_error_contained",),
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

    def _publish(self, result: SentinelTechnicalValidationResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_sentinel_technical_validation_result",
        ):
            self.status.mark_sentinel_technical_validation_result(
                result.to_dict()
            )

    def _log_result(self, result: SentinelTechnicalValidationResult) -> None:
        if result.status == TECHNICAL_STATUS_ERROR:
            logger.error(
                "sentinel_technical_validation: error validation_id=%s error=%s",
                result.validation_id,
                result.error,
            )
            return
        if result.status == TECHNICAL_STATUS_BLOCKED:
            logger.warning(
                "sentinel_technical_validation: blocked validation_id=%s reasons=%s",
                result.validation_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "sentinel_technical_validation: validated validation_id=%s recommendation=%s",
            result.validation_id,
            result.audit_decision_recommendation,
        )
