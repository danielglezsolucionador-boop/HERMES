"""
Governance escalation control for Hermes runtime.

This layer detects and reports critical governance escalation requirements.
It preserves blocking, authority boundaries, and execution context without
resolving escalations or mutating runtime execution.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.approval_system import ApprovalSystemResult
from app.runner.audit_response_control import AuditResponseControlResult
from app.runner.execution_blocking import ExecutionBlockResult
from app.runner.governance_foundation import GovernanceFoundationResult

logger = logging.getLogger(__name__)

ESCALATION_TYPE_GOVERNANCE = "governance"
ESCALATION_TYPE_APPROVAL = "approval"
ESCALATION_TYPE_AUDIT = "audit"
ESCALATION_TYPE_SECURITY = "security"
ESCALATION_TYPE_EXECUTION = "execution"
ESCALATION_TYPE_CONTINUATION = "continuation"
SUPPORTED_ESCALATION_TYPES = {
    ESCALATION_TYPE_GOVERNANCE,
    ESCALATION_TYPE_APPROVAL,
    ESCALATION_TYPE_AUDIT,
    ESCALATION_TYPE_SECURITY,
    ESCALATION_TYPE_EXECUTION,
    ESCALATION_TYPE_CONTINUATION,
}

ESCALATION_STATUS_ESCALATED = "escalated"
ESCALATION_STATUS_BLOCKED = "blocked"
ESCALATION_STATUS_ERROR = "error"

RISK_ELEVATED = "elevated"
RISK_CRITICAL = "critical"


@dataclass(frozen=True)
class GovernanceEscalationRequest:
    escalation_id: str | None = None
    escalation_type: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    execution_context: dict[str, Any] = field(default_factory=dict)
    governance_status: str | None = None
    approval_status: str | None = None
    audit_status: str | None = None
    security_status: str | None = None
    runtime_status: str | None = None
    blocking_status: str | None = None
    continuation_status: str | None = None
    risk_level: str | None = None
    escalation_reason: str | None = None
    authority_source: str | None = None
    governance_foundation: (
        GovernanceFoundationResult | dict[str, Any] | Any | None
    ) = None
    approval_system: ApprovalSystemResult | dict[str, Any] | Any | None = None
    audit_response: AuditResponseControlResult | dict[str, Any] | Any | None = None
    execution_block: ExecutionBlockResult | dict[str, Any] | Any | None = None
    risks: tuple[str, ...] = field(default_factory=tuple)
    escalation_history: tuple[Any, ...] = field(default_factory=tuple)
    governance_conflict_detected: bool = False
    approval_failure_detected: bool = False
    audit_rejection_detected: bool = False
    security_escalation_detected: bool = False
    runtime_instability_detected: bool = False
    operational_inconsistency_detected: bool = False
    continuation_unsafe_detected: bool = False
    self_resolution_requested: bool = False
    ignore_escalation_requested: bool = False
    minimize_risk_requested: bool = False
    bypass_authority_requested: bool = False
    invalidate_blocking_requested: bool = False
    falsify_severity_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GovernanceEscalationResult:
    status: str
    success: bool
    escalation_id: str
    escalation_type: str | None
    escalation_status: str
    escalation_reason: str | None
    reporting_authority: str | None
    execution_id: str | None
    task_id: str | None
    execution_context: dict[str, Any]
    governance_status: str | None
    approval_status: str | None
    audit_status: str | None
    security_status: str | None
    runtime_status: str | None
    blocking_status: str | None
    continuation_status: str | None
    risk_level: str | None
    critical_conflict_detected: bool
    escalation_required: bool
    authority_respected: bool
    no_self_resolution: bool
    governance_preserved: bool
    runtime_stability_preserved: bool
    blocking_preserved: bool
    execution_safety_preserved: bool
    context_preserved: bool
    traceability_preserved: bool
    honest_reporting_preserved: bool
    governance_conflict_detected: bool
    approval_failure_detected: bool
    audit_rejection_detected: bool
    security_escalation_detected: bool
    runtime_instability_detected: bool
    operational_inconsistency_detected: bool
    continuation_unsafe_detected: bool
    report_payload: dict[str, Any] = field(default_factory=dict)
    escalation_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    escalation_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    risks: tuple[str, ...] = field(default_factory=tuple)
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
            "escalation_type": self.escalation_type,
            "escalation_status": self.escalation_status,
            "escalation_reason": self.escalation_reason,
            "reporting_authority": self.reporting_authority,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "execution_context": dict(self.execution_context),
            "governance_status": self.governance_status,
            "approval_status": self.approval_status,
            "audit_status": self.audit_status,
            "security_status": self.security_status,
            "runtime_status": self.runtime_status,
            "blocking_status": self.blocking_status,
            "continuation_status": self.continuation_status,
            "risk_level": self.risk_level,
            "critical_conflict_detected": self.critical_conflict_detected,
            "escalation_required": self.escalation_required,
            "authority_respected": self.authority_respected,
            "no_self_resolution": self.no_self_resolution,
            "governance_preserved": self.governance_preserved,
            "runtime_stability_preserved": self.runtime_stability_preserved,
            "blocking_preserved": self.blocking_preserved,
            "execution_safety_preserved": self.execution_safety_preserved,
            "context_preserved": self.context_preserved,
            "traceability_preserved": self.traceability_preserved,
            "honest_reporting_preserved": self.honest_reporting_preserved,
            "governance_conflict_detected": self.governance_conflict_detected,
            "approval_failure_detected": self.approval_failure_detected,
            "audit_rejection_detected": self.audit_rejection_detected,
            "security_escalation_detected": (
                self.security_escalation_detected
            ),
            "runtime_instability_detected": (
                self.runtime_instability_detected
            ),
            "operational_inconsistency_detected": (
                self.operational_inconsistency_detected
            ),
            "continuation_unsafe_detected": (
                self.continuation_unsafe_detected
            ),
            "report_payload": dict(self.report_payload),
            "escalation_lifecycle": [
                dict(entry) for entry in self.escalation_lifecycle
            ],
            "escalation_history": [
                dict(entry) for entry in self.escalation_history
            ],
            "risks": list(self.risks),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class GovernanceEscalation:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def escalate(
        self,
        request: GovernanceEscalationRequest,
        runtime_active: bool = True,
        escalation_permitted: bool = True,
    ) -> GovernanceEscalationResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        escalation_id = request.escalation_id or str(uuid4())

        try:
            governance = self._as_dict(request.governance_foundation)
            approval = self._as_dict(request.approval_system)
            audit = self._as_dict(request.audit_response)
            block = self._as_dict(request.execution_block)
            signals = self._signals(request, governance, approval, audit, block)
            escalation_type = self._escalation_type(request, signals, block)
            execution_id = self._execution_id(request, governance, approval, audit, block)
            task_id = self._task_id(request, approval, audit, block)
            risk_level = self._risk_level(request, escalation_type, signals, block)
            escalation_reason = self._escalation_reason(
                request,
                escalation_type,
                governance,
                approval,
                audit,
                block,
            )
            reporting_authority = self._reporting_authority(
                request,
                escalation_type,
                governance,
                approval,
            )
            reasons = self._validation_reasons(
                request=request,
                runtime_active=runtime_active,
                escalation_permitted=escalation_permitted,
                escalation_type=escalation_type,
                execution_id=execution_id,
                escalation_reason=escalation_reason,
                reporting_authority=reporting_authority,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    ESCALATION_STATUS_BLOCKED
                    if blocked
                    else ESCALATION_STATUS_ESCALATED
                ),
                success=not blocked,
                escalation_id=escalation_id,
                escalation_type=escalation_type,
                escalation_reason=escalation_reason,
                reporting_authority=reporting_authority,
                execution_id=execution_id,
                task_id=task_id,
                risk_level=risk_level,
                request=request,
                governance=governance,
                approval=approval,
                audit=audit,
                block=block,
                signals=signals,
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

    def _result(
        self,
        status: str,
        success: bool,
        escalation_id: str,
        escalation_type: str | None,
        escalation_reason: str | None,
        reporting_authority: str | None,
        execution_id: str | None,
        task_id: str | None,
        risk_level: str | None,
        request: GovernanceEscalationRequest,
        governance: dict[str, Any],
        approval: dict[str, Any],
        audit: dict[str, Any],
        block: dict[str, Any],
        signals: dict[str, bool],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> GovernanceEscalationResult:
        finished_at = datetime.now(timezone.utc)
        no_self_resolution = not request.self_resolution_requested
        authority_respected = not request.bypass_authority_requested
        blocking_preserved = not request.invalidate_blocking_requested
        honest_reporting = not (
            request.ignore_escalation_requested
            or request.minimize_risk_requested
            or request.falsify_severity_requested
        )
        return GovernanceEscalationResult(
            status=status,
            success=success,
            escalation_id=escalation_id,
            escalation_type=escalation_type,
            escalation_status="active" if success else status,
            escalation_reason=escalation_reason,
            reporting_authority=reporting_authority,
            execution_id=execution_id,
            task_id=task_id,
            execution_context=self._execution_context(request, governance, block),
            governance_status=self._governance_status(request, governance, approval),
            approval_status=self._approval_status(request, approval),
            audit_status=self._audit_status(request, audit),
            security_status=self._security_status(request, governance, approval, audit),
            runtime_status=self._runtime_status(request, block),
            blocking_status=self._blocking_status(request, governance, approval, block),
            continuation_status=self._continuation_status(request, block),
            risk_level=risk_level,
            critical_conflict_detected=any(signals.values()),
            escalation_required=success,
            authority_respected=authority_respected,
            no_self_resolution=no_self_resolution,
            governance_preserved=True,
            runtime_stability_preserved=not request.falsify_severity_requested,
            blocking_preserved=blocking_preserved,
            execution_safety_preserved=not request.ignore_escalation_requested,
            context_preserved=True,
            traceability_preserved=True,
            honest_reporting_preserved=honest_reporting,
            governance_conflict_detected=signals["governance_conflict"],
            approval_failure_detected=signals["approval_failure"],
            audit_rejection_detected=signals["audit_rejection"],
            security_escalation_detected=signals["security_escalation"],
            runtime_instability_detected=signals["runtime_instability"],
            operational_inconsistency_detected=(
                signals["operational_inconsistency"]
            ),
            continuation_unsafe_detected=signals["continuation_unsafe"],
            report_payload=self._report_payload(
                escalation_id=escalation_id,
                request=request,
                escalation_type=escalation_type,
                escalation_reason=escalation_reason,
                reporting_authority=reporting_authority,
                risk_level=risk_level,
                signals=signals,
                reasons=reasons,
            ),
            escalation_lifecycle=(
                self._lifecycle("escalation_detection_completed"),
                self._lifecycle("escalation_validation_completed"),
                self._lifecycle(status),
            ),
            escalation_history=tuple(self._escalation_history(request)),
            risks=tuple(self._risks(request, governance, approval, audit, block)),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons),
            error=error,
            metadata=dict(request.metadata),
        )

    def _signals(
        self,
        request: GovernanceEscalationRequest,
        governance: dict[str, Any],
        approval: dict[str, Any],
        audit: dict[str, Any],
        block: dict[str, Any],
    ) -> dict[str, bool]:
        governance_status = self._normalize(
            governance.get("status")
            or governance.get("governance_status")
            or request.governance_status
        )
        approval_status = self._normalize(
            approval.get("status")
            or approval.get("approval_status")
            or request.approval_status
        )
        audit_status = self._normalize(
            audit.get("status")
            or audit.get("audit_result")
            or request.audit_status
        )
        security_status = self._normalize(
            request.security_status
            or governance.get("security_status")
            or approval.get("security_status")
            or audit.get("security_escalation_status")
        )
        block_type = self._normalize(block.get("block_type"))
        return {
            "governance_conflict": request.governance_conflict_detected
            or governance_status in {"blocked", "rejected", "escalated"}
            or bool(governance.get("reasons")),
            "approval_failure": request.approval_failure_detected
            or approval_status in {"blocked", "rejected", "escalation_required"}
            or approval.get("approval_exists") is False,
            "audit_rejection": request.audit_rejection_detected
            or audit_status in {"rejected", "needs_fix"},
            "security_escalation": request.security_escalation_detected
            or security_status in {
                "blocked",
                "critical",
                "critical_blocking",
                "escalated",
                "quarantine",
            }
            or block_type == ESCALATION_TYPE_SECURITY,
            "runtime_instability": request.runtime_instability_detected
            or self._runtime_unstable(request, block),
            "operational_inconsistency": (
                request.operational_inconsistency_detected
                or bool(block.get("execution_inconsistency_detected"))
            ),
            "continuation_unsafe": request.continuation_unsafe_detected
            or self._continuation_unsafe(request, block),
        }

    def _escalation_type(
        self,
        request: GovernanceEscalationRequest,
        signals: dict[str, bool],
        block: dict[str, Any],
    ) -> str | None:
        explicit = self._normalize(request.escalation_type)
        if explicit:
            return explicit
        block_type = self._normalize(block.get("block_type"))
        if block_type in SUPPORTED_ESCALATION_TYPES:
            return block_type
        ordered = (
            ("security_escalation", ESCALATION_TYPE_SECURITY),
            ("audit_rejection", ESCALATION_TYPE_AUDIT),
            ("approval_failure", ESCALATION_TYPE_APPROVAL),
            ("governance_conflict", ESCALATION_TYPE_GOVERNANCE),
            ("runtime_instability", ESCALATION_TYPE_EXECUTION),
            ("operational_inconsistency", ESCALATION_TYPE_EXECUTION),
            ("continuation_unsafe", ESCALATION_TYPE_CONTINUATION),
        )
        for key, value in ordered:
            if signals[key]:
                return value
        return None

    def _risk_level(
        self,
        request: GovernanceEscalationRequest,
        escalation_type: str | None,
        signals: dict[str, bool],
        block: dict[str, Any],
    ) -> str | None:
        value = request.risk_level or block.get("risk_level")
        if value:
            return self._normalize(value)
        if escalation_type in {
            ESCALATION_TYPE_SECURITY,
            ESCALATION_TYPE_EXECUTION,
            ESCALATION_TYPE_CONTINUATION,
        } or signals["security_escalation"]:
            return RISK_CRITICAL
        if escalation_type in SUPPORTED_ESCALATION_TYPES:
            return RISK_ELEVATED
        return None

    def _escalation_reason(
        self,
        request: GovernanceEscalationRequest,
        escalation_type: str | None,
        governance: dict[str, Any],
        approval: dict[str, Any],
        audit: dict[str, Any],
        block: dict[str, Any],
    ) -> str | None:
        if request.escalation_reason:
            return request.escalation_reason
        if block.get("block_reason"):
            return str(block["block_reason"])
        if audit.get("block_reason"):
            return str(audit["block_reason"])
        if approval.get("execution_decision"):
            return str(approval["execution_decision"])
        if governance.get("status"):
            return str(governance["status"])
        reasons = {
            ESCALATION_TYPE_GOVERNANCE: "governance_conflict_requires_escalation",
            ESCALATION_TYPE_APPROVAL: "approval_failure_requires_escalation",
            ESCALATION_TYPE_AUDIT: "audit_rejection_requires_escalation",
            ESCALATION_TYPE_SECURITY: "security_escalation_requires_authority",
            ESCALATION_TYPE_EXECUTION: "runtime_instability_requires_escalation",
            ESCALATION_TYPE_CONTINUATION: "unsafe_continuation_requires_escalation",
        }
        return reasons.get(escalation_type)

    def _reporting_authority(
        self,
        request: GovernanceEscalationRequest,
        escalation_type: str | None,
        governance: dict[str, Any],
        approval: dict[str, Any],
    ) -> str | None:
        if request.authority_source:
            return request.authority_source
        if escalation_type == ESCALATION_TYPE_SECURITY:
            return "CENTINELA"
        if escalation_type == ESCALATION_TYPE_AUDIT:
            return "SENTINEL"
        if escalation_type in {ESCALATION_TYPE_GOVERNANCE, ESCALATION_TYPE_APPROVAL}:
            return "CEO"
        if escalation_type in {ESCALATION_TYPE_EXECUTION, ESCALATION_TYPE_CONTINUATION}:
            return governance.get("reporting_target") or approval.get(
                "authority_source"
            ) or "CEREBRO"
        return None

    def _validation_reasons(
        self,
        request: GovernanceEscalationRequest,
        runtime_active: bool,
        escalation_permitted: bool,
        escalation_type: str | None,
        execution_id: str | None,
        escalation_reason: str | None,
        reporting_authority: str | None,
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not escalation_permitted:
            reasons.append("governance_escalation_not_permitted")
        if escalation_type not in SUPPORTED_ESCALATION_TYPES:
            reasons.append("unsupported_escalation_type")
        if not execution_id:
            reasons.append("missing_execution_id")
        if not escalation_reason:
            reasons.append("missing_escalation_reason")
        if not reporting_authority:
            reasons.append("missing_reporting_authority")
        if request.self_resolution_requested:
            reasons.append("self_resolution_blocked")
        if request.bypass_authority_requested:
            reasons.append("authority_bypass_blocked")
        if request.invalidate_blocking_requested:
            reasons.append("critical_blocking_preserved")
        if (
            request.ignore_escalation_requested
            or request.minimize_risk_requested
            or request.falsify_severity_requested
        ):
            reasons.append("dishonest_escalation_reporting_blocked")
        return self._unique(reasons)

    def _execution_id(
        self,
        request: GovernanceEscalationRequest,
        governance: dict[str, Any],
        approval: dict[str, Any],
        audit: dict[str, Any],
        block: dict[str, Any],
    ) -> str | None:
        return (
            request.execution_id
            or request.execution_context.get("execution_id")
            or governance.get("execution_context", {}).get("execution_id")
            or approval.get("execution_id")
            or audit.get("execution_id")
            or block.get("execution_id")
        )

    def _task_id(
        self,
        request: GovernanceEscalationRequest,
        approval: dict[str, Any],
        audit: dict[str, Any],
        block: dict[str, Any],
    ) -> str | None:
        return (
            request.task_id
            or request.execution_context.get("task_id")
            or approval.get("task_id")
            or audit.get("task_id")
            or block.get("task_id")
        )

    def _execution_context(
        self,
        request: GovernanceEscalationRequest,
        governance: dict[str, Any],
        block: dict[str, Any],
    ) -> dict[str, Any]:
        context: dict[str, Any] = {}
        context.update(governance.get("execution_context") or {})
        context.update(block.get("execution_context") or {})
        context.update(request.execution_context or {})
        return context

    def _governance_status(
        self,
        request: GovernanceEscalationRequest,
        governance: dict[str, Any],
        approval: dict[str, Any],
    ) -> str | None:
        return self._normalize(
            request.governance_status
            or governance.get("governance_status")
            or governance.get("status")
            or approval.get("governance_status")
        )

    def _approval_status(
        self,
        request: GovernanceEscalationRequest,
        approval: dict[str, Any],
    ) -> str | None:
        return self._normalize(
            request.approval_status
            or approval.get("approval_status")
            or approval.get("status")
        )

    def _audit_status(
        self,
        request: GovernanceEscalationRequest,
        audit: dict[str, Any],
    ) -> str | None:
        return self._normalize(
            request.audit_status
            or audit.get("audit_result")
            or audit.get("status")
        )

    def _security_status(
        self,
        request: GovernanceEscalationRequest,
        governance: dict[str, Any],
        approval: dict[str, Any],
        audit: dict[str, Any],
    ) -> str | None:
        return self._normalize(
            request.security_status
            or governance.get("security_status")
            or approval.get("security_status")
            or audit.get("security_escalation_status")
        )

    def _runtime_status(
        self,
        request: GovernanceEscalationRequest,
        block: dict[str, Any],
    ) -> str | None:
        return self._normalize(
            request.runtime_status
            or block.get("runtime_state", {}).get("status")
        )

    def _blocking_status(
        self,
        request: GovernanceEscalationRequest,
        governance: dict[str, Any],
        approval: dict[str, Any],
        block: dict[str, Any],
    ) -> str | None:
        return self._normalize(
            request.blocking_status
            or governance.get("blocking_status")
            or approval.get("blocking_status")
            or block.get("block_status")
        )

    def _continuation_status(
        self,
        request: GovernanceEscalationRequest,
        block: dict[str, Any],
    ) -> str | None:
        return self._normalize(
            request.continuation_status or block.get("continuation_status")
        )

    def _runtime_unstable(
        self,
        request: GovernanceEscalationRequest,
        block: dict[str, Any],
    ) -> bool:
        value = self._normalize(request.runtime_status) or self._normalize(
            block.get("runtime_state", {}).get("status")
        )
        return value in {"unstable", "corrupt", "compromised", "invalid_state"} or bool(
            block.get("runtime_corruption_detected")
        )

    def _continuation_unsafe(
        self,
        request: GovernanceEscalationRequest,
        block: dict[str, Any],
    ) -> bool:
        value = self._normalize(
            request.continuation_status or block.get("continuation_status")
        )
        return value in {
            "unsafe",
            "blocked_unsafe_continuation",
            "blocked_security_authority",
            "blocked_approval_authority",
            "blocked_governance_authority",
        } or bool(block.get("continuation_unsafe_detected"))

    def _risks(
        self,
        request: GovernanceEscalationRequest,
        governance: dict[str, Any],
        approval: dict[str, Any],
        audit: dict[str, Any],
        block: dict[str, Any],
    ) -> list[str]:
        return self._unique(
            [
                *[str(item) for item in request.risks],
                *[str(item) for item in governance.get("risks") or []],
                *[str(item) for item in approval.get("risks") or []],
                *[str(item) for item in audit.get("detected_risks") or []],
                *[str(item) for item in block.get("risk_history") or []],
            ]
        )

    def _report_payload(
        self,
        escalation_id: str,
        request: GovernanceEscalationRequest,
        escalation_type: str | None,
        escalation_reason: str | None,
        reporting_authority: str | None,
        risk_level: str | None,
        signals: dict[str, bool],
        reasons: list[str],
    ) -> dict[str, Any]:
        return {
            "escalation_id": escalation_id,
            "escalation_type": escalation_type,
            "escalation_reason": escalation_reason,
            "reporting_authority": reporting_authority,
            "execution_context": dict(request.execution_context),
            "governance_status": self._normalize(request.governance_status),
            "approval_status": self._normalize(request.approval_status),
            "audit_status": self._normalize(request.audit_status),
            "security_status": self._normalize(request.security_status),
            "runtime_status": self._normalize(request.runtime_status),
            "blocking_status": self._normalize(request.blocking_status),
            "continuation_status": self._normalize(request.continuation_status),
            "risk_level": risk_level,
            "signals": dict(signals),
            "blocked_reasons": list(reasons),
        }

    def _escalation_history(
        self,
        request: GovernanceEscalationRequest,
    ) -> list[dict[str, Any]]:
        return [self._as_dict(entry) for entry in request.escalation_history]

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(
            value,
            (
                GovernanceFoundationResult,
                ApprovalSystemResult,
                AuditResponseControlResult,
                ExecutionBlockResult,
            ),
        ):
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

    def _error_result(
        self,
        escalation_id: str,
        request: GovernanceEscalationRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> GovernanceEscalationResult:
        finished_at = datetime.now(timezone.utc)
        return GovernanceEscalationResult(
            status=ESCALATION_STATUS_ERROR,
            success=False,
            escalation_id=escalation_id,
            escalation_type=self._normalize(request.escalation_type),
            escalation_status=ESCALATION_STATUS_ERROR,
            escalation_reason=request.escalation_reason,
            reporting_authority=request.authority_source,
            execution_id=request.execution_id,
            task_id=request.task_id,
            execution_context=dict(request.execution_context),
            governance_status=self._normalize(request.governance_status),
            approval_status=self._normalize(request.approval_status),
            audit_status=self._normalize(request.audit_status),
            security_status=self._normalize(request.security_status),
            runtime_status=self._normalize(request.runtime_status),
            blocking_status=self._normalize(request.blocking_status),
            continuation_status=self._normalize(request.continuation_status),
            risk_level=self._normalize(request.risk_level),
            critical_conflict_detected=False,
            escalation_required=False,
            authority_respected=False,
            no_self_resolution=False,
            governance_preserved=False,
            runtime_stability_preserved=False,
            blocking_preserved=False,
            execution_safety_preserved=False,
            context_preserved=True,
            traceability_preserved=True,
            honest_reporting_preserved=False,
            governance_conflict_detected=False,
            approval_failure_detected=False,
            audit_rejection_detected=False,
            security_escalation_detected=False,
            runtime_instability_detected=False,
            operational_inconsistency_detected=False,
            continuation_unsafe_detected=False,
            escalation_lifecycle=(self._lifecycle(ESCALATION_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("governance_escalation_error_contained",),
            error=error,
            metadata=dict(request.metadata),
        )

    def _publish(self, result: GovernanceEscalationResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_governance_escalation_result",
        ):
            self.status.mark_governance_escalation_result(result.to_dict())

    def _log_result(self, result: GovernanceEscalationResult) -> None:
        if result.status == ESCALATION_STATUS_ERROR:
            logger.error(
                "governance_escalation: error escalation_id=%s error=%s",
                result.escalation_id,
                result.error,
            )
            return
        if result.status == ESCALATION_STATUS_BLOCKED:
            logger.warning(
                "governance_escalation: blocked escalation_id=%s reasons=%s",
                result.escalation_id,
                ",".join(result.reasons),
            )
            return
        logger.warning(
            "governance_escalation: escalated escalation_id=%s type=%s authority=%s",
            result.escalation_id,
            result.escalation_type,
            result.reporting_authority,
        )
