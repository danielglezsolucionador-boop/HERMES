"""
Controlled continuation safety for Hermes runtime.

This layer validates whether an automatic continuation candidate is safe. It
can allow, warn, block, or require critical escalation, but it does not execute
workflows, override governance, or alter the runtime loop.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.workflow_chaining import WorkflowChainingResult

logger = logging.getLogger(__name__)

SAFETY_TYPE_GOVERNANCE = "governance"
SAFETY_TYPE_AUDIT = "audit"
SAFETY_TYPE_SECURITY = "security"
SAFETY_TYPE_RUNTIME = "runtime"
SAFETY_TYPE_DEPENDENCY = "dependency"
SAFETY_TYPE_EXECUTION = "execution"
SUPPORTED_SAFETY_TYPES = {
    SAFETY_TYPE_GOVERNANCE,
    SAFETY_TYPE_AUDIT,
    SAFETY_TYPE_SECURITY,
    SAFETY_TYPE_RUNTIME,
    SAFETY_TYPE_DEPENDENCY,
    SAFETY_TYPE_EXECUTION,
}

SAFETY_STATUS_SAFE = "safe_continuation"
SAFETY_STATUS_WARNING = "warning_continuation"
SAFETY_STATUS_BLOCKED = "blocked_continuation"
SAFETY_STATUS_CRITICAL = "critical_continuation"
SAFETY_STATUS_ERROR = "error"

APPROVED_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "authorized_by_human",
    "governance_approved",
}
APPROVED_AUDIT_STATUSES = {"approved", "approved_with_warnings"}
SAFE_RUNTIME_STATES = {"active", "online", "ready", "stable"}
COMPLETE_DEPENDENCY_STATUSES = {"satisfied", "complete", "completed", "ready"}
STABLE_EXECUTION_STATUSES = {"completed", "stable", "validated", "resumed"}
SAFE_SECURITY_STATUSES = {"clear", "safe", "not_required", "none", "approved"}
WARNING_RISK_LEVELS = {"low", "elevated", "warning"}
CRITICAL_RISK_LEVELS = {"critical", "severe", "security_block"}
SECURITY_ESCALATION_HINTS = (
    "centinela",
    "security_escalation",
    "security_block",
    "quarantine",
    "runtime compromise",
    "malicious",
    "credential",
    "secret",
)


@dataclass(frozen=True)
class ContinuationSafetyRequest:
    execution_id: str | None = None
    task_id: str | None = None
    safety_type: str = SAFETY_TYPE_EXECUTION
    current_workflow: str | None = None
    next_workflow: str | None = None
    continuation_status: str | None = None
    governance_status: str | None = None
    audit_status: str | None = None
    security_status: str | None = None
    dependency_status: str | None = None
    execution_status: str | None = None
    risk_level: str | None = None
    runtime_state: dict[str, Any] = field(default_factory=dict)
    workflow_chaining: WorkflowChainingResult | dict[str, Any] | Any | None = None
    execution_blocking: dict[str, Any] | Any | None = None
    approval_gate: dict[str, Any] | Any | None = None
    audit_response: dict[str, Any] | Any | None = None
    detected_risks: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    security_events: tuple[Any, ...] = field(default_factory=tuple)
    continuation_logs: tuple[Any, ...] = field(default_factory=tuple)
    execution_context: dict[str, Any] = field(default_factory=dict)
    governance_history: tuple[Any, ...] = field(default_factory=tuple)
    audit_history: tuple[Any, ...] = field(default_factory=tuple)
    workflow_history: tuple[Any, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContinuationSafetyResult:
    status: str
    success: bool
    safety_id: str
    execution_id: str | None
    task_id: str | None
    safety_type: str | None
    current_workflow: str | None
    next_workflow: str | None
    continuation_status: str
    governance_status: str | None
    audit_status: str | None
    security_status: str | None
    risk_level: str
    governance_valid: bool
    audit_valid: bool
    security_clear: bool
    runtime_stable: bool
    dependencies_complete: bool
    execution_consistent: bool
    workflow_integrity: bool
    continuation_allowed: bool
    human_review_required: bool
    sentinel_escalation_required: bool
    centinela_escalation_required: bool
    autonomy_limited: bool
    context_preserved: bool
    traceability_preserved: bool
    detected_risks: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    security_events: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    continuation_logs: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    execution_context: dict[str, Any] = field(default_factory=dict)
    governance_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    audit_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    workflow_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    safety_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "safety_type": self.safety_type,
            "current_workflow": self.current_workflow,
            "next_workflow": self.next_workflow,
            "continuation_status": self.continuation_status,
            "governance_status": self.governance_status,
            "audit_status": self.audit_status,
            "security_status": self.security_status,
            "risk_level": self.risk_level,
            "governance_valid": self.governance_valid,
            "audit_valid": self.audit_valid,
            "security_clear": self.security_clear,
            "runtime_stable": self.runtime_stable,
            "dependencies_complete": self.dependencies_complete,
            "execution_consistent": self.execution_consistent,
            "workflow_integrity": self.workflow_integrity,
            "continuation_allowed": self.continuation_allowed,
            "human_review_required": self.human_review_required,
            "sentinel_escalation_required": self.sentinel_escalation_required,
            "centinela_escalation_required": (
                self.centinela_escalation_required
            ),
            "autonomy_limited": self.autonomy_limited,
            "context_preserved": self.context_preserved,
            "traceability_preserved": self.traceability_preserved,
            "detected_risks": list(self.detected_risks),
            "warnings": list(self.warnings),
            "security_events": [
                dict(entry) for entry in self.security_events
            ],
            "continuation_logs": [
                dict(entry) for entry in self.continuation_logs
            ],
            "execution_context": dict(self.execution_context),
            "governance_history": [
                dict(entry) for entry in self.governance_history
            ],
            "audit_history": [dict(entry) for entry in self.audit_history],
            "workflow_history": [
                dict(entry) for entry in self.workflow_history
            ],
            "safety_lifecycle": [
                dict(entry) for entry in self.safety_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class ContinuationSafety:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def validate(
        self,
        request: ContinuationSafetyRequest,
        runtime_active: bool = True,
        safety_permitted: bool = True,
    ) -> ContinuationSafetyResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        safety_id = str(uuid4())

        try:
            workflow_chaining = self._as_dict(request.workflow_chaining)
            execution_blocking = self._as_dict(request.execution_blocking)
            approval_gate = self._as_dict(request.approval_gate)
            audit_response = self._as_dict(request.audit_response)
            safety_type = self._normalize(request.safety_type)
            governance_status = self._governance_status(
                request,
                workflow_chaining,
                approval_gate,
            )
            audit_status = self._audit_status(
                request,
                workflow_chaining,
                audit_response,
            )
            security_status = self._security_status(request, audit_response)
            risk_level = self._risk_level(request, audit_response)
            continuation_status = self._continuation_status(
                request,
                workflow_chaining,
            )
            current_workflow = (
                request.current_workflow or workflow_chaining.get("current_workflow")
            )
            next_workflow = request.next_workflow or workflow_chaining.get(
                "next_workflow"
            )
            checks = {
                "governance_valid": (
                    governance_status in APPROVED_GOVERNANCE_STATUSES
                ),
                "audit_valid": audit_status in APPROVED_AUDIT_STATUSES,
                "security_clear": self._security_clear(
                    security_status,
                    risk_level,
                    request,
                    audit_response,
                ),
                "runtime_stable": self._runtime_stable(
                    runtime_active,
                    request.runtime_state,
                    workflow_chaining,
                ),
                "dependencies_complete": self._dependencies_complete(
                    request,
                    workflow_chaining,
                ),
                "execution_consistent": self._execution_consistent(
                    request,
                    workflow_chaining,
                    execution_blocking,
                ),
                "workflow_integrity": self._workflow_integrity(
                    request,
                    workflow_chaining,
                ),
            }
            reasons = self._validation_reasons(
                request=request,
                safety_type=safety_type,
                checks=checks,
                runtime_active=runtime_active,
                safety_permitted=safety_permitted,
            )
            decision = self._decision(
                checks=checks,
                risk_level=risk_level,
                warnings=request.warnings,
                reasons=reasons,
                security_status=security_status,
            )
            result = self._result(
                status=str(decision["status"]),
                success=bool(decision["success"]),
                safety_id=safety_id,
                request=request,
                safety_type=safety_type,
                current_workflow=current_workflow,
                next_workflow=next_workflow,
                continuation_status=continuation_status,
                governance_status=governance_status,
                audit_status=audit_status,
                security_status=security_status,
                risk_level=risk_level,
                checks=checks,
                continuation_allowed=bool(decision["continuation_allowed"]),
                human_review_required=bool(decision["human_review_required"]),
                sentinel_escalation_required=bool(
                    decision["sentinel_escalation_required"]
                ),
                centinela_escalation_required=bool(
                    decision["centinela_escalation_required"]
                ),
                autonomy_limited=bool(decision["autonomy_limited"]),
                lifecycle=(
                    self._lifecycle("continuation_request_received"),
                    self._lifecycle("safety_validated"),
                    self._lifecycle(str(decision["status"])),
                ),
                reasons=list(decision["reasons"]),
                error=None if decision["success"] else ";".join(decision["reasons"]),
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
        request: ContinuationSafetyRequest,
        safety_type: str | None,
        current_workflow: str | None,
        next_workflow: str | None,
        continuation_status: str,
        governance_status: str | None,
        audit_status: str | None,
        security_status: str | None,
        risk_level: str,
        checks: dict[str, bool],
        continuation_allowed: bool,
        human_review_required: bool,
        sentinel_escalation_required: bool,
        centinela_escalation_required: bool,
        autonomy_limited: bool,
        lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> ContinuationSafetyResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        return ContinuationSafetyResult(
            status=status,
            success=success,
            safety_id=safety_id,
            execution_id=request.execution_id,
            task_id=request.task_id,
            safety_type=safety_type,
            current_workflow=current_workflow,
            next_workflow=next_workflow,
            continuation_status=continuation_status,
            governance_status=governance_status,
            audit_status=audit_status,
            security_status=security_status,
            risk_level=risk_level,
            governance_valid=checks["governance_valid"],
            audit_valid=checks["audit_valid"],
            security_clear=checks["security_clear"],
            runtime_stable=checks["runtime_stable"],
            dependencies_complete=checks["dependencies_complete"],
            execution_consistent=checks["execution_consistent"],
            workflow_integrity=checks["workflow_integrity"],
            continuation_allowed=continuation_allowed,
            human_review_required=human_review_required,
            sentinel_escalation_required=sentinel_escalation_required,
            centinela_escalation_required=centinela_escalation_required,
            autonomy_limited=autonomy_limited,
            context_preserved=True,
            traceability_preserved=True,
            detected_risks=tuple(request.detected_risks),
            warnings=tuple(request.warnings),
            security_events=tuple(
                self._as_dict(entry) for entry in request.security_events
            ),
            continuation_logs=tuple(
                self._as_dict(entry) for entry in request.continuation_logs
            ),
            execution_context=dict(request.execution_context or {}),
            governance_history=tuple(
                self._as_dict(entry) for entry in request.governance_history
            ),
            audit_history=tuple(
                self._as_dict(entry) for entry in request.audit_history
            ),
            workflow_history=tuple(
                self._as_dict(entry) for entry in request.workflow_history
            ),
            safety_lifecycle=lifecycle,
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            reasons=tuple(reasons or []),
            error=error,
            metadata=dict(request.metadata),
        )

    def _validation_reasons(
        self,
        request: ContinuationSafetyRequest,
        safety_type: str | None,
        checks: dict[str, bool],
        runtime_active: bool,
        safety_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not safety_permitted:
            reasons.append("continuation_safety_not_permitted")
        if safety_type not in SUPPORTED_SAFETY_TYPES:
            reasons.append("unsupported_safety_type")
        if not request.execution_id:
            reasons.append("missing_execution_id")
        if not checks["governance_valid"]:
            reasons.append("governance_approval_required")
        if not checks["audit_valid"]:
            reasons.append("approved_audit_required")
        if not checks["security_clear"]:
            reasons.append("security_clearance_required")
        if not checks["runtime_stable"]:
            reasons.append("runtime_stability_required")
        if not checks["dependencies_complete"]:
            reasons.append("dependency_completion_required")
        if not checks["execution_consistent"]:
            reasons.append("execution_consistency_required")
        if not checks["workflow_integrity"]:
            reasons.append("workflow_integrity_required")
        return self._unique(reasons)

    def _decision(
        self,
        checks: dict[str, bool],
        risk_level: str,
        warnings: tuple[str, ...],
        reasons: list[str],
        security_status: str | None,
    ) -> dict[str, Any]:
        critical = (
            risk_level in CRITICAL_RISK_LEVELS
            or security_status in {"security_block", "centinela_escalated"}
            or "security_clearance_required" in reasons
            and risk_level in CRITICAL_RISK_LEVELS
        )
        if critical:
            return {
                "status": SAFETY_STATUS_CRITICAL,
                "success": False,
                "continuation_allowed": False,
                "human_review_required": True,
                "sentinel_escalation_required": True,
                "centinela_escalation_required": True,
                "autonomy_limited": True,
                "reasons": self._unique(
                    [*reasons, "critical_security_escalation_required"]
                ),
            }
        if reasons:
            return {
                "status": SAFETY_STATUS_BLOCKED,
                "success": False,
                "continuation_allowed": False,
                "human_review_required": True,
                "sentinel_escalation_required": True,
                "centinela_escalation_required": False,
                "autonomy_limited": True,
                "reasons": reasons,
            }
        if warnings or risk_level in WARNING_RISK_LEVELS:
            return {
                "status": SAFETY_STATUS_WARNING,
                "success": True,
                "continuation_allowed": True,
                "human_review_required": True,
                "sentinel_escalation_required": False,
                "centinela_escalation_required": False,
                "autonomy_limited": True,
                "reasons": self._unique(
                    ["warning_continuation_requires_visibility", *warnings]
                ),
            }
        if checks["audit_valid"]:
            return {
                "status": SAFETY_STATUS_SAFE,
                "success": True,
                "continuation_allowed": True,
                "human_review_required": False,
                "sentinel_escalation_required": False,
                "centinela_escalation_required": False,
                "autonomy_limited": False,
                "reasons": ["safe_continuation_validated"],
            }
        return {
            "status": SAFETY_STATUS_BLOCKED,
            "success": False,
            "continuation_allowed": False,
            "human_review_required": True,
            "sentinel_escalation_required": True,
            "centinela_escalation_required": False,
            "autonomy_limited": True,
            "reasons": reasons or ["continuation_blocked"],
        }

    def _governance_status(
        self,
        request: ContinuationSafetyRequest,
        workflow_chaining: dict[str, Any],
        approval_gate: dict[str, Any],
    ) -> str | None:
        value = (
            request.governance_status
            or workflow_chaining.get("governance_status")
            or approval_gate.get("governance_status")
            or approval_gate.get("approval_status")
        )
        return self._normalize(value)

    def _audit_status(
        self,
        request: ContinuationSafetyRequest,
        workflow_chaining: dict[str, Any],
        audit_response: dict[str, Any],
    ) -> str | None:
        value = (
            request.audit_status
            or workflow_chaining.get("audit_status")
            or audit_response.get("audit_result")
            or audit_response.get("status")
        )
        return self._normalize(value)

    def _security_status(
        self,
        request: ContinuationSafetyRequest,
        audit_response: dict[str, Any],
    ) -> str | None:
        if audit_response.get("centinela_escalation") is True:
            return "centinela_escalated"
        value = (
            request.security_status
            or audit_response.get("security_escalation_status")
            or audit_response.get("security_status")
        )
        normalized = self._normalize(value)
        if normalized in {"not_evaluated", "not_required"}:
            return "not_required"
        return normalized or "clear"

    def _risk_level(
        self,
        request: ContinuationSafetyRequest,
        audit_response: dict[str, Any],
    ) -> str:
        value = request.risk_level or audit_response.get("risk_level")
        normalized = self._normalize(value)
        if normalized in {"none", "ok", "safe"}:
            return "clear"
        if normalized in {"minor", "warning", "warnings"}:
            return "low"
        if normalized in {"medium", "moderate"}:
            return "elevated"
        if normalized in {"high", "severe"}:
            return "critical"
        if normalized:
            return normalized
        text = self._risk_text(request, audit_response)
        if any(hint in text for hint in SECURITY_ESCALATION_HINTS):
            return "critical"
        return "clear"

    def _continuation_status(
        self,
        request: ContinuationSafetyRequest,
        workflow_chaining: dict[str, Any],
    ) -> str:
        return (
            request.continuation_status
            or workflow_chaining.get("continuation_status")
            or "candidate"
        )

    def _security_clear(
        self,
        security_status: str | None,
        risk_level: str,
        request: ContinuationSafetyRequest,
        audit_response: dict[str, Any],
    ) -> bool:
        if risk_level in CRITICAL_RISK_LEVELS:
            return False
        if security_status not in SAFE_SECURITY_STATUSES:
            return False
        text = self._risk_text(request, audit_response)
        return not any(hint in text for hint in SECURITY_ESCALATION_HINTS)

    def _runtime_stable(
        self,
        runtime_active: bool,
        runtime_state: dict[str, Any],
        workflow_chaining: dict[str, Any],
    ) -> bool:
        if not runtime_active:
            return False
        if workflow_chaining.get("runtime_safe") is True:
            return True
        values = (
            runtime_state.get("state"),
            runtime_state.get("status"),
            runtime_state.get("loop_state"),
        )
        return any(self._normalize(value) in SAFE_RUNTIME_STATES for value in values)

    def _dependencies_complete(
        self,
        request: ContinuationSafetyRequest,
        workflow_chaining: dict[str, Any],
    ) -> bool:
        if workflow_chaining.get("dependencies_satisfied") is True:
            return True
        status = self._normalize(
            request.dependency_status or workflow_chaining.get("dependency_status")
        )
        return status in COMPLETE_DEPENDENCY_STATUSES

    def _execution_consistent(
        self,
        request: ContinuationSafetyRequest,
        workflow_chaining: dict[str, Any],
        execution_blocking: dict[str, Any],
    ) -> bool:
        if execution_blocking.get("status") == "active":
            return False
        if execution_blocking.get("continuation_blocked") is True:
            return False
        value = (
            request.execution_status
            or workflow_chaining.get("execution_status")
            or request.execution_context.get("status")
        )
        return self._normalize(value) in STABLE_EXECUTION_STATUSES

    def _workflow_integrity(
        self,
        request: ContinuationSafetyRequest,
        workflow_chaining: dict[str, Any],
    ) -> bool:
        status = self._normalize(workflow_chaining.get("status"))
        if workflow_chaining and status not in {"activated", "completed"}:
            return False
        if workflow_chaining.get("workflow_activation") is False:
            return workflow_chaining.get("status") == "completed"
        if request.current_workflow and request.next_workflow:
            return request.current_workflow != request.next_workflow
        return True

    def _risk_text(
        self,
        request: ContinuationSafetyRequest,
        audit_response: dict[str, Any],
    ) -> str:
        values = {
            "detected_risks": list(request.detected_risks),
            "warnings": list(request.warnings),
            "security_events": list(request.security_events),
            "audit_response": audit_response,
        }
        return json.dumps(values, sort_keys=True, default=str).lower()

    def _error_result(
        self,
        safety_id: str,
        request: ContinuationSafetyRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> ContinuationSafetyResult:
        return self._result(
            status=SAFETY_STATUS_ERROR,
            success=False,
            safety_id=safety_id,
            request=request,
            safety_type=self._normalize(request.safety_type),
            current_workflow=request.current_workflow,
            next_workflow=request.next_workflow,
            continuation_status=request.continuation_status or "blocked_error",
            governance_status=request.governance_status,
            audit_status=request.audit_status,
            security_status=request.security_status,
            risk_level=request.risk_level or "unknown",
            checks={
                "governance_valid": False,
                "audit_valid": False,
                "security_clear": False,
                "runtime_stable": False,
                "dependencies_complete": False,
                "execution_consistent": False,
                "workflow_integrity": False,
            },
            continuation_allowed=False,
            human_review_required=True,
            sentinel_escalation_required=True,
            centinela_escalation_required=False,
            autonomy_limited=True,
            lifecycle=(self._lifecycle(SAFETY_STATUS_ERROR),),
            reasons=["continuation_safety_error_contained"],
            error=error,
            started=started,
            started_at=started_at,
        )

    def _normalize(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower().replace("-", "_").replace(" ", "_")

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, WorkflowChainingResult):
            return value.to_dict()
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

    def _publish(self, result: ContinuationSafetyResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_continuation_safety_result",
        ):
            self.status.mark_continuation_safety_result(result.to_dict())

    def _log_result(self, result: ContinuationSafetyResult) -> None:
        if result.status == SAFETY_STATUS_ERROR:
            logger.error(
                "continuation_safety: error safety_id=%s error=%s",
                result.safety_id,
                result.error,
            )
            return
        if result.status in {SAFETY_STATUS_BLOCKED, SAFETY_STATUS_CRITICAL}:
            logger.warning(
                "continuation_safety: %s safety_id=%s reasons=%s",
                result.status,
                result.safety_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "continuation_safety: %s safety_id=%s execution_id=%s",
            result.status,
            result.safety_id,
            result.execution_id,
        )
