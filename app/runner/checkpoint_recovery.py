"""
Controlled checkpoint recovery for Hermes runtime.

This layer creates integrity-checked checkpoint records and prepares safe
restoration from valid checkpoints. It does not overwrite checkpoints, mutate
tasks, resume execution automatically, or bypass audit/governance.
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

logger = logging.getLogger(__name__)

CHECKPOINT_TYPE_EXECUTION = "execution"
CHECKPOINT_TYPE_PHASE = "phase"
CHECKPOINT_TYPE_GOVERNANCE = "governance"
CHECKPOINT_TYPE_RUNTIME = "runtime"
CHECKPOINT_TYPE_PROVIDER = "provider"
SUPPORTED_CHECKPOINT_TYPES = {
    CHECKPOINT_TYPE_EXECUTION,
    CHECKPOINT_TYPE_PHASE,
    CHECKPOINT_TYPE_GOVERNANCE,
    CHECKPOINT_TYPE_RUNTIME,
    CHECKPOINT_TYPE_PROVIDER,
}

CHECKPOINT_STATUS_CREATED = "created"
CHECKPOINT_STATUS_RECOVERY_PREPARED = "recovery_prepared"
CHECKPOINT_STATUS_BLOCKED = "blocked"
CHECKPOINT_STATUS_ERROR = "error"

CRITICAL_HINTS = ("architecture", "security", "deployment", "runtime_loop")


@dataclass(frozen=True)
class CheckpointRequest:
    execution_id: str | None = None
    task_id: str | None = None
    checkpoint_type: str = CHECKPOINT_TYPE_EXECUTION
    phase_state: dict[str, Any] = field(default_factory=dict)
    runtime_state: dict[str, Any] = field(default_factory=dict)
    governance_state: dict[str, Any] = field(default_factory=dict)
    audit_state: dict[str, Any] = field(default_factory=dict)
    provider_state: dict[str, Any] = field(default_factory=dict)
    execution_context: dict[str, Any] = field(default_factory=dict)
    lifecycle_state: dict[str, Any] = field(default_factory=dict)
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    recovery_logs: tuple[Any, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RecoveryRequest:
    execution_id: str | None = None
    checkpoints: tuple[Any, ...] = field(default_factory=tuple)
    failure_context: dict[str, Any] = field(default_factory=dict)
    current_runtime_state: dict[str, Any] = field(default_factory=dict)
    current_logs: tuple[Any, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CheckpointRecoveryResult:
    status: str
    success: bool
    checkpoint_id: str | None
    recovery_id: str | None
    execution_id: str | None
    task_id: str | None
    checkpoint_type: str | None
    recovery_status: str
    checkpoint_valid: bool
    checkpoint_checksum: str | None
    restoration_ready: bool
    continuation_status: str
    context_preserved: bool
    traceability_preserved: bool
    governance_review_required: bool
    audit_review_required: bool
    checkpoint: dict[str, Any] = field(default_factory=dict)
    restored_state: dict[str, Any] = field(default_factory=dict)
    phase_state: dict[str, Any] = field(default_factory=dict)
    runtime_state: dict[str, Any] = field(default_factory=dict)
    governance_state: dict[str, Any] = field(default_factory=dict)
    audit_state: dict[str, Any] = field(default_factory=dict)
    provider_state: dict[str, Any] = field(default_factory=dict)
    execution_context: dict[str, Any] = field(default_factory=dict)
    lifecycle_state: dict[str, Any] = field(default_factory=dict)
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    recovery_logs: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    recovery_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "checkpoint_id": self.checkpoint_id,
            "recovery_id": self.recovery_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "checkpoint_type": self.checkpoint_type,
            "recovery_status": self.recovery_status,
            "checkpoint_valid": self.checkpoint_valid,
            "checkpoint_checksum": self.checkpoint_checksum,
            "restoration_ready": self.restoration_ready,
            "continuation_status": self.continuation_status,
            "context_preserved": self.context_preserved,
            "traceability_preserved": self.traceability_preserved,
            "governance_review_required": self.governance_review_required,
            "audit_review_required": self.audit_review_required,
            "checkpoint": dict(self.checkpoint),
            "restored_state": dict(self.restored_state),
            "phase_state": dict(self.phase_state),
            "runtime_state": dict(self.runtime_state),
            "governance_state": dict(self.governance_state),
            "audit_state": dict(self.audit_state),
            "provider_state": dict(self.provider_state),
            "execution_context": dict(self.execution_context),
            "lifecycle_state": dict(self.lifecycle_state),
            "modified_files": list(self.modified_files),
            "recovery_logs": [dict(entry) for entry in self.recovery_logs],
            "recovery_lifecycle": [
                dict(entry) for entry in self.recovery_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class CheckpointRecovery:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def create(
        self,
        request: CheckpointRequest,
        runtime_active: bool = True,
        checkpoint_permitted: bool = True,
    ) -> CheckpointRecoveryResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        checkpoint_id = str(uuid4())

        try:
            checkpoint_type = self._checkpoint_type(request.checkpoint_type)
            reasons = self._creation_reasons(
                request,
                checkpoint_type,
                runtime_active,
                checkpoint_permitted,
            )
            if reasons:
                result = self._result(
                    status=CHECKPOINT_STATUS_BLOCKED,
                    success=False,
                    checkpoint_id=checkpoint_id,
                    recovery_id=None,
                    request=request,
                    checkpoint_type=checkpoint_type,
                    recovery_status=CHECKPOINT_STATUS_BLOCKED,
                    checkpoint_valid=False,
                    checkpoint={},
                    restored_state={},
                    restoration_ready=False,
                    continuation_status="blocked_checkpoint_creation",
                    governance_review_required=False,
                    audit_review_required=False,
                    lifecycle=(self._lifecycle(CHECKPOINT_STATUS_BLOCKED),),
                    reasons=reasons,
                    error=";".join(reasons),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            checkpoint = self._checkpoint_record(checkpoint_id, request, checkpoint_type)
            result = self._result(
                status=CHECKPOINT_STATUS_CREATED,
                success=True,
                checkpoint_id=checkpoint_id,
                recovery_id=None,
                request=request,
                checkpoint_type=checkpoint_type,
                recovery_status="checkpoint_created",
                checkpoint_valid=True,
                checkpoint=checkpoint,
                restored_state={},
                restoration_ready=False,
                continuation_status="checkpoint_saved_no_auto_continue",
                governance_review_required=self._governance_review_required(request),
                audit_review_required=self._audit_review_required(request),
                lifecycle=(
                    self._lifecycle("checkpoint_creation"),
                    self._lifecycle(CHECKPOINT_STATUS_CREATED),
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
                checkpoint_id=checkpoint_id,
                recovery_id=None,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def recover(
        self,
        request: RecoveryRequest,
        runtime_active: bool = True,
        recovery_permitted: bool = True,
    ) -> CheckpointRecoveryResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        recovery_id = str(uuid4())

        try:
            checkpoint, reasons = self._select_checkpoint(request)
            if not runtime_active:
                reasons.append("runtime_inactive")
            if not recovery_permitted:
                reasons.append("checkpoint_recovery_not_permitted")
            if not request.execution_id:
                reasons.append("missing_execution_id")
            if reasons:
                result = self._recovery_result(
                    status=CHECKPOINT_STATUS_BLOCKED,
                    success=False,
                    recovery_id=recovery_id,
                    request=request,
                    checkpoint=checkpoint,
                    recovery_status=CHECKPOINT_STATUS_BLOCKED,
                    restoration_ready=False,
                    continuation_status="blocked_checkpoint_recovery",
                    lifecycle=(
                        self._lifecycle("failure_detected"),
                        self._lifecycle(CHECKPOINT_STATUS_BLOCKED),
                    ),
                    reasons=self._unique(reasons),
                    error=";".join(self._unique(reasons)),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            result = self._recovery_result(
                status=CHECKPOINT_STATUS_RECOVERY_PREPARED,
                success=True,
                recovery_id=recovery_id,
                request=request,
                checkpoint=checkpoint,
                recovery_status="restoration_prepared",
                restoration_ready=True,
                continuation_status="blocked_pending_recovery_validation",
                lifecycle=(
                    self._lifecycle("failure_detected"),
                    self._lifecycle("checkpoint_identified"),
                    self._lifecycle("restoration_prepared"),
                    self._lifecycle("recovery_validation_required"),
                ),
                reasons=["continuation_blocked_until_recovery_validation"],
                error=None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._recovery_error_result(
                recovery_id=recovery_id,
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
        checkpoint_id: str | None,
        recovery_id: str | None,
        request: CheckpointRequest,
        checkpoint_type: str | None,
        recovery_status: str,
        checkpoint_valid: bool,
        checkpoint: dict[str, Any],
        restored_state: dict[str, Any],
        restoration_ready: bool,
        continuation_status: str,
        governance_review_required: bool,
        audit_review_required: bool,
        lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> CheckpointRecoveryResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        return CheckpointRecoveryResult(
            status=status,
            success=success,
            checkpoint_id=checkpoint_id,
            recovery_id=recovery_id,
            execution_id=request.execution_id,
            task_id=request.task_id,
            checkpoint_type=checkpoint_type,
            recovery_status=recovery_status,
            checkpoint_valid=checkpoint_valid,
            checkpoint_checksum=checkpoint.get("checksum"),
            restoration_ready=restoration_ready,
            continuation_status=continuation_status,
            context_preserved=True,
            traceability_preserved=True,
            governance_review_required=governance_review_required,
            audit_review_required=audit_review_required,
            checkpoint=checkpoint,
            restored_state=restored_state,
            phase_state=dict(request.phase_state),
            runtime_state=dict(request.runtime_state),
            governance_state=dict(request.governance_state),
            audit_state=dict(request.audit_state),
            provider_state=dict(request.provider_state),
            execution_context=dict(request.execution_context),
            lifecycle_state=dict(request.lifecycle_state),
            modified_files=tuple(request.modified_files),
            recovery_logs=tuple(self._logs(request.recovery_logs)),
            recovery_lifecycle=lifecycle,
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            reasons=tuple(reasons or []),
            error=error,
            metadata=dict(request.metadata),
        )

    def _recovery_result(
        self,
        status: str,
        success: bool,
        recovery_id: str,
        request: RecoveryRequest,
        checkpoint: dict[str, Any],
        recovery_status: str,
        restoration_ready: bool,
        continuation_status: str,
        lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> CheckpointRecoveryResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        restored_state = dict(checkpoint.get("state") or {})
        return CheckpointRecoveryResult(
            status=status,
            success=success,
            checkpoint_id=checkpoint.get("checkpoint_id"),
            recovery_id=recovery_id,
            execution_id=request.execution_id,
            task_id=checkpoint.get("task_id"),
            checkpoint_type=checkpoint.get("checkpoint_type"),
            recovery_status=recovery_status,
            checkpoint_valid=self._checkpoint_valid(checkpoint),
            checkpoint_checksum=checkpoint.get("checksum"),
            restoration_ready=restoration_ready,
            continuation_status=continuation_status,
            context_preserved=True,
            traceability_preserved=True,
            governance_review_required=self._state_review_required(restored_state),
            audit_review_required=self._state_review_required(restored_state),
            checkpoint=checkpoint,
            restored_state=restored_state,
            phase_state=dict(restored_state.get("phase_state") or {}),
            runtime_state=dict(restored_state.get("runtime_state") or {}),
            governance_state=dict(restored_state.get("governance_state") or {}),
            audit_state=dict(restored_state.get("audit_state") or {}),
            provider_state=dict(restored_state.get("provider_state") or {}),
            execution_context=dict(restored_state.get("execution_context") or {}),
            lifecycle_state=dict(restored_state.get("lifecycle_state") or {}),
            modified_files=tuple(restored_state.get("modified_files") or []),
            recovery_logs=tuple(
                [
                    *self._logs(request.current_logs),
                    {
                        "event": "checkpoint_recovery_prepared",
                        "recovery_id": recovery_id,
                    },
                ]
            ),
            recovery_lifecycle=lifecycle,
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            reasons=tuple(reasons or []),
            error=error,
            metadata=dict(request.metadata),
        )

    def _creation_reasons(
        self,
        request: CheckpointRequest,
        checkpoint_type: str | None,
        runtime_active: bool,
        checkpoint_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not checkpoint_permitted:
            reasons.append("checkpoint_creation_not_permitted")
        if not request.execution_id:
            reasons.append("missing_execution_id")
        if checkpoint_type not in SUPPORTED_CHECKPOINT_TYPES:
            reasons.append("unsupported_checkpoint_type")
        if not any(
            (
                request.phase_state,
                request.runtime_state,
                request.governance_state,
                request.audit_state,
                request.provider_state,
                request.execution_context,
                request.lifecycle_state,
            )
        ):
            reasons.append("missing_checkpoint_state")
        return self._unique(reasons)

    def _checkpoint_record(
        self,
        checkpoint_id: str,
        request: CheckpointRequest,
        checkpoint_type: str,
    ) -> dict[str, Any]:
        state = {
            "phase_state": dict(request.phase_state),
            "runtime_state": dict(request.runtime_state),
            "governance_state": dict(request.governance_state),
            "audit_state": dict(request.audit_state),
            "provider_state": dict(request.provider_state),
            "execution_context": dict(request.execution_context),
            "lifecycle_state": dict(request.lifecycle_state),
            "modified_files": list(request.modified_files),
        }
        checkpoint = {
            "checkpoint_id": checkpoint_id,
            "execution_id": request.execution_id,
            "task_id": request.task_id,
            "checkpoint_type": checkpoint_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "state": state,
        }
        checkpoint["checksum"] = self._checksum(checkpoint)
        return checkpoint

    def _select_checkpoint(
        self,
        request: RecoveryRequest,
    ) -> tuple[dict[str, Any], list[str]]:
        reasons: list[str] = []
        candidates = [self._as_dict(value) for value in request.checkpoints]
        matching = [
            item
            for item in candidates
            if item.get("execution_id") == request.execution_id
        ]
        if not candidates:
            reasons.append("missing_checkpoints")
            return {}, reasons
        if not matching:
            reasons.append("matching_checkpoint_not_found")
            return {}, reasons
        valid = [item for item in matching if self._checkpoint_valid(item)]
        if not valid:
            reasons.append("valid_checkpoint_not_found")
            return matching[-1], reasons
        return valid[-1], reasons

    def _checkpoint_valid(self, checkpoint: dict[str, Any]) -> bool:
        if not checkpoint:
            return False
        if not checkpoint.get("checkpoint_id") or not checkpoint.get("execution_id"):
            return False
        if not isinstance(checkpoint.get("state"), dict):
            return False
        checksum = checkpoint.get("checksum")
        return bool(checksum) and checksum == self._checksum(checkpoint)

    def _checkpoint_type(self, value: str | None) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower().replace("-", "_").replace(" ", "_")

    def _governance_review_required(self, request: CheckpointRequest) -> bool:
        body = self._state_text(
            request.phase_state,
            request.runtime_state,
            request.governance_state,
            request.audit_state,
            request.execution_context,
            {"modified_files": list(request.modified_files)},
        )
        return any(hint in body for hint in CRITICAL_HINTS)

    def _audit_review_required(self, request: CheckpointRequest) -> bool:
        return self._governance_review_required(request)

    def _state_review_required(self, state: dict[str, Any]) -> bool:
        return any(hint in self._state_text(state) for hint in CRITICAL_HINTS)

    def _state_text(self, *values: Any) -> str:
        return " ".join(
            json.dumps(value, sort_keys=True, default=str) for value in values
        ).lower()

    def _checksum(self, checkpoint: dict[str, Any]) -> str:
        payload = {
            key: value for key, value in checkpoint.items() if key != "checksum"
        }
        body = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(body).hexdigest()

    def _logs(self, values: tuple[Any, ...]) -> list[dict[str, Any]]:
        return [self._as_dict(value) for value in values]

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
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

    def _error_result(
        self,
        checkpoint_id: str | None,
        recovery_id: str | None,
        request: CheckpointRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> CheckpointRecoveryResult:
        return self._result(
            status=CHECKPOINT_STATUS_ERROR,
            success=False,
            checkpoint_id=checkpoint_id,
            recovery_id=recovery_id,
            request=request,
            checkpoint_type=request.checkpoint_type,
            recovery_status=CHECKPOINT_STATUS_ERROR,
            checkpoint_valid=False,
            checkpoint={},
            restored_state={},
            restoration_ready=False,
            continuation_status="blocked_checkpoint_error",
            governance_review_required=True,
            audit_review_required=True,
            lifecycle=(self._lifecycle(CHECKPOINT_STATUS_ERROR),),
            reasons=["checkpoint_recovery_error_contained"],
            error=error,
            started=started,
            started_at=started_at,
        )

    def _recovery_error_result(
        self,
        recovery_id: str,
        request: RecoveryRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> CheckpointRecoveryResult:
        checkpoint_request = CheckpointRequest(execution_id=request.execution_id)
        return self._error_result(
            checkpoint_id=None,
            recovery_id=recovery_id,
            request=checkpoint_request,
            error=error,
            started=started,
            started_at=started_at,
        )

    def _publish(self, result: CheckpointRecoveryResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_checkpoint_recovery_result",
        ):
            self.status.mark_checkpoint_recovery_result(result.to_dict())

    def _log_result(self, result: CheckpointRecoveryResult) -> None:
        if result.status == CHECKPOINT_STATUS_ERROR:
            logger.error(
                "checkpoint_recovery: error checkpoint_id=%s recovery_id=%s error=%s",
                result.checkpoint_id,
                result.recovery_id,
                result.error,
            )
            return
        if result.status == CHECKPOINT_STATUS_BLOCKED:
            logger.warning(
                "checkpoint_recovery: blocked checkpoint_id=%s recovery_id=%s reasons=%s",
                result.checkpoint_id,
                result.recovery_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "checkpoint_recovery: %s checkpoint_id=%s recovery_id=%s execution_id=%s",
            result.status,
            result.checkpoint_id,
            result.recovery_id,
            result.execution_id,
        )
