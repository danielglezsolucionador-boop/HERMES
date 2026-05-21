"""
Controlled execution blocking for Hermes runtime.

This layer activates traceable operational blocks when continuation is unsafe.
It freezes continuation at the governance/control layer, preserves context, and
does not mutate tasks, kill the runtime loop, recover work, or bypass human or
security authority.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.approval_gate import ApprovalGateResult
from app.runner.approval_system import ApprovalSystemResult
from app.runner.audit_response_control import AuditResponseControlResult
from app.runner.governance_foundation import GovernanceFoundationResult

logger = logging.getLogger(__name__)

BLOCK_TYPE_AUDIT = "audit"
BLOCK_TYPE_APPROVAL = "approval"
BLOCK_TYPE_SECURITY = "security"
BLOCK_TYPE_GOVERNANCE = "governance"
BLOCK_TYPE_RUNTIME = "runtime"
BLOCK_TYPE_PROVIDER = "provider"
BLOCK_TYPE_HUMAN = "human"
BLOCK_TYPE_CONTINUATION = "continuation"
SUPPORTED_BLOCK_TYPES = {
    BLOCK_TYPE_AUDIT,
    BLOCK_TYPE_APPROVAL,
    BLOCK_TYPE_SECURITY,
    BLOCK_TYPE_GOVERNANCE,
    BLOCK_TYPE_RUNTIME,
    BLOCK_TYPE_PROVIDER,
    BLOCK_TYPE_HUMAN,
    BLOCK_TYPE_CONTINUATION,
}

BLOCK_STATUS_ACTIVE = "active"
BLOCK_STATUS_BLOCKED = "blocked"
BLOCK_STATUS_ERROR = "error"

BLOCK_CLASS_TEMPORARY = "temporary_block"
BLOCK_CLASS_CRITICAL = "critical_block"
BLOCK_CLASS_GOVERNANCE = "governance_block"
BLOCK_CLASS_SECURITY = "security_block"

RISK_CLEAR = "clear"
RISK_ELEVATED = "elevated"
RISK_CRITICAL = "critical"

SECURITY_HINTS = (
    "security",
    "secret",
    "credential",
    "malicious",
    "leak",
    "compromise",
    "destructive",
    "filesystem danger",
    "unauthorized execution",
)


@dataclass(frozen=True)
class ExecutionBlockRequest:
    execution_id: str | None = None
    task_id: str | None = None
    block_type: str | None = None
    block_reason: str = ""
    risk_level: str | None = None
    audit_response: AuditResponseControlResult | dict[str, Any] | Any | None = None
    approval_gate: ApprovalGateResult | dict[str, Any] | Any | None = None
    approval_system: ApprovalSystemResult | dict[str, Any] | Any | None = None
    governance_foundation: (
        GovernanceFoundationResult | dict[str, Any] | Any | None
    ) = None
    continuation_status: str | None = None
    security_status: str | None = None
    blocking_status: str | None = None
    runtime_state: dict[str, Any] = field(default_factory=dict)
    provider_context: dict[str, Any] = field(default_factory=dict)
    execution_context: dict[str, Any] = field(default_factory=dict)
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    runtime_logs: tuple[Any, ...] = field(default_factory=tuple)
    audit_history: tuple[Any, ...] = field(default_factory=tuple)
    risk_history: tuple[str, ...] = field(default_factory=tuple)
    corruption_warnings: tuple[str, ...] = field(default_factory=tuple)
    human_requested: bool = False
    override_block_requested: bool = False
    ignore_critical_block_requested: bool = False
    minimize_risk_requested: bool = False
    falsify_runtime_stability_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionBlockResult:
    status: str
    success: bool
    block_id: str
    execution_id: str | None
    task_id: str | None
    block_type: str | None
    block_status: str
    block_classification: str | None
    block_reason: str | None
    risk_level: str | None
    escalation_status: str
    continuation_status: str
    execution_frozen: bool
    continuation_blocked: bool
    context_preserved: bool
    governance_protected: bool
    security_authority_required: bool
    human_authority_required: bool
    block_condition_detected: bool
    governance_conflict_detected: bool
    approval_missing_detected: bool
    audit_rejection_detected: bool
    security_escalation_detected: bool
    runtime_corruption_detected: bool
    execution_inconsistency_detected: bool
    continuation_unsafe_detected: bool
    block_preserved: bool
    escalation_report: dict[str, Any] = field(default_factory=dict)
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    runtime_logs: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    audit_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    risk_history: tuple[str, ...] = field(default_factory=tuple)
    runtime_state: dict[str, Any] = field(default_factory=dict)
    provider_context: dict[str, Any] = field(default_factory=dict)
    execution_context: dict[str, Any] = field(default_factory=dict)
    blocking_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "block_id": self.block_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "block_type": self.block_type,
            "block_status": self.block_status,
            "block_classification": self.block_classification,
            "block_reason": self.block_reason,
            "risk_level": self.risk_level,
            "escalation_status": self.escalation_status,
            "continuation_status": self.continuation_status,
            "execution_frozen": self.execution_frozen,
            "continuation_blocked": self.continuation_blocked,
            "context_preserved": self.context_preserved,
            "governance_protected": self.governance_protected,
            "security_authority_required": self.security_authority_required,
            "human_authority_required": self.human_authority_required,
            "block_condition_detected": self.block_condition_detected,
            "governance_conflict_detected": self.governance_conflict_detected,
            "approval_missing_detected": self.approval_missing_detected,
            "audit_rejection_detected": self.audit_rejection_detected,
            "security_escalation_detected": self.security_escalation_detected,
            "runtime_corruption_detected": self.runtime_corruption_detected,
            "execution_inconsistency_detected": (
                self.execution_inconsistency_detected
            ),
            "continuation_unsafe_detected": (
                self.continuation_unsafe_detected
            ),
            "block_preserved": self.block_preserved,
            "escalation_report": dict(self.escalation_report),
            "modified_files": list(self.modified_files),
            "runtime_logs": [dict(entry) for entry in self.runtime_logs],
            "audit_history": [dict(entry) for entry in self.audit_history],
            "risk_history": list(self.risk_history),
            "runtime_state": dict(self.runtime_state),
            "provider_context": dict(self.provider_context),
            "execution_context": dict(self.execution_context),
            "blocking_lifecycle": [
                dict(entry) for entry in self.blocking_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class ExecutionBlocking:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def activate(
        self,
        request: ExecutionBlockRequest,
        runtime_active: bool = True,
        blocking_permitted: bool = True,
    ) -> ExecutionBlockResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        block_id = str(uuid4())

        try:
            audit_response = self._audit_response(request.audit_response)
            approval_gate = self._approval_gate(request.approval_gate)
            approval_system = self._approval_system(request.approval_system)
            governance_foundation = self._governance_foundation(
                request.governance_foundation
            )
            block_type = self._block_type(
                request,
                audit_response,
                approval_gate,
                approval_system,
                governance_foundation,
            )
            risk_level = self._risk_level(
                request,
                audit_response,
                approval_gate,
                approval_system,
                governance_foundation,
            )
            execution_id = self._execution_id(
                request,
                audit_response,
                approval_gate,
                approval_system,
                governance_foundation,
            )
            task_id = self._task_id(
                request,
                audit_response,
                approval_gate,
                approval_system,
            )
            block_reason = self._block_reason(
                request,
                audit_response,
                approval_gate,
                approval_system,
                governance_foundation,
                block_type,
            )
            reasons = self._request_reasons(
                runtime_active=runtime_active,
                blocking_permitted=blocking_permitted,
                execution_id=execution_id,
                block_type=block_type,
                block_reason=block_reason,
                risk_level=risk_level,
            )
            if reasons:
                result = self._result(
                    status=BLOCK_STATUS_BLOCKED,
                    success=False,
                    block_id=block_id,
                    execution_id=execution_id,
                    task_id=task_id,
                    block_type=block_type,
                    block_status=BLOCK_STATUS_BLOCKED,
                    block_classification=None,
                    block_reason=block_reason,
                    risk_level=risk_level,
                    escalation_status="not_evaluated",
                    continuation_status="blocked_invalid_execution_block",
                    execution_frozen=True,
                    continuation_blocked=True,
                    context_preserved=True,
                    governance_protected=True,
                    security_authority_required=False,
                    human_authority_required=True,
                    request=request,
                    audit_response=audit_response,
                    approval_gate=approval_gate,
                    approval_system=approval_system,
                    governance_foundation=governance_foundation,
                    lifecycle=(
                        self._lifecycle("block_detection"),
                        self._lifecycle(BLOCK_STATUS_BLOCKED),
                    ),
                    reasons=reasons,
                    error=";".join(reasons),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            classification = self._classification(block_type, risk_level)
            escalation_status = self._escalation_status(
                block_type,
                classification,
            )
            result = self._result(
                status=BLOCK_STATUS_ACTIVE,
                success=True,
                block_id=block_id,
                execution_id=execution_id,
                task_id=task_id,
                block_type=block_type,
                block_status=BLOCK_STATUS_ACTIVE,
                block_classification=classification,
                block_reason=block_reason,
                risk_level=risk_level,
                escalation_status=escalation_status,
                continuation_status=self._continuation_status(
                    block_type,
                    classification,
                ),
                execution_frozen=True,
                continuation_blocked=True,
                context_preserved=True,
                governance_protected=True,
                security_authority_required=classification == BLOCK_CLASS_SECURITY,
                human_authority_required=classification
                in {BLOCK_CLASS_CRITICAL, BLOCK_CLASS_GOVERNANCE, BLOCK_CLASS_SECURITY},
                request=request,
                audit_response=audit_response,
                approval_gate=approval_gate,
                approval_system=approval_system,
                governance_foundation=governance_foundation,
                lifecycle=(
                    self._lifecycle("block_detection"),
                    self._lifecycle("block_activation"),
                    self._lifecycle(classification),
                ),
                reasons=self._activation_reasons(block_type, classification),
                error=None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._result(
                status=BLOCK_STATUS_ERROR,
                success=False,
                block_id=block_id,
                execution_id=request.execution_id,
                task_id=request.task_id,
                block_type=request.block_type,
                block_status=BLOCK_STATUS_ERROR,
                block_classification=None,
                block_reason=request.block_reason,
                risk_level=request.risk_level,
                escalation_status="not_evaluated",
                continuation_status="blocked_execution_blocking_error",
                execution_frozen=True,
                continuation_blocked=True,
                context_preserved=True,
                governance_protected=True,
                security_authority_required=False,
                human_authority_required=True,
                request=request,
                audit_response={},
                approval_gate={},
                approval_system={},
                governance_foundation={},
                lifecycle=(self._lifecycle(BLOCK_STATUS_ERROR),),
                reasons=["execution_blocking_error_contained"],
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
        block_id: str,
        execution_id: str | None,
        task_id: str | None,
        block_type: str | None,
        block_status: str,
        block_classification: str | None,
        block_reason: str | None,
        risk_level: str | None,
        escalation_status: str,
        continuation_status: str,
        execution_frozen: bool,
        continuation_blocked: bool,
        context_preserved: bool,
        governance_protected: bool,
        security_authority_required: bool,
        human_authority_required: bool,
        request: ExecutionBlockRequest,
        audit_response: dict[str, Any],
        approval_gate: dict[str, Any],
        approval_system: dict[str, Any],
        governance_foundation: dict[str, Any],
        lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> ExecutionBlockResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        return ExecutionBlockResult(
            status=status,
            success=success,
            block_id=block_id,
            execution_id=execution_id,
            task_id=task_id,
            block_type=block_type,
            block_status=block_status,
            block_classification=block_classification,
            block_reason=block_reason,
            risk_level=risk_level,
            escalation_status=escalation_status,
            continuation_status=continuation_status,
            execution_frozen=execution_frozen,
            continuation_blocked=continuation_blocked,
            context_preserved=context_preserved,
            governance_protected=governance_protected,
            security_authority_required=security_authority_required,
            human_authority_required=human_authority_required,
            block_condition_detected=block_type in SUPPORTED_BLOCK_TYPES,
            governance_conflict_detected=self._governance_conflict(
                governance_foundation,
                approval_gate,
            ),
            approval_missing_detected=self._approval_missing(approval_system),
            audit_rejection_detected=self._audit_rejected(audit_response),
            security_escalation_detected=self._security_escalation(
                request,
                audit_response,
                approval_system,
                governance_foundation,
            ),
            runtime_corruption_detected=self._runtime_corrupted(
                request.runtime_state
            ),
            execution_inconsistency_detected=self._execution_inconsistent(
                request,
            ),
            continuation_unsafe_detected=self._continuation_unsafe(request),
            block_preserved=not (
                request.override_block_requested
                or request.ignore_critical_block_requested
            ),
            escalation_report=self._escalation_report(
                request=request,
                block_type=block_type,
                block_reason=block_reason,
                risk_level=risk_level,
                escalation_status=escalation_status,
                governance_foundation=governance_foundation,
                approval_system=approval_system,
            ),
            modified_files=tuple(self._modified_files(request, audit_response)),
            runtime_logs=tuple(self._runtime_logs(request)),
            audit_history=tuple(self._audit_history(request, audit_response)),
            risk_history=tuple(self._risk_history(request, audit_response)),
            runtime_state=dict(request.runtime_state or {}),
            provider_context=dict(request.provider_context or {}),
            execution_context=dict(request.execution_context or {}),
            blocking_lifecycle=lifecycle,
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            reasons=tuple(reasons or []),
            error=error,
            metadata=dict(request.metadata),
        )

    def _request_reasons(
        self,
        runtime_active: bool,
        blocking_permitted: bool,
        execution_id: str | None,
        block_type: str | None,
        block_reason: str | None,
        risk_level: str | None,
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not blocking_permitted:
            reasons.append("execution_blocking_not_permitted")
        if not execution_id:
            reasons.append("missing_execution_id")
        if block_type not in SUPPORTED_BLOCK_TYPES:
            reasons.append("unsupported_block_type")
        if not block_reason:
            reasons.append("missing_block_reason")
        if not risk_level:
            reasons.append("missing_risk_level")
        return self._unique(reasons)

    def _block_type(
        self,
        request: ExecutionBlockRequest,
        audit_response: dict[str, Any],
        approval_gate: dict[str, Any],
        approval_system: dict[str, Any],
        governance_foundation: dict[str, Any],
    ) -> str | None:
        if request.block_type:
            return str(request.block_type).strip().lower()
        if request.human_requested:
            return BLOCK_TYPE_HUMAN
        if self._security_escalation(
            request,
            audit_response,
            approval_system,
            governance_foundation,
        ):
            return BLOCK_TYPE_SECURITY
        audit_status = str(audit_response.get("status") or "").lower()
        if audit_response.get("centinela_escalation") or self._has_security_hint(
            request,
            audit_response,
            approval_gate,
            approval_system,
            governance_foundation,
        ):
            return BLOCK_TYPE_SECURITY
        if audit_status in {"rejected", "needs_fix"}:
            return BLOCK_TYPE_AUDIT
        if self._approval_missing(approval_system):
            return BLOCK_TYPE_APPROVAL
        approval_system_status = str(approval_system.get("status") or "").lower()
        if approval_system_status in {
            "blocked",
            "escalation_required",
            "rejected",
        }:
            return BLOCK_TYPE_APPROVAL
        approval_status = str(approval_gate.get("approval_status") or "").lower()
        if approval_status in {"pending", "rejected", "needs_changes", "escalated"}:
            return BLOCK_TYPE_GOVERNANCE
        if self._governance_conflict(governance_foundation, approval_gate):
            return BLOCK_TYPE_GOVERNANCE
        if self._runtime_corrupted(request.runtime_state):
            return BLOCK_TYPE_RUNTIME
        if self._execution_inconsistent(request):
            return BLOCK_TYPE_RUNTIME
        if self._provider_failed(request.provider_context):
            return BLOCK_TYPE_PROVIDER
        if self._continuation_unsafe(request):
            return BLOCK_TYPE_CONTINUATION
        return None

    def _risk_level(
        self,
        request: ExecutionBlockRequest,
        audit_response: dict[str, Any],
        approval_gate: dict[str, Any],
        approval_system: dict[str, Any],
        governance_foundation: dict[str, Any],
    ) -> str | None:
        value = (
            request.risk_level
            or audit_response.get("risk_level")
            or approval_gate.get("risk_status")
            or approval_system.get("risk_level")
        )
        if value is None:
            if self._security_escalation(
                request,
                audit_response,
                approval_system,
                governance_foundation,
            ):
                return RISK_CRITICAL
            if self._approval_missing(approval_system):
                return RISK_ELEVATED
            if self._governance_conflict(governance_foundation, approval_gate):
                return RISK_ELEVATED
            if self._continuation_unsafe(request):
                return RISK_CRITICAL
            if self._provider_failed(request.provider_context):
                return RISK_ELEVATED
            if request.human_requested:
                return RISK_ELEVATED
            return None
        normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in {"none", "ok", "safe"}:
            return RISK_CLEAR
        if normalized in {"high", "severe"}:
            return RISK_CRITICAL
        if normalized in {"medium", "warning", "low"}:
            return RISK_ELEVATED
        return normalized

    def _execution_id(
        self,
        request: ExecutionBlockRequest,
        audit_response: dict[str, Any],
        approval_gate: dict[str, Any],
        approval_system: dict[str, Any],
        governance_foundation: dict[str, Any],
    ) -> str | None:
        return (
            request.execution_id
            or audit_response.get("execution_id")
            or approval_gate.get("execution_id")
            or approval_system.get("execution_id")
            or governance_foundation.get("execution_context", {}).get("execution_id")
        )

    def _task_id(
        self,
        request: ExecutionBlockRequest,
        audit_response: dict[str, Any],
        approval_gate: dict[str, Any],
        approval_system: dict[str, Any],
    ) -> str | None:
        return (
            request.task_id
            or audit_response.get("task_id")
            or approval_gate.get("task_id")
            or approval_system.get("task_id")
        )

    def _block_reason(
        self,
        request: ExecutionBlockRequest,
        audit_response: dict[str, Any],
        approval_gate: dict[str, Any],
        approval_system: dict[str, Any],
        governance_foundation: dict[str, Any],
        block_type: str | None,
    ) -> str | None:
        if request.block_reason:
            return request.block_reason
        if block_type == BLOCK_TYPE_SECURITY:
            return "security_escalation_blocks_continuation"
        if block_type == BLOCK_TYPE_APPROVAL:
            return "approval_validation_blocks_continuation"
        if block_type == BLOCK_TYPE_AUDIT:
            return "audit_result_blocks_continuation"
        if block_type == BLOCK_TYPE_GOVERNANCE:
            return "governance_approval_blocks_continuation"
        if block_type == BLOCK_TYPE_RUNTIME:
            return "runtime_state_blocks_continuation"
        if block_type == BLOCK_TYPE_PROVIDER:
            return "provider_failure_blocks_continuation"
        if block_type == BLOCK_TYPE_HUMAN:
            return "human_requested_execution_block"
        if block_type == BLOCK_TYPE_CONTINUATION:
            return "unsafe_continuation_blocks_execution"
        if approval_system.get("execution_decision"):
            return str(approval_system["execution_decision"])
        if governance_foundation.get("status"):
            return str(governance_foundation["status"])
        if audit_response.get("block_reason"):
            return str(audit_response["block_reason"])
        if approval_gate.get("continuation_status"):
            return str(approval_gate["continuation_status"])
        return None

    def _classification(self, block_type: str | None, risk_level: str | None) -> str:
        if block_type == BLOCK_TYPE_SECURITY:
            return BLOCK_CLASS_SECURITY
        if block_type in {
            BLOCK_TYPE_APPROVAL,
            BLOCK_TYPE_GOVERNANCE,
            BLOCK_TYPE_CONTINUATION,
        }:
            return BLOCK_CLASS_GOVERNANCE
        if risk_level == RISK_CRITICAL or block_type in {
            BLOCK_TYPE_AUDIT,
            BLOCK_TYPE_RUNTIME,
            BLOCK_TYPE_HUMAN,
        }:
            return BLOCK_CLASS_CRITICAL
        return BLOCK_CLASS_TEMPORARY

    def _escalation_status(
        self,
        block_type: str | None,
        classification: str,
    ) -> str:
        if classification == BLOCK_CLASS_SECURITY:
            return "escalated_to_centinela"
        if block_type == BLOCK_TYPE_APPROVAL:
            return "approval_escalation_required"
        if block_type in {BLOCK_TYPE_GOVERNANCE, BLOCK_TYPE_CONTINUATION}:
            return "waiting_human_approval"
        if classification == BLOCK_CLASS_CRITICAL:
            return "human_intervention_required"
        if block_type == BLOCK_TYPE_PROVIDER:
            return "operator_visibility_required"
        return "not_required"

    def _continuation_status(self, block_type: str | None, classification: str) -> str:
        if classification == BLOCK_CLASS_SECURITY:
            return "blocked_security_authority"
        if block_type == BLOCK_TYPE_APPROVAL:
            return "blocked_approval_authority"
        if block_type == BLOCK_TYPE_CONTINUATION:
            return "blocked_unsafe_continuation"
        if classification == BLOCK_CLASS_GOVERNANCE:
            return "blocked_governance_authority"
        if classification == BLOCK_CLASS_CRITICAL:
            return "blocked_critical"
        return "blocked_temporary"

    def _activation_reasons(
        self,
        block_type: str | None,
        classification: str,
    ) -> list[str]:
        return self._unique(
            [
                f"{block_type}_blocking_active" if block_type else "",
                f"{classification}_activated",
                "continuation_blocked",
                "execution_context_preserved",
            ]
        )

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

    def _approval_gate(self, value: Any) -> dict[str, Any]:
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

    def _approval_system(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, ApprovalSystemResult):
            return value.to_dict()
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

    def _governance_foundation(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, GovernanceFoundationResult):
            return value.to_dict()
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

    def _governance_conflict(
        self,
        governance_foundation: dict[str, Any],
        approval_gate: dict[str, Any],
    ) -> bool:
        governance_status = str(
            governance_foundation.get("status")
            or approval_gate.get("governance_status")
            or ""
        ).lower()
        return governance_status in {
            "blocked",
            "rejected",
            "human_rejected",
            "changes_requested",
            "escalated",
        } or bool(governance_foundation.get("reasons"))

    def _approval_missing(self, approval_system: dict[str, Any]) -> bool:
        if not approval_system:
            return False
        status = str(approval_system.get("status") or "").lower()
        reasons = {
            str(reason)
            for reason in (approval_system.get("reasons") or [])
        }
        return (
            approval_system.get("approval_exists") is False
            or status in {"blocked", "escalation_required", "rejected"}
            or "approval_missing" in reasons
            or "approval_status_missing" in reasons
            or "approval_pending" in reasons
        )

    def _audit_rejected(self, audit_response: dict[str, Any]) -> bool:
        status = str(audit_response.get("status") or "").lower()
        audit_result = str(audit_response.get("audit_result") or "").lower()
        return status in {"rejected", "needs_fix"} or audit_result in {
            "rejected",
            "needs_fix",
        }

    def _security_escalation(
        self,
        request: ExecutionBlockRequest,
        audit_response: dict[str, Any],
        approval_system: dict[str, Any],
        governance_foundation: dict[str, Any],
    ) -> bool:
        security_status = str(
            request.security_status
            or approval_system.get("security_status")
            or governance_foundation.get("security_status")
            or audit_response.get("security_escalation_status")
            or ""
        ).lower()
        return (
            audit_response.get("centinela_escalation") is True
            or security_status
            in {"blocked", "critical", "critical_blocking", "escalated", "quarantine"}
        )

    def _execution_inconsistent(self, request: ExecutionBlockRequest) -> bool:
        values = json.dumps(request.execution_context, sort_keys=True, default=str)
        body = " ".join([values, *[str(item) for item in request.corruption_warnings]])
        return any(
            word in body.lower()
            for word in (
                "inconsistent",
                "orphan",
                "mismatch",
                "invalid_state",
                "corrupt",
            )
        ) or request.falsify_runtime_stability_requested

    def _continuation_unsafe(self, request: ExecutionBlockRequest) -> bool:
        status = str(request.continuation_status or "").lower()
        return status in {
            "unsafe",
            "blocked",
            "blocked_unsafe_continuation",
            "dangerous",
        } or bool(
            request.override_block_requested
            or request.ignore_critical_block_requested
            or request.minimize_risk_requested
        )

    def _escalation_report(
        self,
        request: ExecutionBlockRequest,
        block_type: str | None,
        block_reason: str | None,
        risk_level: str | None,
        escalation_status: str,
        governance_foundation: dict[str, Any],
        approval_system: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "block_type": block_type,
            "block_reason": block_reason,
            "risk_level": risk_level,
            "escalation_status": escalation_status,
            "governance_status": request.blocking_status
            or governance_foundation.get("governance_status"),
            "security_status": request.security_status
            or approval_system.get("security_status")
            or governance_foundation.get("security_status"),
            "continuation_status": request.continuation_status,
            "governance_reasons": list(governance_foundation.get("reasons") or []),
            "approval_reasons": list(approval_system.get("reasons") or []),
        }

    def _runtime_corrupted(self, runtime_state: dict[str, Any]) -> bool:
        values = json.dumps(runtime_state, sort_keys=True, default=str).lower()
        return any(word in values for word in ("corrupt", "compromise", "unsafe"))

    def _provider_failed(self, provider_context: dict[str, Any]) -> bool:
        values = json.dumps(provider_context, sort_keys=True, default=str).lower()
        return any(word in values for word in ("failed", "unavailable", "timeout"))

    def _has_security_hint(
        self,
        request: ExecutionBlockRequest,
        audit_response: dict[str, Any],
        approval_gate: dict[str, Any],
        approval_system: dict[str, Any],
        governance_foundation: dict[str, Any],
    ) -> bool:
        body = " ".join(
            [
                *[str(item) for item in request.risk_history],
                *[str(item) for item in audit_response.get("detected_risks") or []],
                *[
                    str(item)
                    for item in audit_response.get("rejection_reasons") or []
                ],
                *[
                    str(item)
                    for item in audit_response.get("correction_requirements") or []
                ],
                str(audit_response.get("escalation_status") or ""),
                str(audit_response.get("block_reason") or ""),
                *[str(item) for item in approval_gate.get("detected_risks") or []],
                str(approval_gate.get("governance_status") or ""),
                str(approval_system.get("security_status") or ""),
                *[str(item) for item in approval_system.get("risks") or []],
                str(governance_foundation.get("security_status") or ""),
                *[str(item) for item in governance_foundation.get("risks") or []],
                json.dumps(request.runtime_state, sort_keys=True, default=str),
                json.dumps(request.provider_context, sort_keys=True, default=str),
            ]
        ).lower()
        return any(hint in body for hint in SECURITY_HINTS)

    def _modified_files(
        self,
        request: ExecutionBlockRequest,
        audit_response: dict[str, Any],
    ) -> list[str]:
        return self._unique(
            [
                *[str(path) for path in request.modified_files],
                *[str(path) for path in audit_response.get("modified_files") or []],
            ]
        )

    def _runtime_logs(self, request: ExecutionBlockRequest) -> list[dict[str, Any]]:
        return [self._as_dict(entry) for entry in request.runtime_logs]

    def _audit_history(
        self,
        request: ExecutionBlockRequest,
        audit_response: dict[str, Any],
    ) -> list[dict[str, Any]]:
        history = [self._as_dict(entry) for entry in request.audit_history]
        if audit_response:
            history.append(
                {
                    "audit_result": audit_response.get("audit_result"),
                    "status": audit_response.get("status"),
                    "risk_level": audit_response.get("risk_level"),
                }
            )
        return history

    def _risk_history(
        self,
        request: ExecutionBlockRequest,
        audit_response: dict[str, Any],
    ) -> list[str]:
        return self._unique(
            [
                *[str(risk) for risk in request.risk_history],
                *[str(risk) for risk in audit_response.get("detected_risks") or []],
                *[
                    str(reason)
                    for reason in audit_response.get("rejection_reasons") or []
                ],
            ]
        )

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {"value": str(value)}
        return {"value": str(value)}

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

    def _publish(self, result: ExecutionBlockResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_execution_blocking_result",
        ):
            self.status.mark_execution_blocking_result(result.to_dict())

    def _log_result(self, result: ExecutionBlockResult) -> None:
        if result.status == BLOCK_STATUS_ERROR:
            logger.error(
                "execution_blocking: error block_id=%s error=%s",
                result.block_id,
                result.error,
            )
            return
        if result.status == BLOCK_STATUS_BLOCKED:
            logger.warning(
                "execution_blocking: invalid block_id=%s reasons=%s",
                result.block_id,
                ",".join(result.reasons),
            )
            return
        logger.warning(
            "execution_blocking: active block_id=%s type=%s class=%s reason=%s",
            result.block_id,
            result.block_type,
            result.block_classification,
            result.block_reason,
        )
