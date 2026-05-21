"""
Execution context memory for Hermes runtime sessions.

This module preserves in-memory operational snapshots for execution continuity.
It does not persist to database, mutate tasks, call providers, or learn
autonomously.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ExecutionContextSnapshot:
    execution_id: str
    phase_id: str
    task_id: str
    active_status: str
    last_checkpoint: str | None = None
    last_action: str | None = None
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    audit_status: str | None = None
    human_approval_status: str | None = None
    error_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    provider_context: dict[str, Any] = field(default_factory=dict)
    lifecycle_stage: str | None = None
    execution_state: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "phase_id": self.phase_id,
            "task_id": self.task_id,
            "active_status": self.active_status,
            "last_checkpoint": self.last_checkpoint,
            "last_action": self.last_action,
            "modified_files": list(self.modified_files),
            "audit_status": self.audit_status,
            "human_approval_status": self.human_approval_status,
            "error_history": [dict(item) for item in self.error_history],
            "provider_context": dict(self.provider_context),
            "lifecycle_stage": self.lifecycle_stage,
            "execution_state": self.execution_state,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ExecutionContextMemoryResult:
    status: str
    success: bool
    runtime_protected: bool
    snapshot: ExecutionContextSnapshot | None = None
    recovery_available: bool = False
    checked_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    duration_ms: int = 0
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success": self.success,
            "runtime_protected": self.runtime_protected,
            "snapshot": self.snapshot.to_dict() if self.snapshot else None,
            "recovery_available": self.recovery_available,
            "checked_at": self.checked_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
        }


class ExecutionContextMemory:
    def preserve(
        self,
        session: dict[str, Any],
        checkpoint: str | None = None,
        last_action: str | None = None,
        modified_files: list[str] | tuple[str, ...] | None = None,
        audit_status: str | None = None,
        human_approval_status: str | None = None,
        error: str | None = None,
        provider_context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionContextMemoryResult:
        started = time.perf_counter()
        try:
            snapshot = self.build_snapshot(
                session,
                checkpoint=checkpoint,
                last_action=last_action,
                modified_files=modified_files,
                audit_status=audit_status,
                human_approval_status=human_approval_status,
                error=error,
                provider_context=provider_context,
                metadata=metadata,
            )
            reasons = self.validation_reasons(snapshot)
            if reasons:
                return self._result(
                    "rejected",
                    False,
                    snapshot,
                    False,
                    reasons,
                    started,
                )
            return self._result(
                "preserved",
                True,
                snapshot,
                bool(snapshot.last_checkpoint),
                [],
                started,
            )
        except Exception as exc:
            return self._result(
                "error",
                False,
                None,
                False,
                ["context_memory_preserve_failed"],
                started,
                error=str(exc),
            )

    def recover(
        self,
        snapshots: list[dict[str, Any]] | tuple[dict[str, Any], ...],
        task_id: str,
        phase_id: str,
    ) -> ExecutionContextMemoryResult:
        started = time.perf_counter()
        try:
            for item in reversed(list(snapshots)):
                if item.get("task_id") != str(task_id):
                    continue
                if item.get("phase_id") != str(phase_id):
                    continue
                snapshot = self.snapshot_from_dict(item)
                reasons = self.validation_reasons(snapshot)
                if reasons:
                    return self._result(
                        "rejected",
                        False,
                        snapshot,
                        False,
                        ["corrupt_context_snapshot", *reasons],
                        started,
                    )
                return self._result(
                    "recovered",
                    True,
                    snapshot,
                    bool(snapshot.last_checkpoint),
                    [],
                    started,
                )
            return self._result(
                "not_found",
                False,
                None,
                False,
                ["recoverable_context_not_found"],
                started,
            )
        except Exception as exc:
            return self._result(
                "error",
                False,
                None,
                False,
                ["context_memory_recovery_failed"],
                started,
                error=str(exc),
            )

    def build_snapshot(
        self,
        session: dict[str, Any],
        checkpoint: str | None = None,
        last_action: str | None = None,
        modified_files: list[str] | tuple[str, ...] | None = None,
        audit_status: str | None = None,
        human_approval_status: str | None = None,
        error: str | None = None,
        provider_context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionContextSnapshot:
        existing_errors = session.get("error_history") or []
        errors = [dict(item) for item in existing_errors if isinstance(item, dict)]
        if error:
            errors.append(
                {
                    "error": error,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        existing_files = session.get("modified_files") or []
        files = [str(path) for path in existing_files if path]
        for path in modified_files or []:
            path_value = str(path)
            if path_value and path_value not in files:
                files.append(path_value)

        return ExecutionContextSnapshot(
            execution_id=str(session.get("session_id") or ""),
            phase_id=str(session.get("phase_id") or ""),
            task_id=str(session.get("task_id") or ""),
            active_status=str(session.get("execution_status") or ""),
            last_checkpoint=checkpoint or session.get("last_checkpoint"),
            last_action=last_action or session.get("last_action"),
            modified_files=tuple(files),
            audit_status=audit_status or session.get("audit_status"),
            human_approval_status=(
                human_approval_status or session.get("human_approval_status")
            ),
            error_history=tuple(errors),
            provider_context=dict(
                provider_context or session.get("provider_context") or {}
            ),
            lifecycle_stage=session.get("lifecycle_stage"),
            execution_state=session.get("execution_status"),
            metadata=dict(metadata or {}),
        )

    def snapshot_from_dict(
        self,
        data: dict[str, Any],
    ) -> ExecutionContextSnapshot:
        return ExecutionContextSnapshot(
            execution_id=str(data.get("execution_id") or ""),
            phase_id=str(data.get("phase_id") or ""),
            task_id=str(data.get("task_id") or ""),
            active_status=str(data.get("active_status") or ""),
            last_checkpoint=data.get("last_checkpoint"),
            last_action=data.get("last_action"),
            modified_files=tuple(str(path) for path in data.get("modified_files") or []),
            audit_status=data.get("audit_status"),
            human_approval_status=data.get("human_approval_status"),
            error_history=tuple(
                dict(item)
                for item in data.get("error_history") or []
                if isinstance(item, dict)
            ),
            provider_context=dict(data.get("provider_context") or {}),
            lifecycle_stage=data.get("lifecycle_stage"),
            execution_state=data.get("execution_state"),
            created_at=data.get("created_at")
            or datetime.now(timezone.utc).isoformat(),
            metadata=dict(data.get("metadata") or {}),
        )

    def validation_reasons(
        self,
        snapshot: ExecutionContextSnapshot,
    ) -> list[str]:
        reasons: list[str] = []
        if not snapshot.execution_id:
            reasons.append("missing_execution_id")
        if not snapshot.phase_id:
            reasons.append("missing_phase_id")
        if not snapshot.task_id:
            reasons.append("missing_task_id")
        if not snapshot.active_status:
            reasons.append("missing_active_status")
        if snapshot.provider_context and not isinstance(
            snapshot.provider_context,
            dict,
        ):
            reasons.append("invalid_provider_context")
        if len(set(snapshot.modified_files)) != len(snapshot.modified_files):
            reasons.append("duplicate_modified_files")
        return reasons

    def _result(
        self,
        status: str,
        success: bool,
        snapshot: ExecutionContextSnapshot | None,
        recovery_available: bool,
        reasons: list[str],
        started: float,
        error: str | None = None,
    ) -> ExecutionContextMemoryResult:
        return ExecutionContextMemoryResult(
            status=status,
            success=success,
            runtime_protected=True,
            snapshot=snapshot,
            recovery_available=bool(recovery_available),
            reasons=tuple(reasons),
            duration_ms=int((time.perf_counter() - started) * 1000),
            error=error,
        )
