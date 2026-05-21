"""
Governance foundation for Hermes runtime.

This layer validates official governance context before execution workflows.
It preserves human authority, approval integrity, security blocking, and
ecosystem hierarchy without executing tasks or changing runtime behavior.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.ecosystem_registry import EcosystemRegistry

logger = logging.getLogger(__name__)

GOVERNANCE_TYPE_EXECUTION = "execution"
GOVERNANCE_TYPE_APPROVAL = "approval"
GOVERNANCE_TYPE_AUDIT = "audit"
GOVERNANCE_TYPE_SECURITY = "security"
GOVERNANCE_TYPE_CONTINUATION = "continuation"
GOVERNANCE_TYPE_ECOSYSTEM = "ecosystem"

SUPPORTED_GOVERNANCE_TYPES = {
    GOVERNANCE_TYPE_EXECUTION,
    GOVERNANCE_TYPE_APPROVAL,
    GOVERNANCE_TYPE_AUDIT,
    GOVERNANCE_TYPE_SECURITY,
    GOVERNANCE_TYPE_CONTINUATION,
    GOVERNANCE_TYPE_ECOSYSTEM,
}

GOVERNANCE_STATUS_VALIDATED = "validated"
GOVERNANCE_STATUS_BLOCKED = "blocked"
GOVERNANCE_STATUS_ERROR = "error"

APPROVED_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "authorized_by_human",
    "governance_approved",
}
APPROVED_APPROVAL_STATUSES = {
    "approved",
    "approved_with_restrictions",
    "human_approved",
    "authorized",
    "authorized_by_human",
    "conditional_approval",
    "approval_granted",
}
BLOCKING_STATUSES = {
    "blocked",
    "critical_blocked",
    "critical_blocking",
    "quarantine",
    "halted",
    "stopped",
}
SECURITY_RESTRICTED_STATUSES = {
    "blocked",
    "critical",
    "critical_blocking",
    "escalated",
    "quarantine",
}


@dataclass(frozen=True)
class GovernanceFoundationRequest:
    governance_id: str | None = None
    authority_source: str | None = None
    governance_type: str = GOVERNANCE_TYPE_EXECUTION
    execution_context: dict[str, Any] = field(default_factory=dict)
    governance_status: str | None = None
    approval_status: str | None = None
    security_status: str | None = None
    blocking_status: str | None = None
    audit_status: str | None = None
    operational_status: str | None = None
    approval_required: bool = False
    security_escalation_active: bool = False
    critical_blocking_active: bool = False
    authority_override_requested: bool = False
    alter_authorities_requested: bool = False
    approval_bypass_requested: bool = False
    ignore_audit_requested: bool = False
    autonomy_expansion_requested: bool = False
    invalidate_blocking_requested: bool = False
    conceal_conflicts_requested: bool = False
    minimize_risks_requested: bool = False
    falsify_approval_requested: bool = False
    risks: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GovernanceFoundationResult:
    status: str
    success: bool
    governance_id: str
    authority_source: str | None
    authority_level: str | None
    governance_type: str | None
    execution_context: dict[str, Any]
    governance_status: str | None
    approval_status: str | None
    security_status: str | None
    blocking_status: str | None
    audit_status: str | None
    operational_status: str | None
    authority_identified: bool
    authority_legitimate: bool
    human_authority_preserved: bool
    execution_limits_preserved: bool
    runtime_protected: bool
    audit_security_respected: bool
    approval_required: bool
    approval_satisfied: bool
    security_escalation_required: bool
    blocking_active: bool
    execution_permitted: bool
    governance_transparency_preserved: bool
    traceability_preserved: bool
    reporting_target: str | None
    active_authorities: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    governance_rules: tuple[str, ...] = field(default_factory=tuple)
    report_payload: dict[str, Any] = field(default_factory=dict)
    governance_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "governance_id": self.governance_id,
            "authority_source": self.authority_source,
            "authority_level": self.authority_level,
            "governance_type": self.governance_type,
            "execution_context": dict(self.execution_context),
            "governance_status": self.governance_status,
            "approval_status": self.approval_status,
            "security_status": self.security_status,
            "blocking_status": self.blocking_status,
            "audit_status": self.audit_status,
            "operational_status": self.operational_status,
            "authority_identified": self.authority_identified,
            "authority_legitimate": self.authority_legitimate,
            "human_authority_preserved": self.human_authority_preserved,
            "execution_limits_preserved": self.execution_limits_preserved,
            "runtime_protected": self.runtime_protected,
            "audit_security_respected": self.audit_security_respected,
            "approval_required": self.approval_required,
            "approval_satisfied": self.approval_satisfied,
            "security_escalation_required": self.security_escalation_required,
            "blocking_active": self.blocking_active,
            "execution_permitted": self.execution_permitted,
            "governance_transparency_preserved": (
                self.governance_transparency_preserved
            ),
            "traceability_preserved": self.traceability_preserved,
            "reporting_target": self.reporting_target,
            "active_authorities": [
                dict(authority) for authority in self.active_authorities
            ],
            "governance_rules": list(self.governance_rules),
            "report_payload": dict(self.report_payload),
            "governance_lifecycle": [
                dict(entry) for entry in self.governance_lifecycle
            ],
            "risks": list(self.risks),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class GovernanceFoundation:
    def __init__(
        self,
        status: Any | None = None,
        registry: EcosystemRegistry | None = None,
    ) -> None:
        self.status = status
        self.registry = registry or EcosystemRegistry()

    def validate(
        self,
        request: GovernanceFoundationRequest,
        governance_permitted: bool = True,
    ) -> GovernanceFoundationResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        governance_id = request.governance_id or str(uuid4())

        try:
            authority = self.registry.get_system(request.authority_source)
            governance_type = self._normalize(request.governance_type)
            reasons = self._validation_reasons(
                request=request,
                authority=authority,
                governance_type=governance_type,
                governance_permitted=governance_permitted,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    GOVERNANCE_STATUS_BLOCKED
                    if blocked
                    else GOVERNANCE_STATUS_VALIDATED
                ),
                success=not blocked,
                governance_id=governance_id,
                request=request,
                authority=authority,
                governance_type=governance_type,
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
                governance_id=governance_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def assess(
        self,
        request: GovernanceFoundationRequest,
        governance_permitted: bool = True,
    ) -> GovernanceFoundationResult:
        return self.validate(
            request,
            governance_permitted=governance_permitted,
        )

    def _result(
        self,
        status: str,
        success: bool,
        governance_id: str,
        request: GovernanceFoundationRequest,
        authority: Any | None,
        governance_type: str | None,
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> GovernanceFoundationResult:
        finished_at = datetime.now(timezone.utc)
        authority_source = authority.system_id if authority else request.authority_source
        reporting_target = self._reporting_target(request, authority, reasons)
        approval_satisfied = self._approval_satisfied(request)
        blocking_active = self._blocking_active(request)
        security_escalation_required = self._security_escalation_required(request)
        report_payload = self._report_payload(
            governance_id=governance_id,
            request=request,
            authority_source=authority_source,
            governance_type=governance_type,
            reporting_target=reporting_target,
            reasons=reasons,
        )
        return GovernanceFoundationResult(
            status=status,
            success=success,
            governance_id=governance_id,
            authority_source=authority_source,
            authority_level=authority.authority_level if authority else None,
            governance_type=governance_type,
            execution_context=dict(request.execution_context),
            governance_status=self._normalize(request.governance_status),
            approval_status=self._normalize(request.approval_status),
            security_status=self._normalize(request.security_status),
            blocking_status=self._normalize(request.blocking_status),
            audit_status=self._normalize(request.audit_status),
            operational_status=self._normalize(request.operational_status),
            authority_identified=authority is not None,
            authority_legitimate=self._authority_can_govern(
                authority,
                governance_type,
            ),
            human_authority_preserved=self._human_authority_preserved(request),
            execution_limits_preserved=not request.autonomy_expansion_requested,
            runtime_protected=not request.invalidate_blocking_requested,
            audit_security_respected=not (
                request.ignore_audit_requested
                or request.invalidate_blocking_requested
            ),
            approval_required=request.approval_required,
            approval_satisfied=approval_satisfied,
            security_escalation_required=security_escalation_required,
            blocking_active=blocking_active,
            execution_permitted=success,
            governance_transparency_preserved=not (
                request.conceal_conflicts_requested
                or request.minimize_risks_requested
                or request.falsify_approval_requested
            ),
            traceability_preserved=True,
            reporting_target=reporting_target,
            active_authorities=tuple(self._active_authorities()),
            governance_rules=tuple(self._governance_rules()),
            report_payload=report_payload,
            governance_lifecycle=(
                self._lifecycle("governance_identification_completed"),
                self._lifecycle("governance_validation_completed"),
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
        request: GovernanceFoundationRequest,
        authority: Any | None,
        governance_type: str | None,
        governance_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not governance_permitted:
            reasons.append("governance_not_permitted")
        if authority is None:
            reasons.append("unknown_authority_source")
        if governance_type not in SUPPORTED_GOVERNANCE_TYPES:
            reasons.append("unsupported_governance_type")
        if not self._authority_can_govern(authority, governance_type):
            reasons.append("authority_scope_not_allowed")
        if request.authority_override_requested or request.alter_authorities_requested:
            reasons.append("authority_override_blocked")
        if request.autonomy_expansion_requested:
            reasons.append("autonomy_expansion_blocked")
        if request.approval_bypass_requested or request.falsify_approval_requested:
            reasons.append("approval_integrity_violation")
        if request.ignore_audit_requested:
            reasons.append("audit_governance_required")
        if request.invalidate_blocking_requested:
            reasons.append("critical_blocking_preserved")
        if (
            request.conceal_conflicts_requested
            or request.minimize_risks_requested
            or request.falsify_approval_requested
        ):
            reasons.append("dishonest_governance_blocked")
        if request.approval_required and not self._approval_satisfied(request):
            reasons.append("approval_required")
        if self._security_escalation_required(request):
            reasons.append("security_escalation_required")
        if self._blocking_active(request):
            reasons.append("blocking_condition_active")
        if self._governance_rejected(request):
            reasons.append("governance_status_blocked")
        return self._unique(reasons)

    def _authority_can_govern(
        self,
        authority: Any | None,
        governance_type: str | None,
    ) -> bool:
        if authority is None or governance_type is None:
            return False
        source = authority.system_id
        if source == "CEO":
            return True
        if source == "CEREBRO":
            return governance_type in {
                GOVERNANCE_TYPE_EXECUTION,
                GOVERNANCE_TYPE_APPROVAL,
                GOVERNANCE_TYPE_CONTINUATION,
                GOVERNANCE_TYPE_ECOSYSTEM,
            }
        if source == "HERMES":
            return governance_type in {
                GOVERNANCE_TYPE_EXECUTION,
                GOVERNANCE_TYPE_CONTINUATION,
            }
        if source == "SENTINEL":
            return governance_type == GOVERNANCE_TYPE_AUDIT
        if source == "CENTINELA":
            return governance_type == GOVERNANCE_TYPE_SECURITY
        return False

    def _approval_satisfied(self, request: GovernanceFoundationRequest) -> bool:
        if not request.approval_required:
            return True
        return self._normalize(request.approval_status) in APPROVED_APPROVAL_STATUSES

    def _security_escalation_required(
        self,
        request: GovernanceFoundationRequest,
    ) -> bool:
        security_status = self._normalize(request.security_status)
        return (
            request.security_escalation_active
            or security_status in SECURITY_RESTRICTED_STATUSES
        )

    def _blocking_active(self, request: GovernanceFoundationRequest) -> bool:
        blocking_status = self._normalize(request.blocking_status)
        return request.critical_blocking_active or blocking_status in BLOCKING_STATUSES

    def _governance_rejected(self, request: GovernanceFoundationRequest) -> bool:
        return self._normalize(request.governance_status) in {
            "blocked",
            "rejected",
            "revoked",
        }

    def _human_authority_preserved(
        self,
        request: GovernanceFoundationRequest,
    ) -> bool:
        return not (
            request.authority_override_requested
            or request.alter_authorities_requested
            or request.autonomy_expansion_requested
            or request.approval_bypass_requested
            or request.falsify_approval_requested
        )

    def _reporting_target(
        self,
        request: GovernanceFoundationRequest,
        authority: Any | None,
        reasons: list[str],
    ) -> str | None:
        if (
            "security_escalation_required" in reasons
            or "blocking_condition_active" in reasons
        ):
            return "CENTINELA"
        if "audit_governance_required" in reasons:
            return "SENTINEL"
        if authority and authority.system_id == "CEO":
            return "CEO"
        if authority and authority.reports_to:
            return authority.reports_to
        return request.authority_source or "CEREBRO"

    def _report_payload(
        self,
        governance_id: str,
        request: GovernanceFoundationRequest,
        authority_source: str | None,
        governance_type: str | None,
        reporting_target: str | None,
        reasons: list[str],
    ) -> dict[str, Any]:
        return {
            "governance_id": governance_id,
            "authority_source": authority_source,
            "governance_type": governance_type,
            "reporting_target": reporting_target,
            "execution_context": dict(request.execution_context),
            "governance_status": self._normalize(request.governance_status),
            "approval_status": self._normalize(request.approval_status),
            "security_status": self._normalize(request.security_status),
            "blocking_status": self._normalize(request.blocking_status),
            "audit_status": self._normalize(request.audit_status),
            "operational_status": self._normalize(request.operational_status),
            "risks": list(request.risks),
            "blocked_reasons": list(reasons),
        }

    def _active_authorities(self) -> list[dict[str, Any]]:
        snapshot = self.registry.snapshot()
        return [dict(authority) for authority in snapshot.active_authorities]

    def _governance_rules(self) -> list[str]:
        return [
            "human_authority_is_final",
            "no_governance_override",
            "approval_integrity_required",
            "security_blocking_is_preserved",
            "audit_and_security_are_respected",
            "honest_governance_reporting",
        ]

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
        governance_id: str,
        request: GovernanceFoundationRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> GovernanceFoundationResult:
        finished_at = datetime.now(timezone.utc)
        return GovernanceFoundationResult(
            status=GOVERNANCE_STATUS_ERROR,
            success=False,
            governance_id=governance_id,
            authority_source=request.authority_source,
            authority_level=None,
            governance_type=self._normalize(request.governance_type),
            execution_context=dict(request.execution_context),
            governance_status=self._normalize(request.governance_status),
            approval_status=self._normalize(request.approval_status),
            security_status=self._normalize(request.security_status),
            blocking_status=self._normalize(request.blocking_status),
            audit_status=self._normalize(request.audit_status),
            operational_status=self._normalize(request.operational_status),
            authority_identified=False,
            authority_legitimate=False,
            human_authority_preserved=False,
            execution_limits_preserved=False,
            runtime_protected=False,
            audit_security_respected=False,
            approval_required=request.approval_required,
            approval_satisfied=False,
            security_escalation_required=False,
            blocking_active=False,
            execution_permitted=False,
            governance_transparency_preserved=False,
            traceability_preserved=True,
            reporting_target="CEREBRO",
            governance_rules=tuple(self._governance_rules()),
            governance_lifecycle=(self._lifecycle(GOVERNANCE_STATUS_ERROR),),
            risks=tuple(request.risks),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("governance_foundation_error_contained",),
            error=error,
            metadata=dict(request.metadata),
        )

    def _publish(self, result: GovernanceFoundationResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_governance_foundation_result",
        ):
            self.status.mark_governance_foundation_result(result.to_dict())

    def _log_result(self, result: GovernanceFoundationResult) -> None:
        if result.status == GOVERNANCE_STATUS_ERROR:
            logger.error(
                "governance_foundation: error governance_id=%s error=%s",
                result.governance_id,
                result.error,
            )
            return
        if result.status == GOVERNANCE_STATUS_BLOCKED:
            logger.warning(
                "governance_foundation: blocked governance_id=%s reasons=%s",
                result.governance_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "governance_foundation: %s governance_id=%s authority=%s",
            result.status,
            result.governance_id,
            result.authority_source,
        )
