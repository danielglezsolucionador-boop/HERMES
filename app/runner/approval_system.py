"""
Operational approval validation system for Hermes runtime.

This layer validates official approvals before critical workflow continuation.
It does not create approvals, auto-approve work, execute tasks, or replace the
existing human approval gate.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.ecosystem_registry import EcosystemRegistry
from app.runner.governance_foundation import (
    GovernanceFoundation,
    GovernanceFoundationRequest,
)

logger = logging.getLogger(__name__)

APPROVAL_TYPE_CEO = "ceo"
APPROVAL_TYPE_CEREBRO = "cerebro"
APPROVAL_TYPE_AUDIT = "audit"
APPROVAL_TYPE_SECURITY = "security"
SUPPORTED_APPROVAL_TYPES = {
    APPROVAL_TYPE_CEO,
    APPROVAL_TYPE_CEREBRO,
    APPROVAL_TYPE_AUDIT,
    APPROVAL_TYPE_SECURITY,
}

APPROVAL_SYSTEM_STATUS_APPROVED = "approved"
APPROVAL_SYSTEM_STATUS_CONDITIONAL = "conditional_approval"
APPROVAL_SYSTEM_STATUS_REJECTED = "rejected"
APPROVAL_SYSTEM_STATUS_ESCALATION_REQUIRED = "escalation_required"
APPROVAL_SYSTEM_STATUS_BLOCKED = "blocked"
APPROVAL_SYSTEM_STATUS_ERROR = "error"

APPROVED_APPROVAL_STATUSES = {
    "approved",
    "approval_granted",
    "authorized",
    "authorized_by_human",
    "human_approved",
}
CONDITIONAL_APPROVAL_STATUSES = {
    "conditional",
    "conditional_approval",
    "approved_with_restrictions",
}
REJECTED_APPROVAL_STATUSES = {
    "denied",
    "human_rejected",
    "rejected",
}
ESCALATION_APPROVAL_STATUSES = {
    "escalated",
    "escalation_required",
    "requires_escalation",
}
PENDING_APPROVAL_STATUSES = {
    "pending",
    "requested",
    "waiting",
    "waiting_human_authority",
}
BLOCKING_STATUSES = {
    "blocked",
    "critical_blocked",
    "critical_blocking",
    "quarantine",
}
SECURITY_RESTRICTED_STATUSES = {
    "blocked",
    "critical",
    "critical_blocking",
    "escalated",
    "quarantine",
}


@dataclass(frozen=True)
class ApprovalSystemRequest:
    approval_id: str | None = None
    authority_source: str | None = None
    approval_type: str | None = None
    approval_status: str | None = None
    workflow_id: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    execution_context: dict[str, Any] = field(default_factory=dict)
    governance_status: str | None = None
    security_status: str | None = None
    audit_status: str | None = None
    blocking_status: str | None = None
    critical_workflow: bool = False
    architecture_change: bool = False
    ecosystem_change: bool = False
    governance_expansion: bool = False
    continuation_requested: bool = False
    orchestration_requested: bool = False
    audit_required: bool = False
    security_sensitive: bool = False
    quarantine_release_requested: bool = False
    approval_record: dict[str, Any] | Any | None = None
    approval_restrictions: tuple[str, ...] = field(default_factory=tuple)
    self_approval_requested: bool = False
    create_fake_approval_requested: bool = False
    modify_official_approval_requested: bool = False
    falsify_approval_status_requested: bool = False
    assume_permission_requested: bool = False
    ignore_rejection_requested: bool = False
    ignore_blocking_requested: bool = False
    conceal_missing_approval_requested: bool = False
    minimize_governance_conflicts_requested: bool = False
    risks: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ApprovalSystemResult:
    status: str
    success: bool
    approval_id: str
    authority_source: str | None
    authority_level: str | None
    approval_type: str | None
    required_approval_type: str
    approval_status: str | None
    execution_decision: str
    execution_permitted: bool
    conditional_approval: bool
    approval_restrictions: tuple[str, ...]
    workflow_id: str | None
    execution_id: str | None
    task_id: str | None
    execution_context: dict[str, Any]
    governance_status: str | None
    security_status: str | None
    audit_status: str | None
    blocking_status: str | None
    approval_exists: bool
    approval_legitimate: bool
    authority_legitimate: bool
    human_authority_preserved: bool
    no_self_approval: bool
    governance_compatible: bool
    audit_permission_valid: bool
    security_permission_valid: bool
    blocking_active: bool
    escalation_required: bool
    critical_workflow: bool
    security_sensitive: bool
    approval_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    governance_foundation: dict[str, Any] = field(default_factory=dict)
    report_payload: dict[str, Any] = field(default_factory=dict)
    approval_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "approval_id": self.approval_id,
            "authority_source": self.authority_source,
            "authority_level": self.authority_level,
            "approval_type": self.approval_type,
            "required_approval_type": self.required_approval_type,
            "approval_status": self.approval_status,
            "execution_decision": self.execution_decision,
            "execution_permitted": self.execution_permitted,
            "conditional_approval": self.conditional_approval,
            "approval_restrictions": list(self.approval_restrictions),
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "execution_context": dict(self.execution_context),
            "governance_status": self.governance_status,
            "security_status": self.security_status,
            "audit_status": self.audit_status,
            "blocking_status": self.blocking_status,
            "approval_exists": self.approval_exists,
            "approval_legitimate": self.approval_legitimate,
            "authority_legitimate": self.authority_legitimate,
            "human_authority_preserved": self.human_authority_preserved,
            "no_self_approval": self.no_self_approval,
            "governance_compatible": self.governance_compatible,
            "audit_permission_valid": self.audit_permission_valid,
            "security_permission_valid": self.security_permission_valid,
            "blocking_active": self.blocking_active,
            "escalation_required": self.escalation_required,
            "critical_workflow": self.critical_workflow,
            "security_sensitive": self.security_sensitive,
            "approval_history": [
                dict(entry) for entry in self.approval_history
            ],
            "governance_foundation": dict(self.governance_foundation),
            "report_payload": dict(self.report_payload),
            "approval_lifecycle": [
                dict(entry) for entry in self.approval_lifecycle
            ],
            "risks": list(self.risks),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class ApprovalSystem:
    def __init__(
        self,
        status: Any | None = None,
        registry: EcosystemRegistry | None = None,
        governance: GovernanceFoundation | None = None,
    ) -> None:
        self.status = status
        self.registry = registry or EcosystemRegistry()
        self.governance = governance or GovernanceFoundation(registry=self.registry)

    def validate(
        self,
        request: ApprovalSystemRequest,
        runtime_active: bool = True,
        approval_permitted: bool = True,
    ) -> ApprovalSystemResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)

        try:
            approval_record = self._approval_record(request.approval_record)
            approval_id = self._approval_id(request, approval_record)
            approval_id_present = self._approval_id_present(
                request,
                approval_record,
            )
            approval_status = self._approval_status(request, approval_record)
            authority_source = self._authority_source(request, approval_record)
            authority = self.registry.get_system(authority_source)
            required_type = self._required_approval_type(request, approval_record)
            approval_type = self._approval_type(request, approval_record) or required_type
            governance_result = self._governance_result(
                request=request,
                authority_source=authority_source,
                approval_status=approval_status,
                required_type=required_type,
            )
            reasons = self._validation_reasons(
                request=request,
                approval_id=approval_id,
                approval_id_present=approval_id_present,
                approval_status=approval_status,
                authority=authority,
                approval_type=approval_type,
                required_type=required_type,
                governance_result=governance_result,
                runtime_active=runtime_active,
                approval_permitted=approval_permitted,
            )
            status = self._status_from(
                approval_status=approval_status,
                reasons=reasons,
                restrictions=request.approval_restrictions,
            )
            success = status in {
                APPROVAL_SYSTEM_STATUS_APPROVED,
                APPROVAL_SYSTEM_STATUS_CONDITIONAL,
            }
            result = self._result(
                status=status,
                success=success,
                approval_id=approval_id,
                approval_id_present=approval_id_present,
                authority=authority,
                authority_source=authority_source,
                approval_type=approval_type,
                required_type=required_type,
                approval_status=approval_status,
                request=request,
                approval_record=approval_record,
                governance_result=governance_result,
                reasons=reasons,
                error=";".join(reasons) if not success else None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
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
        approval_id: str,
        approval_id_present: bool,
        authority: Any | None,
        authority_source: str | None,
        approval_type: str | None,
        required_type: str,
        approval_status: str | None,
        request: ApprovalSystemRequest,
        approval_record: dict[str, Any],
        governance_result: dict[str, Any],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> ApprovalSystemResult:
        finished_at = datetime.now(timezone.utc)
        conditional = status == APPROVAL_SYSTEM_STATUS_CONDITIONAL
        blocking_active = self._blocking_active(request)
        escalation_required = status == APPROVAL_SYSTEM_STATUS_ESCALATION_REQUIRED
        return ApprovalSystemResult(
            status=status,
            success=success,
            approval_id=approval_id,
            authority_source=authority.system_id if authority else authority_source,
            authority_level=authority.authority_level if authority else None,
            approval_type=approval_type,
            required_approval_type=required_type,
            approval_status=approval_status,
            execution_decision=status,
            execution_permitted=success and not blocking_active,
            conditional_approval=conditional,
            approval_restrictions=tuple(request.approval_restrictions),
            workflow_id=request.workflow_id,
            execution_id=request.execution_id or approval_record.get("execution_id"),
            task_id=request.task_id or approval_record.get("task_id"),
            execution_context=dict(request.execution_context),
            governance_status=self._normalize(request.governance_status),
            security_status=self._normalize(request.security_status),
            audit_status=self._normalize(request.audit_status),
            blocking_status=self._normalize(request.blocking_status),
            approval_exists=bool(approval_id_present and approval_status),
            approval_legitimate="approval_integrity_violation" not in reasons,
            authority_legitimate=self._authority_valid(authority, required_type),
            human_authority_preserved=self._human_authority_preserved(request),
            no_self_approval=not self._self_approval(request, authority),
            governance_compatible=not governance_result.get("reasons"),
            audit_permission_valid=(
                required_type != APPROVAL_TYPE_AUDIT
                or authority is not None
                and authority.system_id == "SENTINEL"
            ),
            security_permission_valid=(
                required_type != APPROVAL_TYPE_SECURITY
                or authority is not None
                and authority.system_id in {"CENTINELA", "CEO"}
            ),
            blocking_active=blocking_active,
            escalation_required=escalation_required,
            critical_workflow=self._critical_workflow(request),
            security_sensitive=self._security_sensitive(request),
            approval_history=tuple(self._approval_history(approval_record)),
            governance_foundation=governance_result,
            report_payload=self._report_payload(
                approval_id=approval_id,
                authority_source=authority_source,
                approval_type=approval_type,
                required_type=required_type,
                approval_status=approval_status,
                status=status,
                reasons=reasons,
                request=request,
            ),
            approval_lifecycle=(
                self._lifecycle("approval_requirement_detected"),
                self._lifecycle("approval_validation_completed"),
                self._lifecycle(status),
            ),
            risks=tuple(request.risks),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons),
            error=error,
            metadata=dict(request.metadata),
        )

    def _validation_reasons(
        self,
        request: ApprovalSystemRequest,
        approval_id: str,
        approval_id_present: bool,
        approval_status: str | None,
        authority: Any | None,
        approval_type: str | None,
        required_type: str,
        governance_result: dict[str, Any],
        runtime_active: bool,
        approval_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not approval_permitted:
            reasons.append("approval_validation_not_permitted")
        if required_type not in SUPPORTED_APPROVAL_TYPES:
            reasons.append("unsupported_approval_type")
        if approval_type != required_type:
            reasons.append(f"{required_type}_approval_required")
        if not approval_id_present:
            reasons.append("approval_missing")
        if not approval_status:
            reasons.append("approval_status_missing")
        if approval_status in PENDING_APPROVAL_STATUSES:
            reasons.append("approval_pending")
        if approval_status in REJECTED_APPROVAL_STATUSES:
            reasons.append("approval_rejected")
        if approval_status in ESCALATION_APPROVAL_STATUSES:
            reasons.append("approval_escalation_required")
        if conditional := approval_status in CONDITIONAL_APPROVAL_STATUSES:
            if not request.approval_restrictions:
                reasons.append("conditional_approval_restrictions_required")
        if authority is None:
            reasons.append("unknown_approval_authority")
        elif not self._authority_valid(authority, required_type):
            reasons.append("approval_authority_insufficient")
        if self._self_approval(request, authority):
            reasons.append("self_approval_blocked")
        if self._integrity_violation(request):
            reasons.append("approval_integrity_violation")
        if request.assume_permission_requested:
            reasons.append("assumed_permission_blocked")
        if request.ignore_rejection_requested:
            reasons.append("valid_rejection_preserved")
        if request.ignore_blocking_requested:
            reasons.append("critical_blocking_preserved")
        if (
            request.conceal_missing_approval_requested
            or request.minimize_governance_conflicts_requested
        ):
            reasons.append("dishonest_approval_reporting_blocked")
        if self._blocking_active(request):
            reasons.append("blocking_condition_active")
        if governance_result.get("reasons"):
            reasons.append("governance_foundation_blocked")
        return self._unique(reasons)

    def _status_from(
        self,
        approval_status: str | None,
        reasons: list[str],
        restrictions: tuple[str, ...],
    ) -> str:
        blocking_reasons = {
            "runtime_inactive",
            "approval_validation_not_permitted",
            "unsupported_approval_type",
            "unknown_approval_authority",
            "self_approval_blocked",
            "approval_integrity_violation",
            "assumed_permission_blocked",
            "valid_rejection_preserved",
            "critical_blocking_preserved",
            "dishonest_approval_reporting_blocked",
            "blocking_condition_active",
            "conditional_approval_restrictions_required",
        }
        escalation_reasons = {
            "approval_missing",
            "approval_status_missing",
            "approval_pending",
            "approval_authority_insufficient",
            "approval_escalation_required",
        }
        escalation_reasons.update(
            reason
            for reason in reasons
            if reason.endswith("_approval_required")
        )
        if any(reason in blocking_reasons for reason in reasons):
            return APPROVAL_SYSTEM_STATUS_BLOCKED
        if approval_status in REJECTED_APPROVAL_STATUSES:
            return APPROVAL_SYSTEM_STATUS_REJECTED
        if any(reason in escalation_reasons for reason in reasons):
            return APPROVAL_SYSTEM_STATUS_ESCALATION_REQUIRED
        if approval_status in CONDITIONAL_APPROVAL_STATUSES and restrictions:
            return APPROVAL_SYSTEM_STATUS_CONDITIONAL
        if approval_status in APPROVED_APPROVAL_STATUSES:
            return APPROVAL_SYSTEM_STATUS_APPROVED
        return APPROVAL_SYSTEM_STATUS_BLOCKED

    def _governance_result(
        self,
        request: ApprovalSystemRequest,
        authority_source: str | None,
        approval_status: str | None,
        required_type: str,
    ) -> dict[str, Any]:
        governance_type = {
            APPROVAL_TYPE_AUDIT: "audit",
            APPROVAL_TYPE_SECURITY: "security",
        }.get(required_type, "approval")
        result = self.governance.validate(
            GovernanceFoundationRequest(
                authority_source=authority_source,
                governance_type=governance_type,
                execution_context=request.execution_context,
                governance_status=request.governance_status,
                approval_required=True,
                approval_status=approval_status,
                security_status=request.security_status,
                blocking_status=request.blocking_status,
                audit_status=request.audit_status,
                critical_blocking_active=self._blocking_active(request),
                approval_bypass_requested=request.assume_permission_requested,
                authority_override_requested=False,
                falsify_approval_requested=(
                    request.falsify_approval_status_requested
                    or request.create_fake_approval_requested
                ),
                invalidate_blocking_requested=request.ignore_blocking_requested,
                conceal_conflicts_requested=(
                    request.conceal_missing_approval_requested
                ),
                minimize_risks_requested=(
                    request.minimize_governance_conflicts_requested
                ),
                risks=request.risks,
            )
        )
        return result.to_dict()

    def _approval_record(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return dict(result) if isinstance(result, dict) else {}
        return {}

    def _approval_id(
        self,
        request: ApprovalSystemRequest,
        approval_record: dict[str, Any],
    ) -> str:
        return (
            request.approval_id
            or approval_record.get("approval_id")
            or ""
        )

    def _approval_id_present(
        self,
        request: ApprovalSystemRequest,
        approval_record: dict[str, Any],
    ) -> bool:
        return bool(request.approval_id or approval_record.get("approval_id"))

    def _authority_source(
        self,
        request: ApprovalSystemRequest,
        approval_record: dict[str, Any],
    ) -> str | None:
        return (
            request.authority_source
            or approval_record.get("authority_source")
            or approval_record.get("decided_by")
        )

    def _approval_status(
        self,
        request: ApprovalSystemRequest,
        approval_record: dict[str, Any],
    ) -> str | None:
        value = (
            request.approval_status
            or approval_record.get("approval_status")
            or approval_record.get("status")
        )
        return self._normalize(value)

    def _approval_type(
        self,
        request: ApprovalSystemRequest,
        approval_record: dict[str, Any],
    ) -> str | None:
        value = request.approval_type or approval_record.get("approval_type")
        return self._normalize_approval_type(value)

    def _required_approval_type(
        self,
        request: ApprovalSystemRequest,
        approval_record: dict[str, Any],
    ) -> str:
        explicit = self._normalize_approval_type(
            request.approval_type or approval_record.get("approval_type")
        )
        if explicit in SUPPORTED_APPROVAL_TYPES:
            return explicit
        if (
            request.critical_workflow
            or request.architecture_change
            or request.ecosystem_change
            or request.governance_expansion
        ):
            return APPROVAL_TYPE_CEO
        if self._security_sensitive(request):
            return APPROVAL_TYPE_SECURITY
        if request.audit_required:
            return APPROVAL_TYPE_AUDIT
        return APPROVAL_TYPE_CEREBRO

    def _normalize_approval_type(self, value: Any) -> str | None:
        normalized = self._normalize(value)
        if normalized in {None, ""}:
            return None
        aliases = {
            "architecture": APPROVAL_TYPE_CEO,
            "ceo_approval": APPROVAL_TYPE_CEO,
            "critical": APPROVAL_TYPE_CEO,
            "ecosystem": APPROVAL_TYPE_CEO,
            "strategic": APPROVAL_TYPE_CEO,
            "cerebro_approval": APPROVAL_TYPE_CEREBRO,
            "continuation": APPROVAL_TYPE_CEREBRO,
            "coordination": APPROVAL_TYPE_CEREBRO,
            "execution": APPROVAL_TYPE_CEREBRO,
            "orchestration": APPROVAL_TYPE_CEREBRO,
            "audit_approval": APPROVAL_TYPE_AUDIT,
            "security_approval": APPROVAL_TYPE_SECURITY,
        }
        return aliases.get(normalized, normalized)

    def _authority_valid(self, authority: Any | None, required_type: str) -> bool:
        if authority is None:
            return False
        source = authority.system_id
        if required_type == APPROVAL_TYPE_CEO:
            return source == "CEO"
        if required_type == APPROVAL_TYPE_CEREBRO:
            return source in {"CEREBRO", "CEO"}
        if required_type == APPROVAL_TYPE_AUDIT:
            return source == "SENTINEL"
        if required_type == APPROVAL_TYPE_SECURITY:
            return source in {"CENTINELA", "CEO"}
        return False

    def _self_approval(
        self,
        request: ApprovalSystemRequest,
        authority: Any | None,
    ) -> bool:
        return request.self_approval_requested or (
            authority is not None and authority.system_id == "HERMES"
        )

    def _integrity_violation(self, request: ApprovalSystemRequest) -> bool:
        return (
            request.create_fake_approval_requested
            or request.modify_official_approval_requested
            or request.falsify_approval_status_requested
        )

    def _human_authority_preserved(
        self,
        request: ApprovalSystemRequest,
    ) -> bool:
        return not (
            request.self_approval_requested
            or request.create_fake_approval_requested
            or request.modify_official_approval_requested
            or request.falsify_approval_status_requested
            or request.assume_permission_requested
        )

    def _critical_workflow(self, request: ApprovalSystemRequest) -> bool:
        return (
            request.critical_workflow
            or request.architecture_change
            or request.ecosystem_change
            or request.governance_expansion
        )

    def _security_sensitive(self, request: ApprovalSystemRequest) -> bool:
        security_status = self._normalize(request.security_status)
        return (
            request.security_sensitive
            or request.quarantine_release_requested
            or security_status in SECURITY_RESTRICTED_STATUSES
        )

    def _blocking_active(self, request: ApprovalSystemRequest) -> bool:
        return self._normalize(request.blocking_status) in BLOCKING_STATUSES

    def _approval_history(
        self,
        approval_record: dict[str, Any],
    ) -> list[dict[str, Any]]:
        history = approval_record.get("approval_history") or []
        records = [
            dict(record) for record in history if isinstance(record, dict)
        ]
        if approval_record:
            records.append(
                {
                    "approval_id": approval_record.get("approval_id"),
                    "approval_status": approval_record.get("approval_status"),
                    "authority_source": approval_record.get("authority_source")
                    or approval_record.get("decided_by"),
                }
            )
        return records

    def _report_payload(
        self,
        approval_id: str,
        authority_source: str | None,
        approval_type: str | None,
        required_type: str,
        approval_status: str | None,
        status: str,
        reasons: list[str],
        request: ApprovalSystemRequest,
    ) -> dict[str, Any]:
        return {
            "approval_id": approval_id,
            "authority_source": authority_source,
            "approval_type": approval_type,
            "required_approval_type": required_type,
            "approval_status": approval_status,
            "execution_decision": status,
            "workflow_id": request.workflow_id,
            "execution_id": request.execution_id,
            "task_id": request.task_id,
            "governance_status": self._normalize(request.governance_status),
            "security_status": self._normalize(request.security_status),
            "audit_status": self._normalize(request.audit_status),
            "blocking_status": self._normalize(request.blocking_status),
            "risks": list(request.risks),
            "blocked_reasons": list(reasons),
        }

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
        request: ApprovalSystemRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> ApprovalSystemResult:
        finished_at = datetime.now(timezone.utc)
        approval_id = request.approval_id or str(uuid4())
        return ApprovalSystemResult(
            status=APPROVAL_SYSTEM_STATUS_ERROR,
            success=False,
            approval_id=approval_id,
            authority_source=request.authority_source,
            authority_level=None,
            approval_type=self._normalize_approval_type(request.approval_type),
            required_approval_type=self._required_approval_type(request, {}),
            approval_status=self._normalize(request.approval_status),
            execution_decision=APPROVAL_SYSTEM_STATUS_ERROR,
            execution_permitted=False,
            conditional_approval=False,
            approval_restrictions=tuple(request.approval_restrictions),
            workflow_id=request.workflow_id,
            execution_id=request.execution_id,
            task_id=request.task_id,
            execution_context=dict(request.execution_context),
            governance_status=self._normalize(request.governance_status),
            security_status=self._normalize(request.security_status),
            audit_status=self._normalize(request.audit_status),
            blocking_status=self._normalize(request.blocking_status),
            approval_exists=False,
            approval_legitimate=False,
            authority_legitimate=False,
            human_authority_preserved=False,
            no_self_approval=False,
            governance_compatible=False,
            audit_permission_valid=False,
            security_permission_valid=False,
            blocking_active=False,
            escalation_required=False,
            critical_workflow=self._critical_workflow(request),
            security_sensitive=self._security_sensitive(request),
            approval_lifecycle=(self._lifecycle(APPROVAL_SYSTEM_STATUS_ERROR),),
            risks=tuple(request.risks),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("approval_system_error_contained",),
            error=error,
            metadata=dict(request.metadata),
        )

    def _publish(self, result: ApprovalSystemResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_approval_system_result",
        ):
            self.status.mark_approval_system_result(result.to_dict())

    def _log_result(self, result: ApprovalSystemResult) -> None:
        if result.status == APPROVAL_SYSTEM_STATUS_ERROR:
            logger.error(
                "approval_system: error approval_id=%s error=%s",
                result.approval_id,
                result.error,
            )
            return
        if result.status in {
            APPROVAL_SYSTEM_STATUS_BLOCKED,
            APPROVAL_SYSTEM_STATUS_REJECTED,
            APPROVAL_SYSTEM_STATUS_ESCALATION_REQUIRED,
        }:
            logger.warning(
                "approval_system: %s approval_id=%s reasons=%s",
                result.status,
                result.approval_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "approval_system: %s approval_id=%s authority=%s",
            result.status,
            result.approval_id,
            result.authority_source,
        )
