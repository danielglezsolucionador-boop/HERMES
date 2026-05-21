"""
Controlled human approval gate for Hermes runtime.

This layer prepares human approval requests and records official human
decisions. It preserves governance and traceability, freezes continuation
while pending, and never auto-approves or continues execution.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.audit_response_control import AuditResponseControlResult

logger = logging.getLogger(__name__)

APPROVAL_TYPE_EXECUTION = "execution"
APPROVAL_TYPE_ARCHITECTURE = "architecture"
APPROVAL_TYPE_SECURITY = "security"
APPROVAL_TYPE_DEPLOYMENT = "deployment"
APPROVAL_TYPE_CONTINUATION = "continuation"
SUPPORTED_APPROVAL_TYPES = {
    APPROVAL_TYPE_EXECUTION,
    APPROVAL_TYPE_ARCHITECTURE,
    APPROVAL_TYPE_SECURITY,
    APPROVAL_TYPE_DEPLOYMENT,
    APPROVAL_TYPE_CONTINUATION,
}

APPROVAL_STATUS_PENDING = "pending"
APPROVAL_STATUS_APPROVED = "approved"
APPROVAL_STATUS_REJECTED = "rejected"
APPROVAL_STATUS_NEEDS_CHANGES = "needs_changes"
APPROVAL_STATUS_ESCALATED = "escalated"
APPROVAL_STATUS_BLOCKED = "blocked"
APPROVAL_STATUS_ERROR = "error"

HUMAN_DECISION_APPROVE = "approve"
HUMAN_DECISION_REJECT = "reject"
HUMAN_DECISION_NEEDS_CHANGES = "needs_changes"
HUMAN_DECISION_ESCALATE = "escalate"
SUPPORTED_HUMAN_DECISIONS = {
    HUMAN_DECISION_APPROVE,
    HUMAN_DECISION_REJECT,
    HUMAN_DECISION_NEEDS_CHANGES,
    HUMAN_DECISION_ESCALATE,
}

AUDIT_APPROVED = "approved"
AUDIT_APPROVED_WITH_WARNINGS = "approved_with_warnings"


@dataclass(frozen=True)
class ApprovalGateRequest:
    execution_id: str | None = None
    task_id: str | None = None
    approval_type: str | None = None
    audit_response: AuditResponseControlResult | dict[str, Any] | Any | None = None
    audit_status: str | None = None
    risk_status: str | None = None
    execution_summary: str = ""
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    detected_risks: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    continuation_recommendation: str = ""
    execution_context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HumanDecisionInput:
    approval_id: str | None = None
    execution_id: str | None = None
    human_decision: str | None = None
    decided_by: str | None = None
    decision_reason: str = ""
    approval_request: dict[str, Any] | Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ApprovalGateResult:
    status: str
    success: bool
    approval_id: str
    execution_id: str | None
    task_id: str | None
    approval_type: str | None
    approval_status: str
    audit_status: str | None
    human_decision: str | None
    continuation_status: str
    risk_status: str | None
    governance_status: str
    context_preserved: bool
    human_authority_preserved: bool
    autonomy_blocked: bool
    decided_by: str | None = None
    decision_reason: str = ""
    human_report: dict[str, Any] = field(default_factory=dict)
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    detected_risks: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    approval_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    execution_context: dict[str, Any] = field(default_factory=dict)
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
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "approval_type": self.approval_type,
            "approval_status": self.approval_status,
            "audit_status": self.audit_status,
            "human_decision": self.human_decision,
            "continuation_status": self.continuation_status,
            "risk_status": self.risk_status,
            "governance_status": self.governance_status,
            "context_preserved": self.context_preserved,
            "human_authority_preserved": self.human_authority_preserved,
            "autonomy_blocked": self.autonomy_blocked,
            "decided_by": self.decided_by,
            "decision_reason": self.decision_reason,
            "human_report": dict(self.human_report),
            "modified_files": list(self.modified_files),
            "detected_risks": list(self.detected_risks),
            "warnings": list(self.warnings),
            "approval_lifecycle": [
                dict(entry) for entry in self.approval_lifecycle
            ],
            "execution_context": dict(self.execution_context),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class ApprovalGate:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def request(
        self,
        request: ApprovalGateRequest,
        runtime_active: bool = True,
        approval_permitted: bool = True,
    ) -> ApprovalGateResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        approval_id = str(uuid4())

        try:
            audit_response = self._audit_response(request.audit_response)
            audit_status = self._audit_status(request, audit_response)
            approval_type = self._approval_type(request, audit_response)
            execution_id = self._execution_id(request, audit_response)
            task_id = self._task_id(request, audit_response)
            risk_status = self._risk_status(request, audit_response)
            reasons = self._request_reasons(
                runtime_active=runtime_active,
                approval_permitted=approval_permitted,
                execution_id=execution_id,
                approval_type=approval_type,
                audit_status=audit_status,
                risk_status=risk_status,
            )
            if reasons:
                result = self._result(
                    status=APPROVAL_STATUS_BLOCKED,
                    success=False,
                    approval_id=approval_id,
                    execution_id=execution_id,
                    task_id=task_id,
                    approval_type=approval_type,
                    approval_status=APPROVAL_STATUS_BLOCKED,
                    audit_status=audit_status,
                    human_decision=None,
                    continuation_status="blocked_approval_request_invalid",
                    risk_status=risk_status,
                    governance_status="blocked",
                    context_preserved=True,
                    human_authority_preserved=True,
                    autonomy_blocked=True,
                    request=request,
                    audit_response=audit_response,
                    human_report={},
                    approval_lifecycle=(
                        self._lifecycle("approval_request_received"),
                        self._lifecycle(APPROVAL_STATUS_BLOCKED),
                    ),
                    reasons=reasons,
                    error=";".join(reasons),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            report = self._human_report(
                request=request,
                audit_response=audit_response,
                approval_id=approval_id,
                approval_type=approval_type,
                execution_id=execution_id,
                task_id=task_id,
                audit_status=audit_status,
                risk_status=risk_status,
            )
            result = self._result(
                status=APPROVAL_STATUS_PENDING,
                success=True,
                approval_id=approval_id,
                execution_id=execution_id,
                task_id=task_id,
                approval_type=approval_type,
                approval_status=APPROVAL_STATUS_PENDING,
                audit_status=audit_status,
                human_decision=None,
                continuation_status="frozen_waiting_human_approval",
                risk_status=risk_status,
                governance_status="waiting_human_authority",
                context_preserved=True,
                human_authority_preserved=True,
                autonomy_blocked=True,
                request=request,
                audit_response=audit_response,
                human_report=report,
                approval_lifecycle=(
                    self._lifecycle("approval_requested"),
                    self._lifecycle(APPROVAL_STATUS_PENDING),
                ),
                reasons=[],
                error=None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                approval_id=approval_id,
                execution_id=request.execution_id,
                task_id=request.task_id,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def decide(
        self,
        decision: HumanDecisionInput,
        runtime_active: bool = True,
        decision_permitted: bool = True,
    ) -> ApprovalGateResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)

        try:
            approval_request = self._approval_request(decision.approval_request)
            approval_id = decision.approval_id or approval_request.get("approval_id")
            execution_id = (
                decision.execution_id or approval_request.get("execution_id")
            )
            human_decision = self._human_decision(decision.human_decision)
            reasons = self._decision_reasons(
                runtime_active=runtime_active,
                decision_permitted=decision_permitted,
                approval_id=approval_id,
                execution_id=execution_id,
                human_decision=human_decision,
                decided_by=decision.decided_by,
                approval_request=approval_request,
            )
            if reasons:
                result = self._decision_result(
                    status=APPROVAL_STATUS_BLOCKED,
                    success=False,
                    approval_id=approval_id or str(uuid4()),
                    execution_id=execution_id,
                    human_decision=human_decision,
                    decision=decision,
                    approval_request=approval_request,
                    approval_status=APPROVAL_STATUS_BLOCKED,
                    continuation_status="blocked_human_decision_invalid",
                    governance_status="blocked",
                    autonomy_blocked=True,
                    approval_lifecycle=(
                        self._lifecycle("human_decision_received"),
                        self._lifecycle(APPROVAL_STATUS_BLOCKED),
                    ),
                    reasons=reasons,
                    error=";".join(reasons),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            outcome = self._decision_outcome(human_decision)
            result = self._decision_result(
                status=str(outcome["approval_status"]),
                success=bool(outcome["success"]),
                approval_id=approval_id or str(uuid4()),
                execution_id=execution_id,
                human_decision=human_decision,
                decision=decision,
                approval_request=approval_request,
                approval_status=str(outcome["approval_status"]),
                continuation_status=str(outcome["continuation_status"]),
                governance_status=str(outcome["governance_status"]),
                autonomy_blocked=bool(outcome["autonomy_blocked"]),
                approval_lifecycle=(
                    self._lifecycle("human_decision_received"),
                    self._lifecycle(str(outcome["approval_status"])),
                ),
                reasons=list(outcome["reasons"]),
                error=None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                approval_id=decision.approval_id or str(uuid4()),
                execution_id=decision.execution_id,
                task_id=None,
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
        execution_id: str | None,
        task_id: str | None,
        approval_type: str | None,
        approval_status: str,
        audit_status: str | None,
        human_decision: str | None,
        continuation_status: str,
        risk_status: str | None,
        governance_status: str,
        context_preserved: bool,
        human_authority_preserved: bool,
        autonomy_blocked: bool,
        request: ApprovalGateRequest,
        audit_response: dict[str, Any],
        human_report: dict[str, Any],
        approval_lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> ApprovalGateResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        return ApprovalGateResult(
            status=status,
            success=success,
            approval_id=approval_id,
            execution_id=execution_id,
            task_id=task_id,
            approval_type=approval_type,
            approval_status=approval_status,
            audit_status=audit_status,
            human_decision=human_decision,
            continuation_status=continuation_status,
            risk_status=risk_status,
            governance_status=governance_status,
            context_preserved=context_preserved,
            human_authority_preserved=human_authority_preserved,
            autonomy_blocked=autonomy_blocked,
            human_report=human_report,
            modified_files=tuple(self._modified_files(request, audit_response)),
            detected_risks=tuple(self._detected_risks(request, audit_response)),
            warnings=tuple(self._warnings(request, audit_response)),
            approval_lifecycle=approval_lifecycle,
            execution_context=dict(request.execution_context or {}),
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            reasons=tuple(reasons or []),
            error=error,
            metadata=dict(request.metadata),
        )

    def _decision_result(
        self,
        status: str,
        success: bool,
        approval_id: str,
        execution_id: str | None,
        human_decision: str | None,
        decision: HumanDecisionInput,
        approval_request: dict[str, Any],
        approval_status: str,
        continuation_status: str,
        governance_status: str,
        autonomy_blocked: bool,
        approval_lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> ApprovalGateResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        return ApprovalGateResult(
            status=status,
            success=success,
            approval_id=approval_id,
            execution_id=execution_id,
            task_id=approval_request.get("task_id"),
            approval_type=approval_request.get("approval_type"),
            approval_status=approval_status,
            audit_status=approval_request.get("audit_status"),
            human_decision=human_decision,
            continuation_status=continuation_status,
            risk_status=approval_request.get("risk_status"),
            governance_status=governance_status,
            context_preserved=True,
            human_authority_preserved=True,
            autonomy_blocked=autonomy_blocked,
            decided_by=decision.decided_by,
            decision_reason=decision.decision_reason,
            human_report=dict(approval_request.get("human_report") or {}),
            modified_files=tuple(approval_request.get("modified_files") or []),
            detected_risks=tuple(approval_request.get("detected_risks") or []),
            warnings=tuple(approval_request.get("warnings") or []),
            approval_lifecycle=approval_lifecycle,
            execution_context=dict(approval_request.get("execution_context") or {}),
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            reasons=tuple(reasons or []),
            error=error,
            metadata=dict(decision.metadata),
        )

    def _error_result(
        self,
        approval_id: str,
        execution_id: str | None,
        task_id: str | None,
        error: str,
        started: float,
        started_at: datetime,
    ) -> ApprovalGateResult:
        finished_at = datetime.now(timezone.utc)
        return ApprovalGateResult(
            status=APPROVAL_STATUS_ERROR,
            success=False,
            approval_id=approval_id,
            execution_id=execution_id,
            task_id=task_id,
            approval_type=None,
            approval_status=APPROVAL_STATUS_ERROR,
            audit_status=None,
            human_decision=None,
            continuation_status="blocked_approval_gate_error",
            risk_status=None,
            governance_status="blocked",
            context_preserved=True,
            human_authority_preserved=True,
            autonomy_blocked=True,
            approval_lifecycle=(self._lifecycle(APPROVAL_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("approval_gate_error_contained",),
            error=error,
        )

    def _request_reasons(
        self,
        runtime_active: bool,
        approval_permitted: bool,
        execution_id: str | None,
        approval_type: str | None,
        audit_status: str | None,
        risk_status: str | None,
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not approval_permitted:
            reasons.append("approval_request_not_permitted")
        if not execution_id:
            reasons.append("missing_execution_id")
        if approval_type not in SUPPORTED_APPROVAL_TYPES:
            reasons.append("unsupported_approval_type")
        if not audit_status:
            reasons.append("missing_audit_status")
        elif audit_status not in {AUDIT_APPROVED, AUDIT_APPROVED_WITH_WARNINGS}:
            reasons.append("audit_not_approved_for_approval_gate")
        if not risk_status:
            reasons.append("missing_risk_status")
        return self._unique(reasons)

    def _decision_reasons(
        self,
        runtime_active: bool,
        decision_permitted: bool,
        approval_id: str | None,
        execution_id: str | None,
        human_decision: str | None,
        decided_by: str | None,
        approval_request: dict[str, Any],
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not decision_permitted:
            reasons.append("human_decision_not_permitted")
        if not approval_id:
            reasons.append("missing_approval_id")
        if not execution_id:
            reasons.append("missing_execution_id")
        if human_decision not in SUPPORTED_HUMAN_DECISIONS:
            reasons.append("unsupported_human_decision")
        if not decided_by:
            reasons.append("missing_human_decision_authority")
        if not approval_request:
            reasons.append("missing_approval_request")
        else:
            if approval_request.get("approval_id") and approval_id:
                if approval_request["approval_id"] != approval_id:
                    reasons.append("approval_id_mismatch")
            if approval_request.get("execution_id") and execution_id:
                if approval_request["execution_id"] != execution_id:
                    reasons.append("execution_id_mismatch")
            if approval_request.get("approval_status") != APPROVAL_STATUS_PENDING:
                reasons.append("approval_not_pending")
        return self._unique(reasons)

    def _decision_outcome(self, human_decision: str | None) -> dict[str, Any]:
        if human_decision == HUMAN_DECISION_APPROVE:
            return {
                "success": True,
                "approval_status": APPROVAL_STATUS_APPROVED,
                "continuation_status": "authorized_by_human",
                "governance_status": "human_approved",
                "autonomy_blocked": False,
                "reasons": ["human_authorization_recorded_no_auto_continue"],
            }
        if human_decision == HUMAN_DECISION_REJECT:
            return {
                "success": False,
                "approval_status": APPROVAL_STATUS_REJECTED,
                "continuation_status": "blocked_human_rejected",
                "governance_status": "human_rejected",
                "autonomy_blocked": True,
                "reasons": ["human_rejection_blocks_continuation"],
            }
        if human_decision == HUMAN_DECISION_NEEDS_CHANGES:
            return {
                "success": False,
                "approval_status": APPROVAL_STATUS_NEEDS_CHANGES,
                "continuation_status": "blocked_needs_changes",
                "governance_status": "changes_requested",
                "autonomy_blocked": True,
                "reasons": ["human_requested_changes"],
            }
        return {
            "success": False,
            "approval_status": APPROVAL_STATUS_ESCALATED,
            "continuation_status": "blocked_escalated",
            "governance_status": "escalated",
            "autonomy_blocked": True,
            "reasons": ["human_escalation_requested"],
        }

    def _human_report(
        self,
        request: ApprovalGateRequest,
        audit_response: dict[str, Any],
        approval_id: str,
        approval_type: str | None,
        execution_id: str | None,
        task_id: str | None,
        audit_status: str | None,
        risk_status: str | None,
    ) -> dict[str, Any]:
        return {
            "approval_id": approval_id,
            "execution_id": execution_id,
            "task_id": task_id,
            "approval_type": approval_type,
            "execution_summary": request.execution_summary,
            "modified_files": self._modified_files(request, audit_response),
            "detected_risks": self._detected_risks(request, audit_response),
            "warnings": self._warnings(request, audit_response),
            "audit_result": audit_status,
            "risk_status": risk_status,
            "continuation_recommendation": request.continuation_recommendation,
            "approval_status": APPROVAL_STATUS_PENDING,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _audit_response(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, AuditResponseControlResult):
            return value.to_dict()
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

    def _approval_request(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, ApprovalGateResult):
            return value.to_dict()
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

    def _audit_status(
        self,
        request: ApprovalGateRequest,
        audit_response: dict[str, Any],
    ) -> str | None:
        value = request.audit_status or audit_response.get("audit_result")
        if value is None:
            return None
        return str(value).strip().lower().replace("-", "_").replace(" ", "_")

    def _risk_status(
        self,
        request: ApprovalGateRequest,
        audit_response: dict[str, Any],
    ) -> str | None:
        value = request.risk_status or audit_response.get("risk_level")
        if value is None:
            return None
        return str(value).strip().lower().replace("-", "_").replace(" ", "_")

    def _approval_type(
        self,
        request: ApprovalGateRequest,
        audit_response: dict[str, Any],
    ) -> str | None:
        if request.approval_type:
            return str(request.approval_type).strip().lower()
        if audit_response.get("security_escalation_status") == "escalated_to_centinela":
            return APPROVAL_TYPE_SECURITY
        files = " ".join(self._modified_files(request, audit_response)).lower()
        if "render" in files or "deploy" in files:
            return APPROVAL_TYPE_DEPLOYMENT
        if "architecture" in files or "runtime_loop" in files:
            return APPROVAL_TYPE_ARCHITECTURE
        return APPROVAL_TYPE_CONTINUATION

    def _execution_id(
        self,
        request: ApprovalGateRequest,
        audit_response: dict[str, Any],
    ) -> str | None:
        return request.execution_id or audit_response.get("execution_id")

    def _task_id(
        self,
        request: ApprovalGateRequest,
        audit_response: dict[str, Any],
    ) -> str | None:
        return request.task_id or audit_response.get("task_id")

    def _human_decision(self, value: str | None) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower().replace("-", "_").replace(" ", "_")

    def _modified_files(
        self,
        request: ApprovalGateRequest,
        audit_response: dict[str, Any],
    ) -> list[str]:
        return self._unique(
            [
                *[str(path) for path in request.modified_files],
                *[str(path) for path in audit_response.get("modified_files") or []],
            ]
        )

    def _detected_risks(
        self,
        request: ApprovalGateRequest,
        audit_response: dict[str, Any],
    ) -> list[str]:
        return self._unique(
            [
                *[str(risk) for risk in request.detected_risks],
                *[str(risk) for risk in audit_response.get("detected_risks") or []],
            ]
        )

    def _warnings(
        self,
        request: ApprovalGateRequest,
        audit_response: dict[str, Any],
    ) -> list[str]:
        return self._unique(
            [
                *[str(warning) for warning in request.warnings],
                *[str(warning) for warning in audit_response.get("warnings") or []],
            ]
        )

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

    def _publish(self, result: ApprovalGateResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_approval_gate_result",
        ):
            self.status.mark_approval_gate_result(result.to_dict())

    def _log_result(self, result: ApprovalGateResult) -> None:
        if result.status == APPROVAL_STATUS_ERROR:
            logger.error(
                "approval_gate: error approval_id=%s error=%s",
                result.approval_id,
                result.error,
            )
            return
        if result.status == APPROVAL_STATUS_BLOCKED:
            logger.warning(
                "approval_gate: blocked approval_id=%s reasons=%s",
                result.approval_id,
                ",".join(result.reasons),
            )
            return
        if result.status == APPROVAL_STATUS_PENDING:
            logger.info(
                "approval_gate: pending approval_id=%s execution_id=%s type=%s",
                result.approval_id,
                result.execution_id,
                result.approval_type,
            )
            return
        logger.info(
            "approval_gate: decision approval_id=%s status=%s decision=%s",
            result.approval_id,
            result.approval_status,
            result.human_decision,
        )
