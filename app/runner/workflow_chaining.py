"""
Controlled workflow chaining for Hermes runtime.

This layer identifies the next roadmap workflow and records a safe chaining
decision when completion, dependencies, runtime stability, audit, and
governance are valid. It does not execute roadmap files, skip subphases,
mutate tasks, or bypass human/audit controls.
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
from app.runner.execution_resume import ExecutionResumeResult
from app.runner.phase_continuation import PhaseContinuationResult

logger = logging.getLogger(__name__)

CHAINING_TYPE_PHASE = "phase"
CHAINING_TYPE_SUBPHASE = "subphase"
CHAINING_TYPE_EXECUTION = "execution"
CHAINING_TYPE_GOVERNANCE = "governance"
CHAINING_TYPE_AUDIT = "audit"
SUPPORTED_CHAINING_TYPES = {
    CHAINING_TYPE_PHASE,
    CHAINING_TYPE_SUBPHASE,
    CHAINING_TYPE_EXECUTION,
    CHAINING_TYPE_GOVERNANCE,
    CHAINING_TYPE_AUDIT,
}

CHAINING_STATUS_ACTIVATED = "activated"
CHAINING_STATUS_BLOCKED = "blocked"
CHAINING_STATUS_COMPLETED = "completed"
CHAINING_STATUS_ERROR = "error"

APPROVED_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "authorized_by_human",
    "governance_approved",
}
APPROVED_AUDIT_STATUSES = {"approved", "approved_with_warnings"}
STABLE_EXECUTION_STATUSES = {"completed", "stable", "validated", "resumed"}
SAFE_RUNTIME_STATES = {"active", "online", "ready", "stable"}


@dataclass(frozen=True)
class WorkflowChainingRequest:
    current_workflow: str | None = None
    next_workflow: str | None = None
    current_phase: str | None = None
    current_subphase: str | None = None
    chaining_type: str = CHAINING_TYPE_SUBPHASE
    roadmap: tuple[str, ...] = field(default_factory=tuple)
    completed_workflows: tuple[str, ...] = field(default_factory=tuple)
    dependencies: dict[str, tuple[str, ...] | list[str]] = field(default_factory=dict)
    governance_status: str | None = None
    audit_status: str | None = None
    execution_status: str | None = None
    runtime_state: dict[str, Any] = field(default_factory=dict)
    phase_continuation: PhaseContinuationResult | dict[str, Any] | Any | None = None
    execution_resume: ExecutionResumeResult | dict[str, Any] | Any | None = None
    approval_gate: ApprovalGateResult | dict[str, Any] | Any | None = None
    audit_response: AuditResponseControlResult | dict[str, Any] | Any | None = None
    execution_context: dict[str, Any] = field(default_factory=dict)
    lifecycle_history: tuple[Any, ...] = field(default_factory=tuple)
    roadmap_history: tuple[Any, ...] = field(default_factory=tuple)
    governance_history: tuple[Any, ...] = field(default_factory=tuple)
    audit_history: tuple[Any, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowChainingResult:
    status: str
    success: bool
    chaining_id: str
    current_workflow: str | None
    next_workflow: str | None
    current_phase: str | None
    current_subphase: str | None
    chaining_type: str | None
    governance_status: str | None
    audit_status: str | None
    execution_status: str | None
    dependency_status: str
    continuation_status: str
    roadmap_loaded: bool
    current_workflow_completed: bool
    dependencies_satisfied: bool
    governance_satisfied: bool
    audit_satisfied: bool
    execution_stable: bool
    runtime_safe: bool
    progression_allowed: bool
    workflow_activation: bool
    context_preserved: bool
    traceability_preserved: bool
    roadmap: tuple[str, ...] = field(default_factory=tuple)
    completed_workflows: tuple[str, ...] = field(default_factory=tuple)
    required_dependencies: tuple[str, ...] = field(default_factory=tuple)
    missing_dependencies: tuple[str, ...] = field(default_factory=tuple)
    next_workflow_context: dict[str, Any] = field(default_factory=dict)
    execution_context: dict[str, Any] = field(default_factory=dict)
    lifecycle_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    roadmap_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    governance_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    audit_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    chaining_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "chaining_id": self.chaining_id,
            "current_workflow": self.current_workflow,
            "next_workflow": self.next_workflow,
            "current_phase": self.current_phase,
            "current_subphase": self.current_subphase,
            "chaining_type": self.chaining_type,
            "governance_status": self.governance_status,
            "audit_status": self.audit_status,
            "execution_status": self.execution_status,
            "dependency_status": self.dependency_status,
            "continuation_status": self.continuation_status,
            "roadmap_loaded": self.roadmap_loaded,
            "current_workflow_completed": self.current_workflow_completed,
            "dependencies_satisfied": self.dependencies_satisfied,
            "governance_satisfied": self.governance_satisfied,
            "audit_satisfied": self.audit_satisfied,
            "execution_stable": self.execution_stable,
            "runtime_safe": self.runtime_safe,
            "progression_allowed": self.progression_allowed,
            "workflow_activation": self.workflow_activation,
            "context_preserved": self.context_preserved,
            "traceability_preserved": self.traceability_preserved,
            "roadmap": list(self.roadmap),
            "completed_workflows": list(self.completed_workflows),
            "required_dependencies": list(self.required_dependencies),
            "missing_dependencies": list(self.missing_dependencies),
            "next_workflow_context": dict(self.next_workflow_context),
            "execution_context": dict(self.execution_context),
            "lifecycle_history": [
                dict(entry) for entry in self.lifecycle_history
            ],
            "roadmap_history": [dict(entry) for entry in self.roadmap_history],
            "governance_history": [
                dict(entry) for entry in self.governance_history
            ],
            "audit_history": [dict(entry) for entry in self.audit_history],
            "chaining_lifecycle": [
                dict(entry) for entry in self.chaining_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class WorkflowChaining:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def chain(
        self,
        request: WorkflowChainingRequest,
        runtime_active: bool = True,
        chaining_permitted: bool = True,
    ) -> WorkflowChainingResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        chaining_id = str(uuid4())

        try:
            phase_continuation = self._as_dict(request.phase_continuation)
            execution_resume = self._as_dict(request.execution_resume)
            approval_gate = self._as_dict(request.approval_gate)
            audit_response = self._as_dict(request.audit_response)
            chaining_type = self._normalize(request.chaining_type)
            current_workflow = self._current_workflow(request)
            detected_next = self._next_workflow(request, current_workflow)
            next_workflow = request.next_workflow or detected_next
            required_dependencies = self._dependencies(request, next_workflow)
            missing_dependencies = tuple(
                dependency
                for dependency in required_dependencies
                if dependency not in set(request.completed_workflows)
            )
            governance_status = self._governance_status(
                request,
                phase_continuation,
                execution_resume,
                approval_gate,
            )
            audit_status = self._audit_status(
                request,
                phase_continuation,
                execution_resume,
                audit_response,
            )
            execution_status = self._execution_status(
                request,
                phase_continuation,
                execution_resume,
            )
            checks = {
                "roadmap_loaded": bool(request.roadmap),
                "current_workflow_completed": current_workflow
                in set(request.completed_workflows),
                "dependencies_satisfied": not missing_dependencies,
                "governance_satisfied": (
                    governance_status in APPROVED_GOVERNANCE_STATUSES
                ),
                "audit_satisfied": audit_status in APPROVED_AUDIT_STATUSES,
                "execution_stable": execution_status in STABLE_EXECUTION_STATUSES,
                "runtime_safe": self._runtime_safe(
                    runtime_active,
                    request.runtime_state,
                    phase_continuation,
                    execution_resume,
                ),
            }
            reasons = self._reasons(
                request=request,
                chaining_type=chaining_type,
                current_workflow=current_workflow,
                detected_next=detected_next,
                next_workflow=next_workflow,
                checks=checks,
                missing_dependencies=missing_dependencies,
                runtime_active=runtime_active,
                chaining_permitted=chaining_permitted,
            )
            completed = bool(request.roadmap) and detected_next is None and not reasons
            if reasons:
                result = self._result(
                    status=CHAINING_STATUS_BLOCKED,
                    success=False,
                    chaining_id=chaining_id,
                    request=request,
                    current_workflow=current_workflow,
                    next_workflow=next_workflow,
                    chaining_type=chaining_type,
                    governance_status=governance_status,
                    audit_status=audit_status,
                    execution_status=execution_status,
                    dependency_status="blocked",
                    continuation_status="blocked_workflow_chaining",
                    checks=checks,
                    required_dependencies=required_dependencies,
                    missing_dependencies=missing_dependencies,
                    progression_allowed=False,
                    workflow_activation=False,
                    next_workflow_context={},
                    lifecycle=(
                        self._lifecycle("execution_completion_detected"),
                        self._lifecycle(CHAINING_STATUS_BLOCKED),
                    ),
                    reasons=reasons,
                    error=";".join(reasons),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            next_context = self._next_workflow_context(
                request=request,
                current_workflow=current_workflow,
                next_workflow=next_workflow,
                chaining_id=chaining_id,
                governance_status=governance_status,
                audit_status=audit_status,
                execution_status=execution_status,
            )
            result = self._result(
                status=(
                    CHAINING_STATUS_COMPLETED
                    if completed
                    else CHAINING_STATUS_ACTIVATED
                ),
                success=True,
                chaining_id=chaining_id,
                request=request,
                current_workflow=current_workflow,
                next_workflow=next_workflow,
                chaining_type=chaining_type,
                governance_status=governance_status,
                audit_status=audit_status,
                execution_status=execution_status,
                dependency_status="satisfied",
                continuation_status=(
                    "roadmap_completed"
                    if completed
                    else "next_workflow_activated_under_chaining_control"
                ),
                checks=checks,
                required_dependencies=required_dependencies,
                missing_dependencies=missing_dependencies,
                progression_allowed=not completed,
                workflow_activation=not completed,
                next_workflow_context=next_context,
                lifecycle=(
                    self._lifecycle("execution_completion_detected"),
                    self._lifecycle("roadmap_analyzed"),
                    self._lifecycle("chaining_validated"),
                    self._lifecycle(
                        CHAINING_STATUS_COMPLETED
                        if completed
                        else CHAINING_STATUS_ACTIVATED
                    ),
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
                status=CHAINING_STATUS_ERROR,
                success=False,
                chaining_id=chaining_id,
                request=request,
                current_workflow=request.current_workflow,
                next_workflow=None,
                chaining_type=request.chaining_type,
                governance_status=request.governance_status,
                audit_status=request.audit_status,
                execution_status=request.execution_status,
                dependency_status="blocked",
                continuation_status="blocked_workflow_chaining_error",
                checks={
                    "roadmap_loaded": False,
                    "current_workflow_completed": False,
                    "dependencies_satisfied": False,
                    "governance_satisfied": False,
                    "audit_satisfied": False,
                    "execution_stable": False,
                    "runtime_safe": False,
                },
                required_dependencies=tuple(),
                missing_dependencies=tuple(),
                progression_allowed=False,
                workflow_activation=False,
                next_workflow_context={},
                lifecycle=(self._lifecycle(CHAINING_STATUS_ERROR),),
                reasons=["workflow_chaining_error_contained"],
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
        chaining_id: str,
        request: WorkflowChainingRequest,
        current_workflow: str | None,
        next_workflow: str | None,
        chaining_type: str | None,
        governance_status: str | None,
        audit_status: str | None,
        execution_status: str | None,
        dependency_status: str,
        continuation_status: str,
        checks: dict[str, bool],
        required_dependencies: tuple[str, ...],
        missing_dependencies: tuple[str, ...],
        progression_allowed: bool,
        workflow_activation: bool,
        next_workflow_context: dict[str, Any],
        lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> WorkflowChainingResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        return WorkflowChainingResult(
            status=status,
            success=success,
            chaining_id=chaining_id,
            current_workflow=current_workflow,
            next_workflow=next_workflow,
            current_phase=request.current_phase,
            current_subphase=request.current_subphase,
            chaining_type=chaining_type,
            governance_status=governance_status,
            audit_status=audit_status,
            execution_status=execution_status,
            dependency_status=dependency_status,
            continuation_status=continuation_status,
            roadmap_loaded=checks["roadmap_loaded"],
            current_workflow_completed=checks["current_workflow_completed"],
            dependencies_satisfied=checks["dependencies_satisfied"],
            governance_satisfied=checks["governance_satisfied"],
            audit_satisfied=checks["audit_satisfied"],
            execution_stable=checks["execution_stable"],
            runtime_safe=checks["runtime_safe"],
            progression_allowed=progression_allowed,
            workflow_activation=workflow_activation,
            context_preserved=True,
            traceability_preserved=True,
            roadmap=tuple(request.roadmap),
            completed_workflows=tuple(request.completed_workflows),
            required_dependencies=required_dependencies,
            missing_dependencies=missing_dependencies,
            next_workflow_context=dict(next_workflow_context),
            execution_context=dict(request.execution_context or {}),
            lifecycle_history=tuple(
                self._as_dict(entry) for entry in request.lifecycle_history
            ),
            roadmap_history=tuple(
                self._as_dict(entry) for entry in request.roadmap_history
            ),
            governance_history=tuple(
                self._as_dict(entry) for entry in request.governance_history
            ),
            audit_history=tuple(
                self._as_dict(entry) for entry in request.audit_history
            ),
            chaining_lifecycle=lifecycle,
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            reasons=tuple(reasons or []),
            error=error,
            metadata=dict(request.metadata),
        )

    def _reasons(
        self,
        request: WorkflowChainingRequest,
        chaining_type: str | None,
        current_workflow: str | None,
        detected_next: str | None,
        next_workflow: str | None,
        checks: dict[str, bool],
        missing_dependencies: tuple[str, ...],
        runtime_active: bool,
        chaining_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not chaining_permitted:
            reasons.append("workflow_chaining_not_permitted")
        if chaining_type not in SUPPORTED_CHAINING_TYPES:
            reasons.append("unsupported_chaining_type")
        if not current_workflow:
            reasons.append("missing_current_workflow")
        if not checks["roadmap_loaded"]:
            reasons.append("missing_roadmap")
        elif current_workflow not in request.roadmap:
            reasons.append("current_workflow_not_in_roadmap")
        if request.next_workflow and request.next_workflow != detected_next:
            reasons.append("workflow_skipping_detected")
        if next_workflow is None and checks["roadmap_loaded"]:
            if not checks["current_workflow_completed"]:
                reasons.append("current_workflow_completion_required")
        if next_workflow is not None:
            if not checks["current_workflow_completed"]:
                reasons.append("current_workflow_completion_required")
            if not checks["dependencies_satisfied"]:
                reasons.extend(
                    f"missing_dependency:{dependency}"
                    for dependency in missing_dependencies
                )
            if not checks["governance_satisfied"]:
                reasons.append("governance_approval_required")
            if not checks["audit_satisfied"]:
                reasons.append("approved_audit_required")
            if not checks["execution_stable"]:
                reasons.append("stable_execution_required")
            if not checks["runtime_safe"]:
                reasons.append("runtime_safety_required")
        return self._unique(reasons)

    def _current_workflow(self, request: WorkflowChainingRequest) -> str | None:
        return request.current_workflow or request.current_subphase

    def _next_workflow(
        self,
        request: WorkflowChainingRequest,
        current_workflow: str | None,
    ) -> str | None:
        if not request.roadmap or not current_workflow:
            return None
        if current_workflow not in request.roadmap:
            return None
        index = request.roadmap.index(current_workflow)
        next_index = index + 1
        if next_index >= len(request.roadmap):
            return None
        return request.roadmap[next_index]

    def _dependencies(
        self,
        request: WorkflowChainingRequest,
        next_workflow: str | None,
    ) -> tuple[str, ...]:
        if not next_workflow:
            return tuple()
        values = request.dependencies.get(next_workflow) or []
        return tuple(str(value) for value in values if value)

    def _governance_status(
        self,
        request: WorkflowChainingRequest,
        phase_continuation: dict[str, Any],
        execution_resume: dict[str, Any],
        approval_gate: dict[str, Any],
    ) -> str | None:
        value = (
            request.governance_status
            or phase_continuation.get("governance_status")
            or execution_resume.get("governance_status")
            or approval_gate.get("governance_status")
            or approval_gate.get("approval_status")
        )
        return self._normalize(value)

    def _audit_status(
        self,
        request: WorkflowChainingRequest,
        phase_continuation: dict[str, Any],
        execution_resume: dict[str, Any],
        audit_response: dict[str, Any],
    ) -> str | None:
        value = (
            request.audit_status
            or phase_continuation.get("audit_status")
            or execution_resume.get("audit_status")
            or audit_response.get("audit_result")
            or audit_response.get("status")
        )
        return self._normalize(value)

    def _execution_status(
        self,
        request: WorkflowChainingRequest,
        phase_continuation: dict[str, Any],
        execution_resume: dict[str, Any],
    ) -> str | None:
        value = (
            request.execution_status
            or phase_continuation.get("execution_status")
            or execution_resume.get("resume_status")
            or execution_resume.get("status")
            or request.execution_context.get("status")
        )
        return self._normalize(value)

    def _runtime_safe(
        self,
        runtime_active: bool,
        runtime_state: dict[str, Any],
        phase_continuation: dict[str, Any],
        execution_resume: dict[str, Any],
    ) -> bool:
        if not runtime_active:
            return False
        if phase_continuation.get("runtime_safe") is True:
            return True
        values = (
            runtime_state.get("state"),
            runtime_state.get("status"),
            runtime_state.get("loop_state"),
            execution_resume.get("runtime_state", {}).get("state")
            if isinstance(execution_resume.get("runtime_state"), dict)
            else None,
            execution_resume.get("runtime_state", {}).get("status")
            if isinstance(execution_resume.get("runtime_state"), dict)
            else None,
        )
        return any(self._normalize(value) in SAFE_RUNTIME_STATES for value in values)

    def _next_workflow_context(
        self,
        request: WorkflowChainingRequest,
        current_workflow: str | None,
        next_workflow: str | None,
        chaining_id: str,
        governance_status: str | None,
        audit_status: str | None,
        execution_status: str | None,
    ) -> dict[str, Any]:
        if not next_workflow:
            return {}
        return {
            "chaining_id": chaining_id,
            "current_workflow": current_workflow,
            "next_workflow": next_workflow,
            "current_phase": request.current_phase,
            "current_subphase": request.current_subphase,
            "governance_status": governance_status,
            "audit_status": audit_status,
            "execution_status": execution_status,
            "prepared_at": datetime.now(timezone.utc).isoformat(),
        }

    def _normalize(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower().replace("-", "_").replace(" ", "_")

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        for cls in (
            PhaseContinuationResult,
            ExecutionResumeResult,
            ApprovalGateResult,
            AuditResponseControlResult,
        ):
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

    def _publish(self, result: WorkflowChainingResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_workflow_chaining_result",
        ):
            self.status.mark_workflow_chaining_result(result.to_dict())

    def _log_result(self, result: WorkflowChainingResult) -> None:
        if result.status == CHAINING_STATUS_ERROR:
            logger.error(
                "workflow_chaining: error chaining_id=%s error=%s",
                result.chaining_id,
                result.error,
            )
            return
        if result.status == CHAINING_STATUS_BLOCKED:
            logger.warning(
                "workflow_chaining: blocked chaining_id=%s reasons=%s",
                result.chaining_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "workflow_chaining: %s chaining_id=%s current=%s next=%s",
            result.status,
            result.chaining_id,
            result.current_workflow,
            result.next_workflow,
        )
