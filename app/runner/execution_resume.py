"""
Controlled execution resume for Hermes runtime.

This layer validates whether a paused or interrupted execution can be resumed
from preserved context. It records the resume decision and restored state, but
does not mutate tasks, start provider calls, bypass governance, or drive the
runtime loop.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.approval_gate import ApprovalGateResult
from app.runner.audit_response_control import AuditResponseControlResult
from app.runner.checkpoint_recovery import CheckpointRecoveryResult

logger = logging.getLogger(__name__)

RESUME_TYPE_MANUAL = "manual"
RESUME_TYPE_GOVERNANCE = "governance"
RESUME_TYPE_AUDIT = "audit"
RESUME_TYPE_CHECKPOINT = "checkpoint"
RESUME_TYPE_RECOVERY = "recovery"
SUPPORTED_RESUME_TYPES = {
    RESUME_TYPE_MANUAL,
    RESUME_TYPE_GOVERNANCE,
    RESUME_TYPE_AUDIT,
    RESUME_TYPE_CHECKPOINT,
    RESUME_TYPE_RECOVERY,
}

RESUME_STATUS_RESUMED = "resumed"
RESUME_STATUS_BLOCKED = "blocked"
RESUME_STATUS_ERROR = "error"

APPROVED_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "authorized_by_human",
    "governance_approved",
}
APPROVED_AUDIT_STATUSES = {"approved", "approved_with_warnings"}
SAFE_RUNTIME_STATES = {"active", "online", "ready", "stable"}
PAUSED_EXECUTION_STATES = {
    "paused",
    "interrupted",
    "blocked",
    "waiting_resume",
    "checkpointed",
    "recovery_prepared",
    "recovered",
    "suspended",
}
ACTIVE_EXECUTION_STATES = {"active", "running", "executing", "resumed"}


@dataclass(frozen=True)
class ExecutionResumeRequest:
    execution_id: str | None = None
    task_id: str | None = None
    resume_type: str = RESUME_TYPE_CHECKPOINT
    paused_execution: dict[str, Any] = field(default_factory=dict)
    checkpoint_recovery: CheckpointRecoveryResult | dict[str, Any] | Any | None = None
    checkpoint: dict[str, Any] = field(default_factory=dict)
    restored_state: dict[str, Any] = field(default_factory=dict)
    runtime_state: dict[str, Any] = field(default_factory=dict)
    governance_state: dict[str, Any] = field(default_factory=dict)
    audit_state: dict[str, Any] = field(default_factory=dict)
    provider_state: dict[str, Any] = field(default_factory=dict)
    execution_context: dict[str, Any] = field(default_factory=dict)
    lifecycle_state: dict[str, Any] = field(default_factory=dict)
    approval_gate: ApprovalGateResult | dict[str, Any] | Any | None = None
    audit_response: AuditResponseControlResult | dict[str, Any] | Any | None = None
    active_executions: tuple[Any, ...] = field(default_factory=tuple)
    lifecycle_history: tuple[Any, ...] = field(default_factory=tuple)
    audit_history: tuple[Any, ...] = field(default_factory=tuple)
    governance_history: tuple[Any, ...] = field(default_factory=tuple)
    recovery_history: tuple[Any, ...] = field(default_factory=tuple)
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionResumeResult:
    status: str
    success: bool
    resume_id: str
    execution_id: str | None
    task_id: str | None
    checkpoint_id: str | None
    resume_type: str | None
    governance_status: str | None
    audit_status: str | None
    resume_status: str
    continuation_status: str
    runtime_stable: bool
    checkpoint_valid: bool
    execution_consistent: bool
    governance_satisfied: bool
    audit_satisfied: bool
    workflow_continuity_preserved: bool
    execution_reactivated: bool
    context_restored: bool
    context_preserved: bool
    traceability_preserved: bool
    provider_context_restored: bool
    restored_state: dict[str, Any] = field(default_factory=dict)
    execution_context: dict[str, Any] = field(default_factory=dict)
    lifecycle_state: dict[str, Any] = field(default_factory=dict)
    runtime_state: dict[str, Any] = field(default_factory=dict)
    governance_state: dict[str, Any] = field(default_factory=dict)
    audit_state: dict[str, Any] = field(default_factory=dict)
    provider_state: dict[str, Any] = field(default_factory=dict)
    lifecycle_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    audit_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    governance_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    recovery_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    resume_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "resume_id": self.resume_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "checkpoint_id": self.checkpoint_id,
            "resume_type": self.resume_type,
            "governance_status": self.governance_status,
            "audit_status": self.audit_status,
            "resume_status": self.resume_status,
            "continuation_status": self.continuation_status,
            "runtime_stable": self.runtime_stable,
            "checkpoint_valid": self.checkpoint_valid,
            "execution_consistent": self.execution_consistent,
            "governance_satisfied": self.governance_satisfied,
            "audit_satisfied": self.audit_satisfied,
            "workflow_continuity_preserved": (
                self.workflow_continuity_preserved
            ),
            "execution_reactivated": self.execution_reactivated,
            "context_restored": self.context_restored,
            "context_preserved": self.context_preserved,
            "traceability_preserved": self.traceability_preserved,
            "provider_context_restored": self.provider_context_restored,
            "restored_state": dict(self.restored_state),
            "execution_context": dict(self.execution_context),
            "lifecycle_state": dict(self.lifecycle_state),
            "runtime_state": dict(self.runtime_state),
            "governance_state": dict(self.governance_state),
            "audit_state": dict(self.audit_state),
            "provider_state": dict(self.provider_state),
            "lifecycle_history": [
                dict(entry) for entry in self.lifecycle_history
            ],
            "audit_history": [dict(entry) for entry in self.audit_history],
            "governance_history": [
                dict(entry) for entry in self.governance_history
            ],
            "recovery_history": [
                dict(entry) for entry in self.recovery_history
            ],
            "modified_files": list(self.modified_files),
            "resume_lifecycle": [
                dict(entry) for entry in self.resume_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class ExecutionResume:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def resume(
        self,
        request: ExecutionResumeRequest,
        runtime_active: bool = True,
        resume_permitted: bool = True,
    ) -> ExecutionResumeResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        resume_id = str(uuid4())

        try:
            resume_type = self._resume_type(request.resume_type)
            checkpoint_recovery = self._as_dict(request.checkpoint_recovery)
            approval_gate = self._as_dict(request.approval_gate)
            audit_response = self._as_dict(request.audit_response)
            checkpoint = self._checkpoint(request, checkpoint_recovery)
            restored_state = self._restored_state(
                request,
                checkpoint_recovery,
                checkpoint,
            )
            execution_id = self._execution_id(
                request,
                checkpoint_recovery,
                checkpoint,
                restored_state,
            )
            task_id = self._task_id(
                request,
                checkpoint_recovery,
                checkpoint,
                restored_state,
            )
            runtime_state = self._runtime_state(
                request,
                checkpoint_recovery,
                restored_state,
            )
            governance_state = self._state(
                request.governance_state,
                checkpoint_recovery.get("governance_state"),
                restored_state.get("governance_state"),
            )
            audit_state = self._state(
                request.audit_state,
                checkpoint_recovery.get("audit_state"),
                restored_state.get("audit_state"),
            )
            provider_state = self._state(
                request.provider_state,
                checkpoint_recovery.get("provider_state"),
                restored_state.get("provider_state"),
            )
            execution_context = self._state(
                request.execution_context,
                checkpoint_recovery.get("execution_context"),
                restored_state.get("execution_context"),
                request.paused_execution,
            )
            lifecycle_state = self._state(
                request.lifecycle_state,
                checkpoint_recovery.get("lifecycle_state"),
                restored_state.get("lifecycle_state"),
            )
            governance_status = self._governance_status(
                request,
                governance_state,
                approval_gate,
            )
            audit_status = self._audit_status(request, audit_state, audit_response)
            checkpoint_valid = bool(checkpoint) and self._checkpoint_valid(checkpoint)
            checks = {
                "runtime_stable": self._runtime_stable(
                    runtime_active,
                    runtime_state,
                ),
                "checkpoint_valid": checkpoint_valid,
                "execution_consistent": self._execution_consistent(
                    execution_id,
                    task_id,
                    checkpoint_recovery,
                    checkpoint,
                    restored_state,
                ),
                "governance_satisfied": (
                    governance_status in APPROVED_GOVERNANCE_STATUSES
                ),
                "audit_satisfied": audit_status in APPROVED_AUDIT_STATUSES,
                "workflow_continuity_preserved": (
                    self._workflow_continuity_preserved(
                        request,
                        checkpoint_recovery,
                        execution_context,
                        lifecycle_state,
                    )
                ),
                "context_restored": bool(
                    restored_state or execution_context or lifecycle_state
                ),
                "provider_context_restored": bool(provider_state),
            }
            reasons = self._reasons(
                request=request,
                resume_type=resume_type,
                execution_id=execution_id,
                checks=checks,
                runtime_active=runtime_active,
                resume_permitted=resume_permitted,
                checkpoint_recovery=checkpoint_recovery,
            )
            if reasons:
                result = self._result(
                    status=RESUME_STATUS_BLOCKED,
                    success=False,
                    resume_id=resume_id,
                    execution_id=execution_id,
                    task_id=task_id,
                    checkpoint=checkpoint,
                    resume_type=resume_type,
                    governance_status=governance_status,
                    audit_status=audit_status,
                    resume_status=RESUME_STATUS_BLOCKED,
                    continuation_status="blocked_execution_resume",
                    execution_reactivated=False,
                    checks=checks,
                    restored_state=restored_state,
                    execution_context=execution_context,
                    lifecycle_state=lifecycle_state,
                    runtime_state=runtime_state,
                    governance_state=governance_state,
                    audit_state=audit_state,
                    provider_state=provider_state,
                    request=request,
                    lifecycle=(
                        self._lifecycle("resume_request_received"),
                        self._lifecycle(RESUME_STATUS_BLOCKED),
                    ),
                    reasons=reasons,
                    error=";".join(reasons),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            resumed_state = dict(restored_state)
            resumed_state["execution_status"] = RESUME_STATUS_RESUMED
            resumed_state["resumed_at"] = datetime.now(timezone.utc).isoformat()
            result = self._result(
                status=RESUME_STATUS_RESUMED,
                success=True,
                resume_id=resume_id,
                execution_id=execution_id,
                task_id=task_id,
                checkpoint=checkpoint,
                resume_type=resume_type,
                governance_status=governance_status,
                audit_status=audit_status,
                resume_status=RESUME_STATUS_RESUMED,
                continuation_status="workflow_reactivated_under_resume_control",
                execution_reactivated=True,
                checks=checks,
                restored_state=resumed_state,
                execution_context=execution_context,
                lifecycle_state=lifecycle_state,
                runtime_state=runtime_state,
                governance_state=governance_state,
                audit_state=audit_state,
                provider_state=provider_state,
                request=request,
                lifecycle=(
                    self._lifecycle("resume_request_received"),
                    self._lifecycle("context_restored"),
                    self._lifecycle("resume_validated"),
                    self._lifecycle(RESUME_STATUS_RESUMED),
                ),
                reasons=["execution_resumed_with_governance_trace"],
                error=None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                resume_id=resume_id,
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
        resume_id: str,
        execution_id: str | None,
        task_id: str | None,
        checkpoint: dict[str, Any],
        resume_type: str | None,
        governance_status: str | None,
        audit_status: str | None,
        resume_status: str,
        continuation_status: str,
        execution_reactivated: bool,
        checks: dict[str, bool],
        restored_state: dict[str, Any],
        execution_context: dict[str, Any],
        lifecycle_state: dict[str, Any],
        runtime_state: dict[str, Any],
        governance_state: dict[str, Any],
        audit_state: dict[str, Any],
        provider_state: dict[str, Any],
        request: ExecutionResumeRequest,
        lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> ExecutionResumeResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        return ExecutionResumeResult(
            status=status,
            success=success,
            resume_id=resume_id,
            execution_id=execution_id,
            task_id=task_id,
            checkpoint_id=checkpoint.get("checkpoint_id"),
            resume_type=resume_type,
            governance_status=governance_status,
            audit_status=audit_status,
            resume_status=resume_status,
            continuation_status=continuation_status,
            runtime_stable=checks["runtime_stable"],
            checkpoint_valid=checks["checkpoint_valid"],
            execution_consistent=checks["execution_consistent"],
            governance_satisfied=checks["governance_satisfied"],
            audit_satisfied=checks["audit_satisfied"],
            workflow_continuity_preserved=checks[
                "workflow_continuity_preserved"
            ],
            execution_reactivated=execution_reactivated,
            context_restored=checks["context_restored"],
            context_preserved=True,
            traceability_preserved=True,
            provider_context_restored=checks["provider_context_restored"],
            restored_state=dict(restored_state),
            execution_context=dict(execution_context),
            lifecycle_state=dict(lifecycle_state),
            runtime_state=dict(runtime_state),
            governance_state=dict(governance_state),
            audit_state=dict(audit_state),
            provider_state=dict(provider_state),
            lifecycle_history=tuple(
                self._as_dict(entry) for entry in request.lifecycle_history
            ),
            audit_history=tuple(
                self._as_dict(entry) for entry in request.audit_history
            ),
            governance_history=tuple(
                self._as_dict(entry) for entry in request.governance_history
            ),
            recovery_history=tuple(
                self._as_dict(entry) for entry in request.recovery_history
            ),
            modified_files=tuple(str(path) for path in request.modified_files),
            resume_lifecycle=lifecycle,
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            reasons=tuple(reasons or []),
            error=error,
            metadata=dict(request.metadata),
        )

    def _reasons(
        self,
        request: ExecutionResumeRequest,
        resume_type: str | None,
        execution_id: str | None,
        checks: dict[str, bool],
        runtime_active: bool,
        resume_permitted: bool,
        checkpoint_recovery: dict[str, Any],
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not resume_permitted:
            reasons.append("execution_resume_not_permitted")
        if resume_type not in SUPPORTED_RESUME_TYPES:
            reasons.append("unsupported_resume_type")
        if not execution_id:
            reasons.append("missing_execution_id")
        if resume_type in {RESUME_TYPE_CHECKPOINT, RESUME_TYPE_RECOVERY}:
            if not checks["checkpoint_valid"]:
                reasons.append("valid_checkpoint_required")
        if resume_type == RESUME_TYPE_RECOVERY:
            if checkpoint_recovery.get("restoration_ready") is not True:
                reasons.append("checkpoint_recovery_not_ready")
        if not checks["execution_consistent"]:
            reasons.append("execution_consistency_required")
        if not checks["governance_satisfied"]:
            reasons.append("governance_approval_required")
        if not checks["audit_satisfied"]:
            reasons.append("approved_audit_required")
        if not checks["runtime_stable"]:
            reasons.append("runtime_stability_required")
        if not checks["workflow_continuity_preserved"]:
            reasons.append("workflow_continuity_required")
        if not checks["context_restored"]:
            reasons.append("execution_context_required")
        if self._duplicate_execution(request):
            reasons.append("duplicate_execution_detected")
        return self._unique(reasons)

    def _checkpoint(
        self,
        request: ExecutionResumeRequest,
        checkpoint_recovery: dict[str, Any],
    ) -> dict[str, Any]:
        checkpoint = dict(request.checkpoint or {})
        if not checkpoint:
            checkpoint = dict(checkpoint_recovery.get("checkpoint") or {})
        return checkpoint

    def _restored_state(
        self,
        request: ExecutionResumeRequest,
        checkpoint_recovery: dict[str, Any],
        checkpoint: dict[str, Any],
    ) -> dict[str, Any]:
        state: dict[str, Any] = {}
        state.update(dict(checkpoint.get("state") or {}))
        state.update(dict(checkpoint_recovery.get("restored_state") or {}))
        state.update(dict(request.restored_state or {}))
        return state

    def _runtime_state(
        self,
        request: ExecutionResumeRequest,
        checkpoint_recovery: dict[str, Any],
        restored_state: dict[str, Any],
    ) -> dict[str, Any]:
        return self._state(
            request.runtime_state,
            checkpoint_recovery.get("runtime_state"),
            restored_state.get("runtime_state"),
        )

    def _state(self, *values: Any) -> dict[str, Any]:
        state: dict[str, Any] = {}
        for value in reversed(values):
            if isinstance(value, dict):
                state.update(value)
        return state

    def _execution_id(
        self,
        request: ExecutionResumeRequest,
        checkpoint_recovery: dict[str, Any],
        checkpoint: dict[str, Any],
        restored_state: dict[str, Any],
    ) -> str | None:
        context = restored_state.get("execution_context") or {}
        return (
            request.execution_id
            or checkpoint_recovery.get("execution_id")
            or checkpoint.get("execution_id")
            or context.get("execution_id")
        )

    def _task_id(
        self,
        request: ExecutionResumeRequest,
        checkpoint_recovery: dict[str, Any],
        checkpoint: dict[str, Any],
        restored_state: dict[str, Any],
    ) -> str | None:
        context = restored_state.get("execution_context") or {}
        return (
            request.task_id
            or checkpoint_recovery.get("task_id")
            or checkpoint.get("task_id")
            or context.get("task_id")
        )

    def _governance_status(
        self,
        request: ExecutionResumeRequest,
        governance_state: dict[str, Any],
        approval_gate: dict[str, Any],
    ) -> str | None:
        value = (
            governance_state.get("governance_status")
            or governance_state.get("approval_status")
            or request.governance_state.get("approval_status")
            or approval_gate.get("governance_status")
            or approval_gate.get("approval_status")
            or approval_gate.get("continuation_status")
        )
        return self._normalize(value)

    def _audit_status(
        self,
        request: ExecutionResumeRequest,
        audit_state: dict[str, Any],
        audit_response: dict[str, Any],
    ) -> str | None:
        value = (
            audit_state.get("audit_status")
            or audit_state.get("audit_result")
            or request.audit_state.get("audit_status")
            or audit_response.get("audit_result")
            or audit_response.get("status")
        )
        return self._normalize(value)

    def _runtime_stable(
        self,
        runtime_active: bool,
        runtime_state: dict[str, Any],
    ) -> bool:
        if not runtime_active:
            return False
        values = (
            runtime_state.get("state"),
            runtime_state.get("status"),
            runtime_state.get("loop_state"),
        )
        return any(self._normalize(value) in SAFE_RUNTIME_STATES for value in values)

    def _workflow_continuity_preserved(
        self,
        request: ExecutionResumeRequest,
        checkpoint_recovery: dict[str, Any],
        execution_context: dict[str, Any],
        lifecycle_state: dict[str, Any],
    ) -> bool:
        state = self._normalize(
            request.paused_execution.get("state")
            or request.paused_execution.get("status")
            or execution_context.get("state")
            or execution_context.get("status")
            or lifecycle_state.get("state")
            or lifecycle_state.get("stage")
            or checkpoint_recovery.get("recovery_status")
        )
        return bool(execution_context or lifecycle_state) and (
            state in PAUSED_EXECUTION_STATES
        )

    def _execution_consistent(
        self,
        execution_id: str | None,
        task_id: str | None,
        checkpoint_recovery: dict[str, Any],
        checkpoint: dict[str, Any],
        restored_state: dict[str, Any],
    ) -> bool:
        if not execution_id:
            return False
        execution_ids = [
            checkpoint_recovery.get("execution_id"),
            checkpoint.get("execution_id"),
            (restored_state.get("execution_context") or {}).get("execution_id"),
        ]
        for value in execution_ids:
            if value and value != execution_id:
                return False
        task_ids = [
            checkpoint_recovery.get("task_id"),
            checkpoint.get("task_id"),
            (restored_state.get("execution_context") or {}).get("task_id"),
        ]
        for value in task_ids:
            if task_id and value and value != task_id:
                return False
        return True

    def _duplicate_execution(self, request: ExecutionResumeRequest) -> bool:
        for value in request.active_executions:
            if isinstance(value, str):
                return value == request.execution_id
            item = self._as_dict(value)
            execution_id = item.get("execution_id") or item.get("id")
            state = self._normalize(item.get("state") or item.get("status"))
            if execution_id == request.execution_id and state in ACTIVE_EXECUTION_STATES:
                return True
        return False

    def _checkpoint_valid(self, checkpoint: dict[str, Any]) -> bool:
        if not checkpoint:
            return False
        if not checkpoint.get("checkpoint_id") or not checkpoint.get("execution_id"):
            return False
        if not isinstance(checkpoint.get("state"), dict):
            return False
        checksum = checkpoint.get("checksum")
        return bool(checksum) and checksum == self._checksum(checkpoint)

    def _checksum(self, checkpoint: dict[str, Any]) -> str:
        payload = {
            key: value for key, value in checkpoint.items() if key != "checksum"
        }
        body = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(body).hexdigest()

    def _resume_type(self, value: str | None) -> str | None:
        if value is None:
            return None
        return self._normalize(value)

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
            CheckpointRecoveryResult,
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

    def _error_result(
        self,
        resume_id: str,
        request: ExecutionResumeRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> ExecutionResumeResult:
        return self._result(
            status=RESUME_STATUS_ERROR,
            success=False,
            resume_id=resume_id,
            execution_id=request.execution_id,
            task_id=request.task_id,
            checkpoint=dict(request.checkpoint or {}),
            resume_type=self._resume_type(request.resume_type),
            governance_status=None,
            audit_status=None,
            resume_status=RESUME_STATUS_ERROR,
            continuation_status="blocked_execution_resume_error",
            execution_reactivated=False,
            checks={
                "runtime_stable": False,
                "checkpoint_valid": False,
                "execution_consistent": False,
                "governance_satisfied": False,
                "audit_satisfied": False,
                "workflow_continuity_preserved": False,
                "context_restored": False,
                "provider_context_restored": False,
            },
            restored_state={},
            execution_context=dict(request.execution_context or {}),
            lifecycle_state=dict(request.lifecycle_state or {}),
            runtime_state=dict(request.runtime_state or {}),
            governance_state=dict(request.governance_state or {}),
            audit_state=dict(request.audit_state or {}),
            provider_state=dict(request.provider_state or {}),
            request=request,
            lifecycle=(self._lifecycle(RESUME_STATUS_ERROR),),
            reasons=["execution_resume_error_contained"],
            error=error,
            started=started,
            started_at=started_at,
        )

    def _publish(self, result: ExecutionResumeResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_execution_resume_result",
        ):
            self.status.mark_execution_resume_result(result.to_dict())

    def _log_result(self, result: ExecutionResumeResult) -> None:
        if result.status == RESUME_STATUS_ERROR:
            logger.error(
                "execution_resume: error resume_id=%s error=%s",
                result.resume_id,
                result.error,
            )
            return
        if result.status == RESUME_STATUS_BLOCKED:
            logger.warning(
                "execution_resume: blocked resume_id=%s reasons=%s",
                result.resume_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "execution_resume: resumed resume_id=%s execution_id=%s type=%s",
            result.resume_id,
            result.execution_id,
            result.resume_type,
        )
