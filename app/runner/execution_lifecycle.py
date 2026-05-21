"""
Execution lifecycle control for Hermes runtime sessions.

The lifecycle controller validates operational stages around execution work.
It does not run providers, audits, approvals, retries, or recovery.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

LIFECYCLE_STAGE_TASK_RECEPTION = "task_reception"
LIFECYCLE_STAGE_EXECUTION_INITIALIZATION = "execution_initialization"
LIFECYCLE_STAGE_ACTIVE_EXECUTION = "active_execution"
LIFECYCLE_STAGE_SELF_VALIDATION = "self_validation"
LIFECYCLE_STAGE_AUDIT_REQUEST = "audit_request"
LIFECYCLE_STAGE_AUDIT_RESULT = "audit_result"
LIFECYCLE_STAGE_HUMAN_APPROVAL = "human_approval"
LIFECYCLE_STAGE_CONTINUATION_DECISION = "continuation_decision"
LIFECYCLE_STAGE_EXECUTION_CLOSE = "execution_close"

AUDIT_APPROVED = "approved"
AUDIT_REJECTED = "rejected"
AUDIT_NEEDS_FIX = "needs_fix"

APPROVAL_APPROVED = "approved"
APPROVAL_REJECTED = "rejected"

CONTINUATION_CONTINUE = "continue"
CONTINUATION_STOP = "stop"
CONTINUATION_FIX = "fix"
CONTINUATION_ROLLBACK = "rollback"
CONTINUATION_ESCALATE = "escalate"

LIFECYCLE_STAGES = {
    LIFECYCLE_STAGE_TASK_RECEPTION,
    LIFECYCLE_STAGE_EXECUTION_INITIALIZATION,
    LIFECYCLE_STAGE_ACTIVE_EXECUTION,
    LIFECYCLE_STAGE_SELF_VALIDATION,
    LIFECYCLE_STAGE_AUDIT_REQUEST,
    LIFECYCLE_STAGE_AUDIT_RESULT,
    LIFECYCLE_STAGE_HUMAN_APPROVAL,
    LIFECYCLE_STAGE_CONTINUATION_DECISION,
    LIFECYCLE_STAGE_EXECUTION_CLOSE,
}

VALID_LIFECYCLE_TRANSITIONS = {
    LIFECYCLE_STAGE_TASK_RECEPTION: {
        LIFECYCLE_STAGE_EXECUTION_INITIALIZATION,
    },
    LIFECYCLE_STAGE_EXECUTION_INITIALIZATION: {
        LIFECYCLE_STAGE_ACTIVE_EXECUTION,
        LIFECYCLE_STAGE_EXECUTION_CLOSE,
    },
    LIFECYCLE_STAGE_ACTIVE_EXECUTION: {
        LIFECYCLE_STAGE_SELF_VALIDATION,
        LIFECYCLE_STAGE_EXECUTION_CLOSE,
    },
    LIFECYCLE_STAGE_SELF_VALIDATION: {
        LIFECYCLE_STAGE_AUDIT_REQUEST,
        LIFECYCLE_STAGE_ACTIVE_EXECUTION,
        LIFECYCLE_STAGE_EXECUTION_CLOSE,
    },
    LIFECYCLE_STAGE_AUDIT_REQUEST: {
        LIFECYCLE_STAGE_AUDIT_RESULT,
        LIFECYCLE_STAGE_EXECUTION_CLOSE,
    },
    LIFECYCLE_STAGE_AUDIT_RESULT: {
        LIFECYCLE_STAGE_HUMAN_APPROVAL,
        LIFECYCLE_STAGE_ACTIVE_EXECUTION,
        LIFECYCLE_STAGE_EXECUTION_CLOSE,
    },
    LIFECYCLE_STAGE_HUMAN_APPROVAL: {
        LIFECYCLE_STAGE_CONTINUATION_DECISION,
        LIFECYCLE_STAGE_EXECUTION_CLOSE,
    },
    LIFECYCLE_STAGE_CONTINUATION_DECISION: {
        LIFECYCLE_STAGE_ACTIVE_EXECUTION,
        LIFECYCLE_STAGE_EXECUTION_CLOSE,
    },
    LIFECYCLE_STAGE_EXECUTION_CLOSE: set(),
}


@dataclass(frozen=True)
class ExecutionLifecycleResult:
    status: str
    allowed: bool
    current_stage: str | None
    next_stage: str | None
    lifecycle_transition: str | None = None
    runtime_protected: bool = True
    critical: bool = True
    validation_passed: bool = False
    audit_status: str | None = None
    approval_status: str | None = None
    continuation_decision: str | None = None
    human_authorized: bool = False
    close_requested: bool = False
    checked_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    duration_ms: int = 0
    reasons: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "allowed": self.allowed,
            "current_stage": self.current_stage,
            "next_stage": self.next_stage,
            "lifecycle_transition": self.lifecycle_transition,
            "runtime_protected": self.runtime_protected,
            "critical": self.critical,
            "validation_passed": self.validation_passed,
            "audit_status": self.audit_status,
            "approval_status": self.approval_status,
            "continuation_decision": self.continuation_decision,
            "human_authorized": self.human_authorized,
            "close_requested": self.close_requested,
            "checked_at": self.checked_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "metadata": dict(self.metadata),
            "error": self.error,
        }


class ExecutionLifecycleController:
    def bootstrap_history(self) -> tuple[dict[str, Any], ...]:
        first = self.evaluate_transition(None, LIFECYCLE_STAGE_TASK_RECEPTION)
        second = self.evaluate_transition(
            LIFECYCLE_STAGE_TASK_RECEPTION,
            LIFECYCLE_STAGE_EXECUTION_INITIALIZATION,
        )
        third = self.evaluate_transition(
            LIFECYCLE_STAGE_EXECUTION_INITIALIZATION,
            LIFECYCLE_STAGE_ACTIVE_EXECUTION,
        )
        return (first.to_dict(), second.to_dict(), third.to_dict())

    def evaluate_transition(
        self,
        current_stage: str | None,
        next_stage: str | None,
        critical: bool = True,
        validation_passed: bool = False,
        audit_status: str | None = None,
        approval_status: str | None = None,
        continuation_decision: str | None = None,
        human_authorized: bool = False,
        close_requested: bool = False,
        reasons: list[str] | tuple[str, ...] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionLifecycleResult:
        started = time.perf_counter()
        try:
            current = self.normalize_stage(current_stage)
            target = self.normalize_stage(next_stage)
            transition = (
                f"{current}->{target}"
                if current is not None and target is not None
                else target
            )
            base_reasons = [str(reason) for reason in (reasons or [])]

            if target is None:
                return self._result(
                    "rejected",
                    False,
                    current,
                    target,
                    transition,
                    critical,
                    validation_passed,
                    audit_status,
                    approval_status,
                    continuation_decision,
                    human_authorized,
                    close_requested,
                    ["missing_next_lifecycle_stage", *base_reasons],
                    metadata,
                    started,
                )
            if target not in LIFECYCLE_STAGES:
                return self._result(
                    "rejected",
                    False,
                    current,
                    target,
                    transition,
                    critical,
                    validation_passed,
                    audit_status,
                    approval_status,
                    continuation_decision,
                    human_authorized,
                    close_requested,
                    ["unknown_lifecycle_stage", *base_reasons],
                    metadata,
                    started,
                )
            if current is None:
                allowed = target == LIFECYCLE_STAGE_TASK_RECEPTION
                return self._result(
                    "allowed" if allowed else "rejected",
                    allowed,
                    current,
                    target,
                    transition,
                    critical,
                    validation_passed,
                    audit_status,
                    approval_status,
                    continuation_decision,
                    human_authorized,
                    close_requested,
                    base_reasons if allowed else ["lifecycle_must_start_at_task_reception", *base_reasons],
                    metadata,
                    started,
                )
            if current not in LIFECYCLE_STAGES:
                return self._result(
                    "rejected",
                    False,
                    current,
                    target,
                    transition,
                    critical,
                    validation_passed,
                    audit_status,
                    approval_status,
                    continuation_decision,
                    human_authorized,
                    close_requested,
                    ["unknown_current_lifecycle_stage", *base_reasons],
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
                    critical,
                    validation_passed,
                    audit_status,
                    approval_status,
                    continuation_decision,
                    human_authorized,
                    close_requested,
                    base_reasons,
                    metadata,
                    started,
                )

            valid_targets = VALID_LIFECYCLE_TRANSITIONS.get(current, set())
            if target not in valid_targets:
                return self._result(
                    "rejected",
                    False,
                    current,
                    target,
                    transition,
                    critical,
                    validation_passed,
                    audit_status,
                    approval_status,
                    continuation_decision,
                    human_authorized,
                    close_requested,
                    ["invalid_lifecycle_transition", *base_reasons],
                    metadata,
                    started,
                )

            safety_reasons = self.safety_reasons(
                current,
                target,
                critical,
                validation_passed,
                audit_status,
                approval_status,
                continuation_decision,
                human_authorized,
                close_requested,
            )
            if safety_reasons:
                return self._result(
                    "rejected",
                    False,
                    current,
                    target,
                    transition,
                    critical,
                    validation_passed,
                    audit_status,
                    approval_status,
                    continuation_decision,
                    human_authorized,
                    close_requested,
                    [*safety_reasons, *base_reasons],
                    metadata,
                    started,
                )

            return self._result(
                "allowed",
                True,
                current,
                target,
                transition,
                critical,
                validation_passed,
                audit_status,
                approval_status,
                continuation_decision,
                human_authorized,
                close_requested,
                base_reasons,
                metadata,
                started,
            )
        except Exception as exc:
            return self._result(
                "error",
                False,
                current_stage,
                next_stage,
                None,
                critical,
                validation_passed,
                audit_status,
                approval_status,
                continuation_decision,
                human_authorized,
                close_requested,
                ["execution_lifecycle_error"],
                metadata,
                started,
                error=str(exc),
            )

    def safety_reasons(
        self,
        current_stage: str,
        next_stage: str,
        critical: bool,
        validation_passed: bool,
        audit_status: str | None,
        approval_status: str | None,
        continuation_decision: str | None,
        human_authorized: bool,
        close_requested: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if (
            current_stage == LIFECYCLE_STAGE_SELF_VALIDATION
            and next_stage == LIFECYCLE_STAGE_AUDIT_REQUEST
            and not validation_passed
        ):
            reasons.append("self_validation_required_before_audit")
        if (
            current_stage == LIFECYCLE_STAGE_AUDIT_RESULT
            and next_stage == LIFECYCLE_STAGE_HUMAN_APPROVAL
            and audit_status != AUDIT_APPROVED
        ):
            reasons.append("audit_approval_required_before_human_approval")
        if (
            current_stage == LIFECYCLE_STAGE_HUMAN_APPROVAL
            and next_stage == LIFECYCLE_STAGE_CONTINUATION_DECISION
            and approval_status is None
        ):
            reasons.append("human_approval_status_required")
        if (
            current_stage == LIFECYCLE_STAGE_CONTINUATION_DECISION
            and next_stage == LIFECYCLE_STAGE_ACTIVE_EXECUTION
            and not human_authorized
        ):
            reasons.append("human_authorization_required_for_continuation")
        if (
            next_stage == LIFECYCLE_STAGE_EXECUTION_CLOSE
            and critical
            and not close_requested
        ):
            reasons.append("explicit_close_request_required")
        if (
            current_stage == LIFECYCLE_STAGE_AUDIT_RESULT
            and audit_status == AUDIT_REJECTED
            and next_stage != LIFECYCLE_STAGE_EXECUTION_CLOSE
        ):
            reasons.append("audit_rejection_blocks_continuation")
        if (
            current_stage == LIFECYCLE_STAGE_HUMAN_APPROVAL
            and approval_status == APPROVAL_REJECTED
            and next_stage != LIFECYCLE_STAGE_EXECUTION_CLOSE
        ):
            reasons.append("human_rejection_blocks_continuation")
        if (
            continuation_decision in {CONTINUATION_ROLLBACK, CONTINUATION_ESCALATE}
            and next_stage == LIFECYCLE_STAGE_ACTIVE_EXECUTION
        ):
            reasons.append("continuation_decision_blocks_execution")
        return reasons

    def normalize_stage(self, stage: str | None) -> str | None:
        if stage is None:
            return None
        return str(stage).strip().lower()

    def _result(
        self,
        status: str,
        allowed: bool,
        current_stage: str | None,
        next_stage: str | None,
        transition: str | None,
        critical: bool,
        validation_passed: bool,
        audit_status: str | None,
        approval_status: str | None,
        continuation_decision: str | None,
        human_authorized: bool,
        close_requested: bool,
        reasons: list[str],
        metadata: dict[str, Any] | None,
        started: float,
        error: str | None = None,
    ) -> ExecutionLifecycleResult:
        return ExecutionLifecycleResult(
            status=status,
            allowed=allowed,
            current_stage=current_stage,
            next_stage=next_stage,
            lifecycle_transition=transition,
            critical=bool(critical),
            validation_passed=bool(validation_passed),
            audit_status=audit_status,
            approval_status=approval_status,
            continuation_decision=continuation_decision,
            human_authorized=bool(human_authorized),
            close_requested=bool(close_requested),
            reasons=tuple(reasons),
            metadata=dict(metadata or {}),
            duration_ms=int((time.perf_counter() - started) * 1000),
            error=error,
        )
