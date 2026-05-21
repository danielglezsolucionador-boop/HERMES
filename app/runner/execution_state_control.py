"""
Execution state control for Hermes runtime sessions.

This module validates operational state transitions. It does not execute tasks,
call providers, mutate database rows, schedule retries, or auto-approve
recovery.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

EXECUTION_STATE_CREATED = "created"
EXECUTION_STATE_INITIALIZING = "initializing"
EXECUTION_STATE_RUNNING = "running"
EXECUTION_STATE_WAITING_APPROVAL = "waiting_approval"
EXECUTION_STATE_WAITING_AUDIT = "waiting_audit"
EXECUTION_STATE_RETRY_PENDING = "retry_pending"
EXECUTION_STATE_BLOCKED = "blocked"
EXECUTION_STATE_FAILED = "failed"
EXECUTION_STATE_COMPLETED = "completed"

EXECUTION_STATES = {
    EXECUTION_STATE_CREATED,
    EXECUTION_STATE_INITIALIZING,
    EXECUTION_STATE_RUNNING,
    EXECUTION_STATE_WAITING_APPROVAL,
    EXECUTION_STATE_WAITING_AUDIT,
    EXECUTION_STATE_RETRY_PENDING,
    EXECUTION_STATE_BLOCKED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_COMPLETED,
}

VALID_EXECUTION_TRANSITIONS = {
    EXECUTION_STATE_CREATED: {EXECUTION_STATE_INITIALIZING},
    EXECUTION_STATE_INITIALIZING: {
        EXECUTION_STATE_RUNNING,
        EXECUTION_STATE_BLOCKED,
        EXECUTION_STATE_FAILED,
    },
    EXECUTION_STATE_RUNNING: {
        EXECUTION_STATE_WAITING_AUDIT,
        EXECUTION_STATE_WAITING_APPROVAL,
        EXECUTION_STATE_BLOCKED,
        EXECUTION_STATE_FAILED,
        EXECUTION_STATE_COMPLETED,
    },
    EXECUTION_STATE_WAITING_AUDIT: {
        EXECUTION_STATE_RUNNING,
        EXECUTION_STATE_BLOCKED,
        EXECUTION_STATE_FAILED,
    },
    EXECUTION_STATE_WAITING_APPROVAL: {
        EXECUTION_STATE_RUNNING,
        EXECUTION_STATE_BLOCKED,
        EXECUTION_STATE_FAILED,
    },
    EXECUTION_STATE_RETRY_PENDING: {
        EXECUTION_STATE_RUNNING,
        EXECUTION_STATE_BLOCKED,
        EXECUTION_STATE_FAILED,
    },
    EXECUTION_STATE_BLOCKED: {EXECUTION_STATE_FAILED},
    EXECUTION_STATE_FAILED: set(),
    EXECUTION_STATE_COMPLETED: set(),
}

RECOVERY_TRANSITIONS = {
    EXECUTION_STATE_BLOCKED: {EXECUTION_STATE_RUNNING},
    EXECUTION_STATE_FAILED: {
        EXECUTION_STATE_RETRY_PENDING,
        EXECUTION_STATE_RUNNING,
    },
}

BLOCKING_REASONS = {
    "dependency_conflict",
    "invalid_architecture",
    "runtime_corruption",
    "provider_failure",
    "audit_rejection",
    "approval_rejection",
    "retry_overflow",
}


@dataclass(frozen=True)
class ExecutionStateTransitionResult:
    status: str
    allowed: bool
    current_state: str | None
    next_state: str | None
    runtime_protected: bool = True
    recovery_authorized: bool = False
    blocking_detected: bool = False
    transition: str | None = None
    checked_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    duration_ms: int = 0
    reasons: tuple[str, ...] = field(default_factory=tuple)
    blocking_reasons: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "allowed": self.allowed,
            "current_state": self.current_state,
            "next_state": self.next_state,
            "runtime_protected": self.runtime_protected,
            "recovery_authorized": self.recovery_authorized,
            "blocking_detected": self.blocking_detected,
            "transition": self.transition,
            "checked_at": self.checked_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "blocking_reasons": list(self.blocking_reasons),
            "metadata": dict(self.metadata),
            "error": self.error,
        }


class ExecutionStateController:
    def evaluate_transition(
        self,
        current_state: str | None,
        next_state: str | None,
        recovery_authorized: bool = False,
        reasons: list[str] | tuple[str, ...] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionStateTransitionResult:
        started = time.perf_counter()
        try:
            current = self.normalize_state(current_state)
            target = self.normalize_state(next_state)
            given_reasons = [str(reason) for reason in (reasons or [])]
            blocking_reasons = self.detect_blocking_reasons(
                given_reasons,
                metadata,
            )
            transition = (
                f"{current}->{target}"
                if current is not None and target is not None
                else None
            )

            if current is None:
                return self._result(
                    "rejected",
                    False,
                    current,
                    target,
                    transition,
                    recovery_authorized,
                    blocking_reasons,
                    ["missing_current_execution_state"],
                    metadata,
                    started,
                )
            if target is None:
                return self._result(
                    "rejected",
                    False,
                    current,
                    target,
                    transition,
                    recovery_authorized,
                    blocking_reasons,
                    ["missing_next_execution_state"],
                    metadata,
                    started,
                )
            if current not in EXECUTION_STATES:
                return self._result(
                    "rejected",
                    False,
                    current,
                    target,
                    transition,
                    recovery_authorized,
                    blocking_reasons,
                    ["unknown_current_execution_state"],
                    metadata,
                    started,
                )
            if target not in EXECUTION_STATES:
                return self._result(
                    "rejected",
                    False,
                    current,
                    target,
                    transition,
                    recovery_authorized,
                    blocking_reasons,
                    ["unknown_next_execution_state"],
                    metadata,
                    started,
                )
            if current == target:
                return self._result(
                    "unchanged",
                    True,
                    current,
                    target,
                    transition,
                    recovery_authorized,
                    blocking_reasons,
                    given_reasons,
                    metadata,
                    started,
                )

            valid_targets = VALID_EXECUTION_TRANSITIONS.get(current, set())
            if target in valid_targets:
                return self._result(
                    "allowed",
                    True,
                    current,
                    target,
                    transition,
                    recovery_authorized,
                    blocking_reasons,
                    given_reasons,
                    metadata,
                    started,
                )

            recovery_targets = RECOVERY_TRANSITIONS.get(current, set())
            if target in recovery_targets and recovery_authorized:
                return self._result(
                    "allowed",
                    True,
                    current,
                    target,
                    transition,
                    recovery_authorized,
                    blocking_reasons,
                    [*given_reasons, "recovery_authorized"],
                    metadata,
                    started,
                )

            invalid_reason = self.invalid_reason(
                current,
                target,
                recovery_authorized,
            )
            return self._result(
                "rejected",
                False,
                current,
                target,
                transition,
                recovery_authorized,
                blocking_reasons,
                [*given_reasons, invalid_reason],
                metadata,
                started,
            )
        except Exception as exc:
            return self._result(
                "error",
                False,
                current_state,
                next_state,
                None,
                recovery_authorized,
                [],
                ["execution_state_control_error"],
                metadata,
                started,
                error=str(exc),
            )

    def normalize_state(self, state: str | None) -> str | None:
        if state is None:
            return None
        return str(state).strip().lower()

    def detect_blocking_reasons(
        self,
        reasons: list[str],
        metadata: dict[str, Any] | None,
    ) -> list[str]:
        blocking = [reason for reason in reasons if reason in BLOCKING_REASONS]
        data = dict(metadata or {})
        for reason in BLOCKING_REASONS:
            if data.get(reason) is True and reason not in blocking:
                blocking.append(reason)
        return blocking

    def invalid_reason(
        self,
        current_state: str,
        next_state: str,
        recovery_authorized: bool,
    ) -> str:
        if current_state == EXECUTION_STATE_FAILED and next_state == EXECUTION_STATE_COMPLETED:
            return "failed_cannot_transition_to_completed"
        if current_state == EXECUTION_STATE_BLOCKED and next_state == EXECUTION_STATE_COMPLETED:
            return "blocked_cannot_transition_to_completed"
        if current_state == EXECUTION_STATE_COMPLETED:
            return "completed_state_is_terminal"
        if (
            current_state == EXECUTION_STATE_FAILED
            and next_state == EXECUTION_STATE_RUNNING
            and not recovery_authorized
        ):
            return "failed_requires_recovery_authorization"
        return "invalid_execution_state_transition"

    def _result(
        self,
        status: str,
        allowed: bool,
        current_state: str | None,
        next_state: str | None,
        transition: str | None,
        recovery_authorized: bool,
        blocking_reasons: list[str],
        reasons: list[str],
        metadata: dict[str, Any] | None,
        started: float,
        error: str | None = None,
    ) -> ExecutionStateTransitionResult:
        return ExecutionStateTransitionResult(
            status=status,
            allowed=allowed,
            current_state=current_state,
            next_state=next_state,
            transition=transition,
            recovery_authorized=bool(recovery_authorized),
            blocking_detected=bool(blocking_reasons),
            blocking_reasons=tuple(blocking_reasons),
            reasons=tuple(reasons),
            metadata=dict(metadata or {}),
            duration_ms=int((time.perf_counter() - started) * 1000),
            error=error,
        )
