"""
Governance safety barrier for Hermes runtime.

This layer preserves official governance boundaries before execution or
continuation. It detects unsafe autonomy, authority conflicts, audit/security
violations, and active blocks without changing runtime behavior.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.approval_system import ApprovalSystemResult
from app.runner.continuation_safety import ContinuationSafetyResult
from app.runner.execution_blocking import ExecutionBlockResult
from app.runner.governance_escalation import GovernanceEscalationResult
from app.runner.governance_foundation import GovernanceFoundationResult

logger = logging.getLogger(__name__)

SAFETY_TYPE_HUMAN_AUTHORITY = "human_authority"
SAFETY_TYPE_GOVERNANCE = "governance"
SAFETY_TYPE_AUDIT = "audit"
SAFETY_TYPE_SECURITY = "security"
SAFETY_TYPE_EXECUTION = "execution"
SAFETY_TYPE_CONTINUATION = "continuation"
SUPPORTED_SAFETY_TYPES = {
    SAFETY_TYPE_HUMAN_AUTHORITY,
    SAFETY_TYPE_GOVERNANCE,
    SAFETY_TYPE_AUDIT,
    SAFETY_TYPE_SECURITY,
    SAFETY_TYPE_EXECUTION,
    SAFETY_TYPE_CONTINUATION,
}

GOVERNANCE_SAFETY_STATUS_SAFE = "safe"
GOVERNANCE_SAFETY_STATUS_BLOCKED = "blocked"
GOVERNANCE_SAFETY_STATUS_ERROR = "error"

APPROVED_STATUSES = {
    "approved",
    "human_approved",
    "authorized",
    "authorized_by_human",
    "validated",
}
BLOCKING_STATUSES = {
    "active",
    "blocked",
    "critical",
    "critical_blocking",
    "critical_blocked",
    "quarantine",
    "rejected",
    "escalated",
}
SAFE_RUNTIME_STATUSES = {"active", "online", "ready", "stable"}


@dataclass(frozen=True)
class GovernanceSafetyRequest:
    safety_id: str | None = None
    safety_type: str = SAFETY_TYPE_GOVERNANCE
    execution_id: str | None = None
    task_id: str | None = None
    authority_source: str | None = None
    execution_context: dict[str, Any] = field(default_factory=dict)
    authority_status: str | None = None
    governance_status: str | None = None
    approval_status: str | None = None
    audit_status: str | None = None
    security_status: str | None = None
    runtime_status: str | None = None
    blocking_status: str | None = None
    continuation_status: str | None = None
    risk_level: str | None = None
    governance_foundation: (
        GovernanceFoundationResult | dict[str, Any] | Any | None
    ) = None
    approval_system: ApprovalSystemResult | dict[str, Any] | Any | None = None
    governance_escalation: (
        GovernanceEscalationResult | dict[str, Any] | Any | None
    ) = None
    execution_blocking: ExecutionBlockResult | dict[str, Any] | Any | None = None
    continuation_safety: (
        ContinuationSafetyResult | dict[str, Any] | Any | None
    ) = None
    risks: tuple[str, ...] = field(default_factory=tuple)
    governance_history: tuple[Any, ...] = field(default_factory=tuple)
    authority_override_requested: bool = False
    alter_authorities_requested: bool = False
    autonomy_expansion_requested: bool = False
    governance_redefinition_requested: bool = False
    ignore_critical_block_requested: bool = False
    invalidate_audit_requested: bool = False
    ignore_security_escalation_requested: bool = False
    unsafe_execution_requested: bool = False
    continuation_override_requested: bool = False
    conceal_conflicts_requested: bool = False
    minimize_risk_requested: bool = False
    falsify_governance_status_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GovernanceSafetyResult:
    status: str
    success: bool
    safety_id: str
    safety_type: str | None
    safety_status: str
    execution_id: str | None
    task_id: str | None
    authority_source: str | None
    reporting_authority: str | None
    execution_context: dict[str, Any]
    authority_status: str | None
    governance_status: str | None
    approval_status: str | None
    audit_status: str | None
    security_status: str | None
    runtime_status: str | None
    blocking_status: str | None
    continuation_status: str | None
    risk_level: str | None
    execution_allowed: bool
    continuation_allowed: bool
    human_authority_preserved: bool
    autonomy_limited: bool
    governance_integrity_preserved: bool
    audit_respected: bool
    security_respected: bool
    blocking_respected: bool
    runtime_stability_preserved: bool
    ecosystem_coherence_preserved: bool
    operational_transparency_preserved: bool
    traceability_preserved: bool
    human_authority_risk_detected: bool
    governance_risk_detected: bool
    audit_risk_detected: bool
    security_risk_detected: bool
    execution_risk_detected: bool
    continuation_risk_detected: bool
    escalation_required: bool
    report_payload: dict[str, Any] = field(default_factory=dict)
    governance_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    safety_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "safety_id": self.safety_id,
            "safety_type": self.safety_type,
            "safety_status": self.safety_status,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "authority_source": self.authority_source,
            "reporting_authority": self.reporting_authority,
            "execution_context": dict(self.execution_context),
            "authority_status": self.authority_status,
            "governance_status": self.governance_status,
            "approval_status": self.approval_status,
            "audit_status": self.audit_status,
            "security_status": self.security_status,
            "runtime_status": self.runtime_status,
            "blocking_status": self.blocking_status,
            "continuation_status": self.continuation_status,
            "risk_level": self.risk_level,
            "execution_allowed": self.execution_allowed,
            "continuation_allowed": self.continuation_allowed,
            "human_authority_preserved": self.human_authority_preserved,
            "autonomy_limited": self.autonomy_limited,
            "governance_integrity_preserved": (
                self.governance_integrity_preserved
            ),
            "audit_respected": self.audit_respected,
            "security_respected": self.security_respected,
            "blocking_respected": self.blocking_respected,
            "runtime_stability_preserved": self.runtime_stability_preserved,
            "ecosystem_coherence_preserved": (
                self.ecosystem_coherence_preserved
            ),
            "operational_transparency_preserved": (
                self.operational_transparency_preserved
            ),
            "traceability_preserved": self.traceability_preserved,
            "human_authority_risk_detected": (
                self.human_authority_risk_detected
            ),
            "governance_risk_detected": self.governance_risk_detected,
            "audit_risk_detected": self.audit_risk_detected,
            "security_risk_detected": self.security_risk_detected,
            "execution_risk_detected": self.execution_risk_detected,
            "continuation_risk_detected": self.continuation_risk_detected,
            "escalation_required": self.escalation_required,
            "report_payload": dict(self.report_payload),
            "governance_history": [
                dict(entry) for entry in self.governance_history
            ],
            "safety_lifecycle": [
                dict(entry) for entry in self.safety_lifecycle
            ],
            "risks": list(self.risks),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class GovernanceSafety:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def validate(
        self,
        request: GovernanceSafetyRequest,
        runtime_active: bool = True,
        safety_permitted: bool = True,
    ) -> GovernanceSafetyResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        safety_id = request.safety_id or str(uuid4())

        try:
            governance = self._as_dict(request.governance_foundation)
            approval = self._as_dict(request.approval_system)
            escalation = self._as_dict(request.governance_escalation)
            execution_block = self._as_dict(request.execution_blocking)
            continuation = self._as_dict(request.continuation_safety)
            safety_type = self._safety_type(request, escalation, execution_block)
            statuses = self._statuses(
                request,
                governance,
                approval,
                escalation,
                execution_block,
                continuation,
            )
            risks = self._risk_flags(
                request,
                governance,
                approval,
                escalation,
                execution_block,
                continuation,
                statuses,
                runtime_active,
            )
            reasons = self._validation_reasons(
                request=request,
                safety_type=safety_type,
                risks=risks,
                statuses=statuses,
                runtime_active=runtime_active,
                safety_permitted=safety_permitted,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    GOVERNANCE_SAFETY_STATUS_BLOCKED
                    if blocked
                    else GOVERNANCE_SAFETY_STATUS_SAFE
                ),
                success=not blocked,
                safety_id=safety_id,
                safety_type=safety_type,
                request=request,
                statuses=statuses,
                risks=risks,
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
                safety_id=safety_id,
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
        safety_id: str,
        safety_type: str | None,
        request: GovernanceSafetyRequest,
        statuses: dict[str, Any],
        risks: dict[str, bool],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> GovernanceSafetyResult:
        finished_at = datetime.now(timezone.utc)
        autonomy_limited = not (
            request.autonomy_expansion_requested
            or request.governance_redefinition_requested
        )
        human_authority_preserved = not (
            request.authority_override_requested
            or request.alter_authorities_requested
        )
        blocking_respected = not request.ignore_critical_block_requested
        audit_respected = not request.invalidate_audit_requested
        security_respected = not request.ignore_security_escalation_requested
        transparency_preserved = not (
            request.conceal_conflicts_requested
            or request.minimize_risk_requested
            or request.falsify_governance_status_requested
        )
        return GovernanceSafetyResult(
            status=status,
            success=success,
            safety_id=safety_id,
            safety_type=safety_type,
            safety_status="preserved" if success else "blocked",
            execution_id=statuses["execution_id"],
            task_id=statuses["task_id"],
            authority_source=statuses["authority_source"],
            reporting_authority=self._reporting_authority(safety_type, statuses),
            execution_context=dict(statuses["execution_context"]),
            authority_status=statuses["authority_status"],
            governance_status=statuses["governance_status"],
            approval_status=statuses["approval_status"],
            audit_status=statuses["audit_status"],
            security_status=statuses["security_status"],
            runtime_status=statuses["runtime_status"],
            blocking_status=statuses["blocking_status"],
            continuation_status=statuses["continuation_status"],
            risk_level=statuses["risk_level"],
            execution_allowed=success,
            continuation_allowed=success and not risks["continuation"],
            human_authority_preserved=human_authority_preserved,
            autonomy_limited=autonomy_limited,
            governance_integrity_preserved=not risks["governance"],
            audit_respected=audit_respected,
            security_respected=security_respected,
            blocking_respected=blocking_respected,
            runtime_stability_preserved=not risks["execution"],
            ecosystem_coherence_preserved=not (
                request.governance_redefinition_requested
                or request.alter_authorities_requested
            ),
            operational_transparency_preserved=transparency_preserved,
            traceability_preserved=True,
            human_authority_risk_detected=risks["human_authority"],
            governance_risk_detected=risks["governance"],
            audit_risk_detected=risks["audit"],
            security_risk_detected=risks["security"],
            execution_risk_detected=risks["execution"],
            continuation_risk_detected=risks["continuation"],
            escalation_required=risks["security"]
            or risks["audit"]
            or risks["execution"]
            or risks["governance"],
            report_payload=self._report_payload(
                safety_id=safety_id,
                safety_type=safety_type,
                statuses=statuses,
                risks=risks,
                reasons=reasons,
            ),
            governance_history=tuple(self._history(request)),
            safety_lifecycle=(
                self._lifecycle("governance_safety_detection_completed"),
                self._lifecycle("governance_safety_validation_completed"),
                self._lifecycle(status),
            ),
            risks=tuple(self._risk_list(request, statuses, reasons)),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons),
            error=error,
            metadata=dict(request.metadata),
        )

    def _safety_type(
        self,
        request: GovernanceSafetyRequest,
        escalation: dict[str, Any],
        execution_block: dict[str, Any],
    ) -> str | None:
        explicit = self._normalize(request.safety_type)
        if explicit:
            return explicit
        escalation_type = self._normalize(escalation.get("escalation_type"))
        if escalation_type in SUPPORTED_SAFETY_TYPES:
            return escalation_type
        block_type = self._normalize(execution_block.get("block_type"))
        if block_type in SUPPORTED_SAFETY_TYPES:
            return block_type
        return SAFETY_TYPE_GOVERNANCE

    def _statuses(
        self,
        request: GovernanceSafetyRequest,
        governance: dict[str, Any],
        approval: dict[str, Any],
        escalation: dict[str, Any],
        execution_block: dict[str, Any],
        continuation: dict[str, Any],
    ) -> dict[str, Any]:
        execution_context = {}
        execution_context.update(governance.get("execution_context") or {})
        execution_context.update(escalation.get("execution_context") or {})
        execution_context.update(execution_block.get("execution_context") or {})
        execution_context.update(request.execution_context or {})
        return {
            "execution_id": request.execution_id
            or execution_context.get("execution_id")
            or approval.get("execution_id")
            or escalation.get("execution_id")
            or execution_block.get("execution_id"),
            "task_id": request.task_id
            or execution_context.get("task_id")
            or approval.get("task_id")
            or execution_block.get("task_id"),
            "authority_source": request.authority_source
            or governance.get("authority_source")
            or approval.get("authority_source"),
            "execution_context": execution_context,
            "authority_status": self._normalize(request.authority_status)
            or governance.get("authority_level"),
            "governance_status": self._normalize(
                request.governance_status
                or governance.get("governance_status")
                or governance.get("status")
                or escalation.get("governance_status")
            ),
            "approval_status": self._normalize(
                request.approval_status
                or approval.get("approval_status")
                or approval.get("status")
                or escalation.get("approval_status")
            ),
            "audit_status": self._normalize(
                request.audit_status
                or escalation.get("audit_status")
                or continuation.get("audit_status")
            ),
            "security_status": self._normalize(
                request.security_status
                or governance.get("security_status")
                or approval.get("security_status")
                or escalation.get("security_status")
                or continuation.get("security_status")
            ),
            "runtime_status": self._normalize(
                request.runtime_status
                or escalation.get("runtime_status")
                or execution_block.get("runtime_state", {}).get("status")
            ),
            "blocking_status": self._normalize(
                request.blocking_status
                or governance.get("blocking_status")
                or approval.get("blocking_status")
                or escalation.get("blocking_status")
                or execution_block.get("block_status")
            ),
            "continuation_status": self._normalize(
                request.continuation_status
                or escalation.get("continuation_status")
                or execution_block.get("continuation_status")
                or continuation.get("continuation_status")
            ),
            "risk_level": self._normalize(
                request.risk_level
                or escalation.get("risk_level")
                or execution_block.get("risk_level")
            ),
        }

    def _risk_flags(
        self,
        request: GovernanceSafetyRequest,
        governance: dict[str, Any],
        approval: dict[str, Any],
        escalation: dict[str, Any],
        execution_block: dict[str, Any],
        continuation: dict[str, Any],
        statuses: dict[str, Any],
        runtime_active: bool,
    ) -> dict[str, bool]:
        human_authority = bool(
            request.authority_override_requested
            or request.alter_authorities_requested
            or approval.get("no_self_approval") is False
            or approval.get("human_authority_preserved") is False
        )
        governance_risk = bool(
            request.governance_redefinition_requested
            or request.autonomy_expansion_requested
            or statuses["governance_status"] in BLOCKING_STATUSES
            or governance.get("reasons")
            or escalation.get("governance_conflict_detected")
        )
        audit_risk = bool(
            request.invalidate_audit_requested
            or statuses["audit_status"] in {"rejected", "needs_fix", "blocked"}
        )
        security_risk = bool(
            request.ignore_security_escalation_requested
            or statuses["security_status"] in BLOCKING_STATUSES
            or escalation.get("security_escalation_detected")
        )
        execution_risk = bool(
            request.unsafe_execution_requested
            or not runtime_active
            or statuses["runtime_status"] not in {None, *SAFE_RUNTIME_STATUSES}
            or execution_block.get("runtime_corruption_detected")
            or execution_block.get("execution_inconsistency_detected")
        )
        continuation_risk = bool(
            request.continuation_override_requested
            or continuation.get("continuation_allowed") is False
            or execution_block.get("continuation_blocked")
            or statuses["continuation_status"]
            in {
                "unsafe",
                "blocked",
                "blocked_unsafe_continuation",
                "blocked_security_authority",
                "blocked_approval_authority",
                "blocked_governance_authority",
            }
        )
        blocking = statuses["blocking_status"] in BLOCKING_STATUSES
        if request.ignore_critical_block_requested or blocking:
            execution_risk = True
        return {
            "human_authority": human_authority,
            "governance": governance_risk,
            "audit": audit_risk,
            "security": security_risk,
            "execution": execution_risk,
            "continuation": continuation_risk,
            "blocking": blocking,
            "dishonest": bool(
                request.conceal_conflicts_requested
                or request.minimize_risk_requested
                or request.falsify_governance_status_requested
            ),
        }

    def _validation_reasons(
        self,
        request: GovernanceSafetyRequest,
        safety_type: str | None,
        risks: dict[str, bool],
        statuses: dict[str, Any],
        runtime_active: bool,
        safety_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not safety_permitted:
            reasons.append("governance_safety_not_permitted")
        if safety_type not in SUPPORTED_SAFETY_TYPES:
            reasons.append("unsupported_governance_safety_type")
        if not statuses["execution_id"]:
            reasons.append("missing_execution_context")
        if risks["human_authority"]:
            reasons.append("human_authority_preserved")
        if risks["governance"]:
            reasons.append("governance_integrity_required")
        if risks["audit"]:
            reasons.append("audit_authority_required")
        if risks["security"]:
            reasons.append("security_authority_required")
        if risks["execution"]:
            reasons.append("execution_safety_required")
        if risks["continuation"]:
            reasons.append("continuation_safety_required")
        if risks["blocking"]:
            reasons.append("critical_blocking_preserved")
        if risks["dishonest"]:
            reasons.append("honest_governance_required")
        return self._unique(reasons)

    def _reporting_authority(
        self,
        safety_type: str | None,
        statuses: dict[str, Any],
    ) -> str:
        if safety_type == SAFETY_TYPE_SECURITY:
            return "CENTINELA"
        if safety_type == SAFETY_TYPE_AUDIT:
            return "SENTINEL"
        if safety_type in {SAFETY_TYPE_HUMAN_AUTHORITY, SAFETY_TYPE_GOVERNANCE}:
            return "CEO"
        return statuses["authority_source"] or "CEREBRO"

    def _report_payload(
        self,
        safety_id: str,
        safety_type: str | None,
        statuses: dict[str, Any],
        risks: dict[str, bool],
        reasons: list[str],
    ) -> dict[str, Any]:
        return {
            "safety_id": safety_id,
            "safety_type": safety_type,
            "reporting_authority": self._reporting_authority(
                safety_type,
                statuses,
            ),
            "execution_context": dict(statuses["execution_context"]),
            "authority_status": statuses["authority_status"],
            "governance_status": statuses["governance_status"],
            "approval_status": statuses["approval_status"],
            "audit_status": statuses["audit_status"],
            "security_status": statuses["security_status"],
            "runtime_status": statuses["runtime_status"],
            "blocking_status": statuses["blocking_status"],
            "continuation_status": statuses["continuation_status"],
            "risk_level": statuses["risk_level"],
            "risks": dict(risks),
            "blocked_reasons": list(reasons),
        }

    def _risk_list(
        self,
        request: GovernanceSafetyRequest,
        statuses: dict[str, Any],
        reasons: list[str],
    ) -> list[str]:
        return self._unique(
            [
                *[str(item) for item in request.risks],
                *[str(item) for item in reasons],
                str(statuses["risk_level"] or ""),
            ]
        )

    def _history(self, request: GovernanceSafetyRequest) -> list[dict[str, Any]]:
        return [self._as_dict(entry) for entry in request.governance_history]

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
                GovernanceEscalationResult,
                ExecutionBlockResult,
                ContinuationSafetyResult,
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
        safety_id: str,
        request: GovernanceSafetyRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> GovernanceSafetyResult:
        finished_at = datetime.now(timezone.utc)
        return GovernanceSafetyResult(
            status=GOVERNANCE_SAFETY_STATUS_ERROR,
            success=False,
            safety_id=safety_id,
            safety_type=self._normalize(request.safety_type),
            safety_status=GOVERNANCE_SAFETY_STATUS_ERROR,
            execution_id=request.execution_id,
            task_id=request.task_id,
            authority_source=request.authority_source,
            reporting_authority=request.authority_source or "CEREBRO",
            execution_context=dict(request.execution_context),
            authority_status=self._normalize(request.authority_status),
            governance_status=self._normalize(request.governance_status),
            approval_status=self._normalize(request.approval_status),
            audit_status=self._normalize(request.audit_status),
            security_status=self._normalize(request.security_status),
            runtime_status=self._normalize(request.runtime_status),
            blocking_status=self._normalize(request.blocking_status),
            continuation_status=self._normalize(request.continuation_status),
            risk_level=self._normalize(request.risk_level),
            execution_allowed=False,
            continuation_allowed=False,
            human_authority_preserved=False,
            autonomy_limited=True,
            governance_integrity_preserved=False,
            audit_respected=False,
            security_respected=False,
            blocking_respected=False,
            runtime_stability_preserved=False,
            ecosystem_coherence_preserved=False,
            operational_transparency_preserved=False,
            traceability_preserved=True,
            human_authority_risk_detected=False,
            governance_risk_detected=False,
            audit_risk_detected=False,
            security_risk_detected=False,
            execution_risk_detected=False,
            continuation_risk_detected=False,
            escalation_required=True,
            safety_lifecycle=(self._lifecycle(GOVERNANCE_SAFETY_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("governance_safety_error_contained",),
            error=error,
            metadata=dict(request.metadata),
        )

    def _publish(self, result: GovernanceSafetyResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_governance_safety_result",
        ):
            self.status.mark_governance_safety_result(result.to_dict())

    def _log_result(self, result: GovernanceSafetyResult) -> None:
        if result.status == GOVERNANCE_SAFETY_STATUS_ERROR:
            logger.error(
                "governance_safety: error safety_id=%s error=%s",
                result.safety_id,
                result.error,
            )
            return
        if result.status == GOVERNANCE_SAFETY_STATUS_BLOCKED:
            logger.warning(
                "governance_safety: blocked safety_id=%s reasons=%s",
                result.safety_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "governance_safety: safe safety_id=%s type=%s",
            result.safety_id,
            result.safety_type,
        )
