"""
Controlled execution session system for Hermes runtime.

This layer tracks the operational session around execution work: task linkage,
phase linkage, context memory, checkpoints, logs, and safe lifecycle closure.
It does not execute tasks, call providers, mutate database state, recover work
autonomously, or schedule future tasks.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.models.task import Task

logger = logging.getLogger(__name__)

SESSION_STATE_CREATED = "created"
SESSION_STATE_RUNNING = "running"
SESSION_STATE_WAITING = "waiting"
SESSION_STATE_BLOCKED = "blocked"
SESSION_STATE_FAILED = "failed"
SESSION_STATE_COMPLETED = "completed"
SESSION_OPEN_STATES = {
    SESSION_STATE_CREATED,
    SESSION_STATE_RUNNING,
    SESSION_STATE_WAITING,
    SESSION_STATE_BLOCKED,
}
SESSION_FINAL_STATES = {SESSION_STATE_FAILED, SESSION_STATE_COMPLETED}


@dataclass(frozen=True)
class ExecutionSessionLogEntry:
    event: str
    message: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "message": self.message,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ExecutionSession:
    session_id: str
    task_id: str
    phase_id: str
    execution_status: str
    runtime_owner: str
    runtime_context: dict[str, Any] = field(default_factory=dict)
    context_memory: dict[str, Any] = field(default_factory=dict)
    audit_status: str = "not_started"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    started_at: str | None = None
    updated_at: str | None = None
    closed_at: str | None = None
    last_checkpoint: str | None = None
    last_file_modified: str | None = None
    last_result: str | None = None
    last_error: str | None = None
    last_audit: str | None = None
    recovery_available: bool = True
    active: bool = True
    logs: tuple[ExecutionSessionLogEntry, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "phase_id": self.phase_id,
            "execution_status": self.execution_status,
            "runtime_owner": self.runtime_owner,
            "runtime_context": dict(self.runtime_context),
            "context_memory": dict(self.context_memory),
            "audit_status": self.audit_status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "closed_at": self.closed_at,
            "last_checkpoint": self.last_checkpoint,
            "last_file_modified": self.last_file_modified,
            "last_result": self.last_result,
            "last_error": self.last_error,
            "last_audit": self.last_audit,
            "recovery_available": self.recovery_available,
            "active": self.active,
            "logs": [entry.to_dict() for entry in self.logs],
        }


@dataclass(frozen=True)
class ExecutionSessionResult:
    status: str
    success: bool
    runtime_protected: bool
    session_state: str
    session_id: str | None = None
    task_id: str | None = None
    phase_id: str | None = None
    runtime_owner: str | None = None
    active_sessions: int = 0
    max_active_sessions: int = 0
    recovery_available: bool = False
    audit_status: str | None = None
    last_checkpoint: str | None = None
    last_file_modified: str | None = None
    last_result: str | None = None
    last_error: str | None = None
    last_audit: str | None = None
    checked_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    duration_ms: int = 0
    session: ExecutionSession | None = None
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success": self.success,
            "runtime_protected": self.runtime_protected,
            "session_state": self.session_state,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "phase_id": self.phase_id,
            "runtime_owner": self.runtime_owner,
            "active_sessions": self.active_sessions,
            "max_active_sessions": self.max_active_sessions,
            "recovery_available": self.recovery_available,
            "audit_status": self.audit_status,
            "last_checkpoint": self.last_checkpoint,
            "last_file_modified": self.last_file_modified,
            "last_result": self.last_result,
            "last_error": self.last_error,
            "last_audit": self.last_audit,
            "checked_at": self.checked_at,
            "duration_ms": self.duration_ms,
            "session": self.session.to_dict() if self.session else None,
            "reasons": list(self.reasons),
            "error": self.error,
        }


class ExecutionSessionManager:
    def __init__(
        self,
        runtime_owner: str = f"{settings.RUNNER_ID}:{settings.RUNTIME_ID}",
        max_active_sessions: int = settings.EXECUTION_SESSION_MAX_ACTIVE,
        max_log_entries: int = settings.EXECUTION_SESSION_MAX_LOG_ENTRIES,
    ) -> None:
        self.runtime_owner = runtime_owner
        self.max_active_sessions = max(1, int(max_active_sessions or 1))
        self.max_log_entries = max(1, int(max_log_entries or 1))
        self._sessions: dict[str, ExecutionSession] = {}
        self._active_session_id: str | None = None

    async def inspect(self) -> ExecutionSessionResult:
        return self.evaluate()

    def evaluate(self) -> ExecutionSessionResult:
        started = time.perf_counter()
        try:
            session = self.active_session()
            return self._result(
                status="active" if session else "idle",
                success=True,
                session_state=(
                    session.execution_status if session else "ready"
                ),
                session=session,
                started=started,
            )
        except Exception as exc:
            result = self._result(
                status="error",
                success=False,
                session_state="error",
                reasons=["execution_session_inspect_failed"],
                error=str(exc),
                started=started,
            )
            self._log_result(result)
            return result

    def start_session(
        self,
        task: Task | dict[str, Any],
        phase_id: str | None = None,
        runtime_context: dict[str, Any] | None = None,
        context_memory: dict[str, Any] | None = None,
        audit_status: str = "not_started",
    ) -> ExecutionSessionResult:
        started = time.perf_counter()
        try:
            task_data = self._task_data(task)
            phase = str(phase_id or task_data.get("phase") or "").strip()
            context = dict(runtime_context or {})
            memory = dict(context_memory or {})
            reasons = self._start_reasons(task_data, phase, context, memory)
            if reasons:
                result = self._result(
                    status="rejected",
                    success=False,
                    session_state="blocked",
                    reasons=reasons,
                    started=started,
                )
                self._log_result(result)
                return result

            now = datetime.now(timezone.utc).isoformat()
            session = ExecutionSession(
                session_id=str(uuid4()),
                task_id=str(task_data["task_id"]),
                phase_id=phase,
                execution_status=SESSION_STATE_RUNNING,
                runtime_owner=self.runtime_owner,
                runtime_context=context,
                context_memory=memory,
                audit_status=audit_status or "not_started",
                started_at=now,
                updated_at=now,
                logs=(
                    ExecutionSessionLogEntry(
                        event="session_started",
                        message="Execution session started.",
                        metadata={"phase_id": phase},
                    ),
                ),
            )
            self._sessions[session.session_id] = session
            self._active_session_id = session.session_id
            result = self._result(
                status="started",
                success=True,
                session_state=session.execution_status,
                session=session,
                started=started,
            )
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._result(
                status="error",
                success=False,
                session_state="error",
                reasons=["execution_session_start_failed"],
                error=str(exc),
                started=started,
            )
            self._log_result(result)
            return result

    def save_session(
        self,
        session_id: str,
        checkpoint: str | None = None,
        file_modified: str | None = None,
        result: str | None = None,
        error: str | None = None,
        audit_status: str | None = None,
        last_audit: str | None = None,
        context_updates: dict[str, Any] | None = None,
        state: str | None = None,
        log_message: str | None = None,
    ) -> ExecutionSessionResult:
        started = time.perf_counter()
        session = self._sessions.get(session_id)
        if session is None:
            return self._rejected(
                "missing_execution_session",
                "blocked",
                started,
            )
        if session.execution_status in SESSION_FINAL_STATES:
            return self._rejected(
                "cannot_update_closed_session",
                session.execution_status,
                started,
                session=session,
            )

        next_state = state or session.execution_status
        if next_state not in SESSION_OPEN_STATES:
            return self._rejected(
                "invalid_execution_session_state",
                session.execution_status,
                started,
                session=session,
            )

        memory = dict(session.context_memory)
        memory.update(dict(context_updates or {}))
        updated = replace(
            session,
            execution_status=next_state,
            context_memory=memory,
            audit_status=audit_status or session.audit_status,
            updated_at=datetime.now(timezone.utc).isoformat(),
            last_checkpoint=checkpoint or session.last_checkpoint,
            last_file_modified=file_modified or session.last_file_modified,
            last_result=result or session.last_result,
            last_error=error or session.last_error,
            last_audit=last_audit or session.last_audit,
            logs=self._append_log(
                session,
                "session_saved",
                log_message or "Execution session progress saved.",
            ),
        )
        self._sessions[session_id] = updated
        return self._result(
            status="saved",
            success=True,
            session_state=updated.execution_status,
            session=updated,
            started=started,
        )

    def recover_session(
        self,
        session_id: str | None = None,
        task_id: str | None = None,
    ) -> ExecutionSessionResult:
        started = time.perf_counter()
        session = self._find_recoverable_session(session_id, task_id)
        if session is None:
            return self._result(
                status="not_found",
                success=False,
                session_state="missing",
                reasons=["recoverable_execution_session_not_found"],
                started=started,
            )
        recovered = replace(
            session,
            execution_status=SESSION_STATE_RUNNING,
            active=True,
            updated_at=datetime.now(timezone.utc).isoformat(),
            logs=self._append_log(
                session,
                "session_recovered",
                "Execution session recovered.",
            ),
        )
        self._sessions[recovered.session_id] = recovered
        self._active_session_id = recovered.session_id
        return self._result(
            status="recovered",
            success=True,
            session_state=recovered.execution_status,
            session=recovered,
            started=started,
        )

    def close_session(
        self,
        session_id: str,
        completed: bool = True,
        result: str | None = None,
        error: str | None = None,
    ) -> ExecutionSessionResult:
        started = time.perf_counter()
        session = self._sessions.get(session_id)
        if session is None:
            return self._rejected(
                "missing_execution_session",
                "blocked",
                started,
            )

        state = SESSION_STATE_COMPLETED if completed else SESSION_STATE_FAILED
        closed = replace(
            session,
            execution_status=state,
            active=False,
            recovery_available=False,
            updated_at=datetime.now(timezone.utc).isoformat(),
            closed_at=datetime.now(timezone.utc).isoformat(),
            last_result=result or session.last_result,
            last_error=error or session.last_error,
            logs=self._append_log(
                session,
                "session_closed",
                "Execution session closed.",
            ),
        )
        self._sessions[session_id] = closed
        if self._active_session_id == session_id:
            self._active_session_id = None
        return self._result(
            status="closed",
            success=completed,
            session_state=closed.execution_status,
            session=closed,
            started=started,
        )

    def active_session(self) -> ExecutionSession | None:
        if not self._active_session_id:
            return None
        return self._sessions.get(self._active_session_id)

    def visibility(self) -> dict[str, Any]:
        active = self.active_session()
        recoverable = [
            session.to_dict()
            for session in self._sessions.values()
            if session.recovery_available
            and session.execution_status in SESSION_OPEN_STATES
        ]
        return {
            "runtime_owner": self.runtime_owner,
            "active_sessions": 1 if active else 0,
            "max_active_sessions": self.max_active_sessions,
            "active_session": active.to_dict() if active else None,
            "recoverable_sessions": recoverable,
            "session_count": len(self._sessions),
        }

    def _task_data(self, task: Task | dict[str, Any]) -> dict[str, Any]:
        if isinstance(task, dict):
            return {
                "task_id": task.get("task_id") or task.get("id"),
                "title": task.get("title"),
                "phase": task.get("phase") or task.get("phase_id"),
            }
        return {
            "task_id": getattr(task, "id", None),
            "title": getattr(task, "title", None),
            "phase": getattr(task, "phase", None),
        }

    def _start_reasons(
        self,
        task_data: dict[str, Any],
        phase_id: str,
        runtime_context: dict[str, Any],
        context_memory: dict[str, Any],
    ) -> list[str]:
        reasons: list[str] = []
        if not task_data.get("task_id"):
            reasons.append("missing_task_id")
        if not phase_id:
            reasons.append("missing_phase_id")
        if not isinstance(runtime_context, dict):
            reasons.append("invalid_runtime_context")
        if not isinstance(context_memory, dict):
            reasons.append("invalid_context_memory")
        active = self.active_session()
        if active is not None:
            if str(task_data.get("task_id")) == active.task_id:
                reasons.append("execution_session_already_active")
            else:
                reasons.append("conflicting_execution_session_active")
        if len([s for s in self._sessions.values() if s.active]) >= self.max_active_sessions:
            reasons.append("max_active_execution_sessions_reached")
        return reasons

    def _find_recoverable_session(
        self,
        session_id: str | None,
        task_id: str | None,
    ) -> ExecutionSession | None:
        sessions = list(self._sessions.values())
        for session in reversed(sessions):
            if session_id and session.session_id != session_id:
                continue
            if task_id and session.task_id != str(task_id):
                continue
            if (
                session.recovery_available
                and session.execution_status in SESSION_OPEN_STATES
            ):
                return session
        return None

    def _append_log(
        self,
        session: ExecutionSession,
        event: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[ExecutionSessionLogEntry, ...]:
        logs = list(session.logs)
        logs.append(
            ExecutionSessionLogEntry(
                event=event,
                message=message,
                metadata=dict(metadata or {}),
            )
        )
        return tuple(logs[-self.max_log_entries :])

    def _rejected(
        self,
        reason: str,
        session_state: str,
        started: float,
        session: ExecutionSession | None = None,
    ) -> ExecutionSessionResult:
        result = self._result(
            status="rejected",
            success=False,
            session_state=session_state,
            session=session,
            reasons=[reason],
            started=started,
        )
        self._log_result(result)
        return result

    def _result(
        self,
        status: str,
        success: bool,
        session_state: str,
        session: ExecutionSession | None = None,
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
    ) -> ExecutionSessionResult:
        active_sessions = 1 if self.active_session() else 0
        return ExecutionSessionResult(
            status=status,
            success=success,
            runtime_protected=True,
            session_state=session_state,
            session_id=session.session_id if session else None,
            task_id=session.task_id if session else None,
            phase_id=session.phase_id if session else None,
            runtime_owner=(session.runtime_owner if session else self.runtime_owner),
            active_sessions=active_sessions,
            max_active_sessions=self.max_active_sessions,
            recovery_available=bool(session and session.recovery_available),
            audit_status=session.audit_status if session else None,
            last_checkpoint=session.last_checkpoint if session else None,
            last_file_modified=session.last_file_modified if session else None,
            last_result=session.last_result if session else None,
            last_error=session.last_error if session else None,
            last_audit=session.last_audit if session else None,
            duration_ms=(
                int((time.perf_counter() - started) * 1000)
                if started is not None
                else 0
            ),
            session=session,
            reasons=tuple(reasons or []),
            error=error,
        )

    def _log_result(self, result: ExecutionSessionResult) -> None:
        if result.status in {"idle", "active"}:
            logger.debug(
                "execution_session: %s active_sessions=%s",
                result.status,
                result.active_sessions,
            )
            return
        if result.status in {"started", "saved", "recovered", "closed"}:
            logger.info(
                "execution_session: %s session_id=%s task_id=%s phase_id=%s state=%s",
                result.status,
                result.session_id,
                result.task_id,
                result.phase_id,
                result.session_state,
            )
            return
        if result.status == "error":
            logger.error(
                "execution_session: error reasons=%s error=%s",
                ",".join(result.reasons),
                result.error,
            )
            return
        logger.warning(
            "execution_session: rejected reasons=%s",
            ",".join(result.reasons),
        )
