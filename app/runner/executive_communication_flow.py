"""
Executive communication flow for Hermes runtime.

This layer validates operational communication between official authorities and
Hermes. It identifies the authority source, preserves execution context, and
prepares honest status reporting without coordinating other systems.
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

COMMUNICATION_TYPE_EXECUTION = "execution"
COMMUNICATION_TYPE_GOVERNANCE = "governance"
COMMUNICATION_TYPE_AUDIT = "audit"
COMMUNICATION_TYPE_SECURITY = "security"
SUPPORTED_COMMUNICATION_TYPES = {
    COMMUNICATION_TYPE_EXECUTION,
    COMMUNICATION_TYPE_GOVERNANCE,
    COMMUNICATION_TYPE_AUDIT,
    COMMUNICATION_TYPE_SECURITY,
}

COMMUNICATION_STATUS_ACCEPTED = "accepted"
COMMUNICATION_STATUS_REPORTED = "reported"
COMMUNICATION_STATUS_BLOCKED = "blocked"
COMMUNICATION_STATUS_ERROR = "error"

EXECUTIVE_AUTHORITIES = {"CEO", "CEREBRO"}
REPORT_AUTHORITIES = {"CEO", "CEREBRO", "SENTINEL", "CENTINELA"}


@dataclass(frozen=True)
class ExecutiveCommunicationRequest:
    communication_id: str | None = None
    authority_source: str | None = None
    communication_type: str = COMMUNICATION_TYPE_EXECUTION
    instruction_type: str | None = None
    execution_context: dict[str, Any] = field(default_factory=dict)
    governance_status: str | None = None
    report_status: str | None = None
    security_status: str | None = None
    operational_status: str | None = None
    audit_status: str | None = None
    blocking_status: str | None = None
    requested_response_target: str | None = None
    risks: tuple[str, ...] = field(default_factory=tuple)
    authority_override_requested: bool = False
    executive_orchestration_requested: bool = False
    distribute_work_requested: bool = False
    activate_superior_authority_requested: bool = False
    conceal_errors_requested: bool = False
    minimize_risks_requested: bool = False
    falsify_status_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutiveCommunicationResult:
    status: str
    success: bool
    communication_id: str
    authority_source: str | None
    authority_level: str | None
    communication_type: str | None
    instruction_type: str | None
    response_target: str | None
    execution_context: dict[str, Any]
    governance_status: str | None
    report_status: str
    security_status: str | None
    operational_status: str | None
    audit_status: str | None
    blocking_status: str | None
    authority_identified: bool
    response_target_valid: bool
    governance_preserved: bool
    security_integrity_preserved: bool
    audit_consistency_preserved: bool
    operational_continuity_preserved: bool
    execution_transparency_preserved: bool
    traceability_preserved: bool
    executive_orchestration_blocked: bool
    honest_reporting_preserved: bool
    report_payload: dict[str, Any] = field(default_factory=dict)
    risks: tuple[str, ...] = field(default_factory=tuple)
    communication_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "communication_id": self.communication_id,
            "authority_source": self.authority_source,
            "authority_level": self.authority_level,
            "communication_type": self.communication_type,
            "instruction_type": self.instruction_type,
            "response_target": self.response_target,
            "execution_context": dict(self.execution_context),
            "governance_status": self.governance_status,
            "report_status": self.report_status,
            "security_status": self.security_status,
            "operational_status": self.operational_status,
            "audit_status": self.audit_status,
            "blocking_status": self.blocking_status,
            "authority_identified": self.authority_identified,
            "response_target_valid": self.response_target_valid,
            "governance_preserved": self.governance_preserved,
            "security_integrity_preserved": self.security_integrity_preserved,
            "audit_consistency_preserved": self.audit_consistency_preserved,
            "operational_continuity_preserved": (
                self.operational_continuity_preserved
            ),
            "execution_transparency_preserved": (
                self.execution_transparency_preserved
            ),
            "traceability_preserved": self.traceability_preserved,
            "executive_orchestration_blocked": (
                self.executive_orchestration_blocked
            ),
            "honest_reporting_preserved": self.honest_reporting_preserved,
            "report_payload": dict(self.report_payload),
            "risks": list(self.risks),
            "communication_lifecycle": [
                dict(entry) for entry in self.communication_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class ExecutiveCommunicationFlow:
    def __init__(
        self,
        status: Any | None = None,
        registry: EcosystemRegistry | None = None,
    ) -> None:
        self.status = status
        self.registry = registry or EcosystemRegistry()

    def handle(
        self,
        request: ExecutiveCommunicationRequest,
        communication_permitted: bool = True,
    ) -> ExecutiveCommunicationResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        communication_id = request.communication_id or str(uuid4())

        try:
            authority = self.registry.get_system(request.authority_source)
            communication_type = self._normalize(request.communication_type)
            reasons = self._validation_reasons(
                request=request,
                authority=authority,
                communication_type=communication_type,
                communication_permitted=communication_permitted,
            )
            blocked = bool(reasons)
            report_payload = self._report_payload(request, authority, reasons)
            result = self._result(
                status=(
                    COMMUNICATION_STATUS_BLOCKED
                    if blocked
                    else COMMUNICATION_STATUS_REPORTED
                    if request.report_status
                    else COMMUNICATION_STATUS_ACCEPTED
                ),
                success=not blocked,
                communication_id=communication_id,
                request=request,
                authority=authority,
                communication_type=communication_type,
                report_payload=report_payload,
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
                communication_id=communication_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def route(
        self,
        request: ExecutiveCommunicationRequest,
        communication_permitted: bool = True,
    ) -> ExecutiveCommunicationResult:
        return self.handle(
            request,
            communication_permitted=communication_permitted,
        )

    def _result(
        self,
        status: str,
        success: bool,
        communication_id: str,
        request: ExecutiveCommunicationRequest,
        authority: Any | None,
        communication_type: str | None,
        report_payload: dict[str, Any],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> ExecutiveCommunicationResult:
        finished_at = datetime.now(timezone.utc)
        response_target = request.requested_response_target or request.authority_source
        return ExecutiveCommunicationResult(
            status=status,
            success=success,
            communication_id=communication_id,
            authority_source=authority.system_id if authority else request.authority_source,
            authority_level=authority.authority_level if authority else None,
            communication_type=communication_type,
            instruction_type=self._normalize(request.instruction_type),
            response_target=response_target,
            execution_context=dict(request.execution_context),
            governance_status=self._normalize(request.governance_status),
            report_status=(
                "blocked"
                if status == COMMUNICATION_STATUS_BLOCKED
                else request.report_status
                or "ready"
            ),
            security_status=self._normalize(request.security_status),
            operational_status=self._normalize(request.operational_status),
            audit_status=self._normalize(request.audit_status),
            blocking_status=self._normalize(request.blocking_status),
            authority_identified=authority is not None,
            response_target_valid=self._response_target_valid(request),
            governance_preserved=not request.authority_override_requested,
            security_integrity_preserved=not request.falsify_status_requested,
            audit_consistency_preserved=not request.conceal_errors_requested,
            operational_continuity_preserved=True,
            execution_transparency_preserved=not (
                request.conceal_errors_requested
                or request.minimize_risks_requested
                or request.falsify_status_requested
            ),
            traceability_preserved=True,
            executive_orchestration_blocked=True,
            honest_reporting_preserved=not (
                request.conceal_errors_requested
                or request.minimize_risks_requested
                or request.falsify_status_requested
            ),
            report_payload=report_payload,
            risks=tuple(request.risks),
            communication_lifecycle=(
                self._lifecycle("request_reception_completed"),
                self._lifecycle("authority_identification_completed"),
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
        request: ExecutiveCommunicationRequest,
        authority: Any | None,
        communication_type: str | None,
        communication_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not communication_permitted:
            reasons.append("executive_communication_not_permitted")
        if authority is None:
            reasons.append("unknown_authority_source")
        if communication_type not in SUPPORTED_COMMUNICATION_TYPES:
            reasons.append("unsupported_communication_type")
        if not self._authority_can_send(request, authority, communication_type):
            reasons.append("authority_scope_not_allowed")
        if not self._response_target_valid(request):
            reasons.append("response_redirection_blocked")
        if request.authority_override_requested:
            reasons.append("authority_override_blocked")
        if (
            request.executive_orchestration_requested
            or request.distribute_work_requested
            or request.activate_superior_authority_requested
        ):
            reasons.append("executive_orchestration_blocked")
        if (
            request.conceal_errors_requested
            or request.minimize_risks_requested
            or request.falsify_status_requested
        ):
            reasons.append("dishonest_reporting_blocked")
        return self._unique(reasons)

    def _authority_can_send(
        self,
        request: ExecutiveCommunicationRequest,
        authority: Any | None,
        communication_type: str | None,
    ) -> bool:
        if authority is None:
            return False
        source = authority.system_id
        instruction_type = self._normalize(request.instruction_type)
        if source in EXECUTIVE_AUTHORITIES:
            return True
        if communication_type == COMMUNICATION_TYPE_AUDIT and source == "SENTINEL":
            return instruction_type in {
                "status_request",
                "audit_context_request",
                "report_request",
            }
        if communication_type == COMMUNICATION_TYPE_SECURITY and source == "CENTINELA":
            return instruction_type in {
                "security_status_request",
                "incident_context_request",
                "report_request",
            }
        return False

    def _response_target_valid(self, request: ExecutiveCommunicationRequest) -> bool:
        if request.requested_response_target is None:
            return True
        return (
            self._normalize(request.requested_response_target)
            == self._normalize(request.authority_source)
        )

    def _report_payload(
        self,
        request: ExecutiveCommunicationRequest,
        authority: Any | None,
        reasons: list[str],
    ) -> dict[str, Any]:
        return {
            "authority_source": authority.system_id if authority else request.authority_source,
            "response_target": request.requested_response_target
            or request.authority_source,
            "execution_context": dict(request.execution_context),
            "governance_status": self._normalize(request.governance_status),
            "report_status": "blocked" if reasons else request.report_status or "ready",
            "security_status": self._normalize(request.security_status),
            "operational_status": self._normalize(request.operational_status),
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
        communication_id: str,
        request: ExecutiveCommunicationRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> ExecutiveCommunicationResult:
        finished_at = datetime.now(timezone.utc)
        return ExecutiveCommunicationResult(
            status=COMMUNICATION_STATUS_ERROR,
            success=False,
            communication_id=communication_id,
            authority_source=request.authority_source,
            authority_level=None,
            communication_type=self._normalize(request.communication_type),
            instruction_type=self._normalize(request.instruction_type),
            response_target=request.authority_source,
            execution_context=dict(request.execution_context),
            governance_status=self._normalize(request.governance_status),
            report_status="error",
            security_status=self._normalize(request.security_status),
            operational_status=self._normalize(request.operational_status),
            audit_status=self._normalize(request.audit_status),
            blocking_status=self._normalize(request.blocking_status),
            authority_identified=False,
            response_target_valid=False,
            governance_preserved=False,
            security_integrity_preserved=False,
            audit_consistency_preserved=False,
            operational_continuity_preserved=False,
            execution_transparency_preserved=False,
            traceability_preserved=True,
            executive_orchestration_blocked=True,
            honest_reporting_preserved=False,
            communication_lifecycle=(self._lifecycle(COMMUNICATION_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("executive_communication_error_contained",),
            error=error,
            metadata=dict(request.metadata),
        )

    def _publish(self, result: ExecutiveCommunicationResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_executive_communication_result",
        ):
            self.status.mark_executive_communication_result(result.to_dict())

    def _log_result(self, result: ExecutiveCommunicationResult) -> None:
        if result.status == COMMUNICATION_STATUS_ERROR:
            logger.error(
                "executive_communication: error communication_id=%s error=%s",
                result.communication_id,
                result.error,
            )
            return
        if result.status == COMMUNICATION_STATUS_BLOCKED:
            logger.warning(
                "executive_communication: blocked communication_id=%s reasons=%s",
                result.communication_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "executive_communication: %s communication_id=%s authority=%s",
            result.status,
            result.communication_id,
            result.authority_source,
        )
