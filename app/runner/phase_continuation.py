"""
Controlled phase continuation for Hermes runtime.

This layer reads an explicit roadmap context, detects the next subphase, and
validates whether continuation is allowed. It does not execute the next
workflow, skip subphases, modify roadmap files, or bypass audit/governance.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.approval_gate import ApprovalGateResult
from app.runner.audit_response_control import AuditResponseControlResult
from app.runner.execution_blocking import ExecutionBlockResult

logger = logging.getLogger(__name__)

CONTINUATION_TYPE_PHASE = "phase"
CONTINUATION_TYPE_SUBPHASE = "subphase"
CONTINUATION_TYPE_EXECUTION = "execution"
CONTINUATION_TYPE_AUDIT = "audit"
CONTINUATION_TYPE_GOVERNANCE = "governance"
SUPPORTED_CONTINUATION_TYPES = {
    CONTINUATION_TYPE_PHASE,
    CONTINUATION_TYPE_SUBPHASE,
    CONTINUATION_TYPE_EXECUTION,
    CONTINUATION_TYPE_AUDIT,
    CONTINUATION_TYPE_GOVERNANCE,
}

CONTINUATION_STATUS_READY = "ready"
CONTINUATION_STATUS_BLOCKED = "blocked"
CONTINUATION_STATUS_COMPLETED = "completed"
CONTINUATION_STATUS_ERROR = "error"

APPROVED_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "authorized_by_human",
}
APPROVED_AUDIT_STATUSES = {"approved", "approved_with_warnings"}
STABLE_EXECUTION_STATUSES = {"completed", "stable", "validated"}
SAFE_RUNTIME_STATES = {"active", "online", "ready", "stable"}


@dataclass(frozen=True)
class PhaseContinuationRequest:
    current_phase: str | None = None
    current_subphase: str | None = None
    next_subphase: str | None = None
    continuation_type: str = CONTINUATION_TYPE_SUBPHASE
    roadmap: tuple[str, ...] = field(default_factory=tuple)
    completed_subphases: tuple[str, ...] = field(default_factory=tuple)
    dependencies: dict[str, tuple[str, ...] | list[str]] = field(default_factory=dict)
    governance_status: str | None = None
    audit_status: str | None = None
    execution_status: str | None = None
    runtime_state: dict[str, Any] = field(default_factory=dict)
    approval_gate: ApprovalGateResult | dict[str, Any] | Any | None = None
    audit_response: AuditResponseControlResult | dict[str, Any] | Any | None = None
    execution_blocking: ExecutionBlockResult | dict[str, Any] | Any | None = None
    execution_context: dict[str, Any] = field(default_factory=dict)
    lifecycle_history: tuple[Any, ...] = field(default_factory=tuple)
    audit_history: tuple[Any, ...] = field(default_factory=tuple)
    governance_history: tuple[Any, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PhaseContinuationResult:
    status: str
    success: bool
    continuation_id: str
    current_phase: str | None
    current_subphase: str | None
    next_subphase: str | None
    continuation_type: str | None
    governance_status: str | None
    audit_status: str | None
    execution_status: str | None
    continuation_status: str
    roadmap_loaded: bool
    dependencies_satisfied: bool
    governance_satisfied: bool
    audit_satisfied: bool
    execution_stable: bool
    runtime_safe: bool
    context_preserved: bool
    traceability_preserved: bool
    progression_allowed: bool
    roadmap: tuple[str, ...] = field(default_factory=tuple)
    completed_subphases: tuple[str, ...] = field(default_factory=tuple)
    required_dependencies: tuple[str, ...] = field(default_factory=tuple)
    missing_dependencies: tuple[str, ...] = field(default_factory=tuple)
    execution_context: dict[str, Any] = field(default_factory=dict)
    lifecycle_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    audit_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    governance_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    continuation_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "continuation_id": self.continuation_id,
            "current_phase": self.current_phase,
            "current_subphase": self.current_subphase,
            "next_subphase": self.next_subphase,
            "continuation_type": self.continuation_type,
            "governance_status": self.governance_status,
            "audit_status": self.audit_status,
            "execution_status": self.execution_status,
            "continuation_status": self.continuation_status,
            "roadmap_loaded": self.roadmap_loaded,
            "dependencies_satisfied": self.dependencies_satisfied,
            "governance_satisfied": self.governance_satisfied,
            "audit_satisfied": self.audit_satisfied,
            "execution_stable": self.execution_stable,
            "runtime_safe": self.runtime_safe,
            "context_preserved": self.context_preserved,
            "traceability_preserved": self.traceability_preserved,
            "progression_allowed": self.progression_allowed,
            "roadmap": list(self.roadmap),
            "completed_subphases": list(self.completed_subphases),
            "required_dependencies": list(self.required_dependencies),
            "missing_dependencies": list(self.missing_dependencies),
            "execution_context": dict(self.execution_context),
            "lifecycle_history": [dict(entry) for entry in self.lifecycle_history],
            "audit_history": [dict(entry) for entry in self.audit_history],
            "governance_history": [
                dict(entry) for entry in self.governance_history
            ],
            "continuation_lifecycle": [
                dict(entry) for entry in self.continuation_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class PhaseContinuation:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def evaluate(
        self,
        request: PhaseContinuationRequest,
        runtime_active: bool = True,
        continuation_permitted: bool = True,
    ) -> PhaseContinuationResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        continuation_id = str(uuid4())

        try:
            approval_gate = self._as_dict(request.approval_gate)
            audit_response = self._as_dict(request.audit_response)
            execution_blocking = self._as_dict(request.execution_blocking)
            governance_status = self._governance_status(request, approval_gate)
            audit_status = self._audit_status(request, audit_response)
            execution_status = self._execution_status(request)
            next_subphase = self._next_subphase(request)
            required_dependencies = self._dependencies(request, next_subphase)
            missing_dependencies = tuple(
                dependency
                for dependency in required_dependencies
                if dependency not in set(request.completed_subphases)
            )
            checks = {
                "roadmap_loaded": bool(request.roadmap),
                "dependencies_satisfied": not missing_dependencies,
                "governance_satisfied": (
                    governance_status in APPROVED_GOVERNANCE_STATUSES
                ),
                "audit_satisfied": audit_status in APPROVED_AUDIT_STATUSES,
                "execution_stable": execution_status in STABLE_EXECUTION_STATUSES,
                "runtime_safe": self._runtime_safe(request, execution_blocking),
            }
            reasons = self._reasons(
                request=request,
                next_subphase=next_subphase,
                checks=checks,
                missing_dependencies=missing_dependencies,
                runtime_active=runtime_active,
                continuation_permitted=continuation_permitted,
            )
            completed = bool(request.roadmap) and next_subphase is None and not reasons
            if reasons:
                result = self._result(
                    status=CONTINUATION_STATUS_BLOCKED,
                    success=False,
                    continuation_id=continuation_id,
                    request=request,
                    next_subphase=next_subphase,
                    governance_status=governance_status,
                    audit_status=audit_status,
                    execution_status=execution_status,
                    continuation_status="blocked_phase_continuation",
                    checks=checks,
                    required_dependencies=required_dependencies,
                    missing_dependencies=missing_dependencies,
                    progression_allowed=False,
                    lifecycle=(
                        self._lifecycle("roadmap_loaded"),
                        self._lifecycle(CONTINUATION_STATUS_BLOCKED),
                    ),
                    reasons=reasons,
                    error=";".join(reasons),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            result = self._result(
                status=(
                    CONTINUATION_STATUS_COMPLETED
                    if completed
                    else CONTINUATION_STATUS_READY
                ),
                success=True,
                continuation_id=continuation_id,
                request=request,
                next_subphase=next_subphase,
                governance_status=governance_status,
                audit_status=audit_status,
                execution_status=execution_status,
                continuation_status=(
                    "roadmap_completed"
                    if completed
                    else "ready_for_next_subphase"
                ),
                checks=checks,
                required_dependencies=required_dependencies,
                missing_dependencies=missing_dependencies,
                progression_allowed=not completed,
                lifecycle=(
                    self._lifecycle("roadmap_loaded"),
                    self._lifecycle("state_identified"),
                    self._lifecycle("next_step_detected"),
                    self._lifecycle("continuation_validated"),
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
            result = self._result(
                status=CONTINUATION_STATUS_ERROR,
                success=False,
                continuation_id=continuation_id,
                request=request,
                next_subphase=None,
                governance_status=request.governance_status,
                audit_status=request.audit_status,
                execution_status=request.execution_status,
                continuation_status="blocked_phase_continuation_error",
                checks={
                    "roadmap_loaded": False,
                    "dependencies_satisfied": False,
                    "governance_satisfied": False,
                    "audit_satisfied": False,
                    "execution_stable": False,
                    "runtime_safe": False,
                },
                required_dependencies=tuple(),
                missing_dependencies=tuple(),
                progression_allowed=False,
                lifecycle=(self._lifecycle(CONTINUATION_STATUS_ERROR),),
                reasons=["phase_continuation_error_contained"],
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
        continuation_id: str,
        request: PhaseContinuationRequest,
        next_subphase: str | None,
        governance_status: str | None,
        audit_status: str | None,
        execution_status: str | None,
        continuation_status: str,
        checks: dict[str, bool],
        required_dependencies: tuple[str, ...],
        missing_dependencies: tuple[str, ...],
        progression_allowed: bool,
        lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> PhaseContinuationResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        return PhaseContinuationResult(
            status=status,
            success=success,
            continuation_id=continuation_id,
            current_phase=request.current_phase,
            current_subphase=request.current_subphase,
            next_subphase=next_subphase,
            continuation_type=self._continuation_type(request),
            governance_status=governance_status,
            audit_status=audit_status,
            execution_status=execution_status,
            continuation_status=continuation_status,
            roadmap_loaded=checks["roadmap_loaded"],
            dependencies_satisfied=checks["dependencies_satisfied"],
            governance_satisfied=checks["governance_satisfied"],
            audit_satisfied=checks["audit_satisfied"],
            execution_stable=checks["execution_stable"],
            runtime_safe=checks["runtime_safe"],
            context_preserved=True,
            traceability_preserved=True,
            progression_allowed=progression_allowed,
            roadmap=tuple(request.roadmap),
            completed_subphases=tuple(request.completed_subphases),
            required_dependencies=required_dependencies,
            missing_dependencies=missing_dependencies,
            execution_context=dict(request.execution_context or {}),
            lifecycle_history=tuple(
                self._as_dict(entry) for entry in request.lifecycle_history
            ),
            audit_history=tuple(
                self._as_dict(entry) for entry in request.audit_history
            ),
            governance_history=tuple(
                self._as_dict(entry) for entry in request.governance_history
            ),
            continuation_lifecycle=lifecycle,
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            reasons=tuple(reasons or []),
            error=error,
            metadata=dict(request.metadata),
        )

    def _reasons(
        self,
        request: PhaseContinuationRequest,
        next_subphase: str | None,
        checks: dict[str, bool],
        missing_dependencies: tuple[str, ...],
        runtime_active: bool,
        continuation_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        continuation_type = self._continuation_type(request)
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not continuation_permitted:
            reasons.append("phase_continuation_not_permitted")
        if continuation_type not in SUPPORTED_CONTINUATION_TYPES:
            reasons.append("unsupported_continuation_type")
        if not request.current_phase:
            reasons.append("missing_current_phase")
        if not request.current_subphase:
            reasons.append("missing_current_subphase")
        if not checks["roadmap_loaded"]:
            reasons.append("missing_roadmap")
        elif request.current_subphase not in request.roadmap:
            reasons.append("current_subphase_not_in_roadmap")
        if request.next_subphase and request.next_subphase != next_subphase:
            reasons.append("phase_skipping_detected")
        if next_subphase is not None and not checks["dependencies_satisfied"]:
            reasons.extend(
                f"missing_dependency:{dependency}"
                for dependency in missing_dependencies
            )
        if next_subphase is not None and not checks["governance_satisfied"]:
            reasons.append("governance_approval_required")
        if next_subphase is not None and not checks["audit_satisfied"]:
            reasons.append("approved_audit_required")
        if next_subphase is not None and not checks["execution_stable"]:
            reasons.append("stable_execution_required")
        if next_subphase is not None and not checks["runtime_safe"]:
            reasons.append("runtime_safety_required")
        return self._unique(reasons)

    def _next_subphase(self, request: PhaseContinuationRequest) -> str | None:
        if not request.roadmap or not request.current_subphase:
            return None
        if request.current_subphase not in request.roadmap:
            return None
        index = request.roadmap.index(request.current_subphase)
        next_index = index + 1
        if next_index >= len(request.roadmap):
            return None
        return request.roadmap[next_index]

    def _dependencies(
        self,
        request: PhaseContinuationRequest,
        next_subphase: str | None,
    ) -> tuple[str, ...]:
        if not next_subphase:
            return tuple()
        values = request.dependencies.get(next_subphase) or []
        return tuple(str(value) for value in values if value)

    def _governance_status(
        self,
        request: PhaseContinuationRequest,
        approval_gate: dict[str, Any],
    ) -> str | None:
        value = (
            request.governance_status
            or approval_gate.get("governance_status")
            or approval_gate.get("approval_status")
            or approval_gate.get("continuation_status")
        )
        return self._normalize(value)

    def _audit_status(
        self,
        request: PhaseContinuationRequest,
        audit_response: dict[str, Any],
    ) -> str | None:
        value = request.audit_status or audit_response.get("audit_result")
        return self._normalize(value)

    def _execution_status(self, request: PhaseContinuationRequest) -> str | None:
        value = request.execution_status or request.execution_context.get("status")
        return self._normalize(value)

    def _runtime_safe(
        self,
        request: PhaseContinuationRequest,
        execution_blocking: dict[str, Any],
    ) -> bool:
        if execution_blocking.get("status") == "active":
            return False
        if execution_blocking.get("continuation_blocked") is True:
            return False
        state = (
            request.runtime_state.get("state")
            or request.runtime_state.get("status")
            or request.runtime_state.get("loop_state")
        )
        if state is None:
            return False
        return self._normalize(state) in SAFE_RUNTIME_STATES

    def _continuation_type(self, request: PhaseContinuationRequest) -> str:
        return str(request.continuation_type or "").strip().lower()

    def _normalize(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower().replace("-", "_").replace(" ", "_")

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        for cls in (ApprovalGateResult, AuditResponseControlResult, ExecutionBlockResult):
            if isinstance(value, cls):
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

    def _publish(self, result: PhaseContinuationResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_phase_continuation_result",
        ):
            self.status.mark_phase_continuation_result(result.to_dict())

    def _log_result(self, result: PhaseContinuationResult) -> None:
        if result.status == CONTINUATION_STATUS_ERROR:
            logger.error(
                "phase_continuation: error continuation_id=%s error=%s",
                result.continuation_id,
                result.error,
            )
            return
        if result.status == CONTINUATION_STATUS_BLOCKED:
            logger.warning(
                "phase_continuation: blocked continuation_id=%s reasons=%s",
                result.continuation_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "phase_continuation: %s continuation_id=%s current=%s next=%s",
            result.status,
            result.continuation_id,
            result.current_subphase,
            result.next_subphase,
        )
