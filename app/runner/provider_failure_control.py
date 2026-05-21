"""
Controlled provider failure handling for Hermes runtime.

This layer detects and contains provider failures, preserves execution context,
and prepares recovery visibility. It does not retry, route providers, recover
tasks, call providers, mutate tasks, or persist data.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.prompt_execution import PromptExecutionResult
from app.runner.provider_bridge import ProviderBridgeResult
from app.runner.provider_response_handling import ProviderResponseHandlingResult

logger = logging.getLogger(__name__)

FAILURE_TYPE_CONNECTION = "connection"
FAILURE_TYPE_EXECUTION = "execution"
FAILURE_TYPE_RESPONSE = "response"
FAILURE_TYPE_LIMIT = "limit"
FAILURE_TYPE_DEGRADATION = "provider_degradation"
FAILURE_TYPE_RUNTIME = "runtime"
SUPPORTED_FAILURE_TYPES = {
    FAILURE_TYPE_CONNECTION,
    FAILURE_TYPE_EXECUTION,
    FAILURE_TYPE_RESPONSE,
    FAILURE_TYPE_LIMIT,
    FAILURE_TYPE_DEGRADATION,
    FAILURE_TYPE_RUNTIME,
}

FAILURE_SEVERITY_LOW = "low"
FAILURE_SEVERITY_MEDIUM = "medium"
FAILURE_SEVERITY_HIGH = "high"
FAILURE_SEVERITY_CRITICAL = "critical"
SUPPORTED_SEVERITIES = {
    FAILURE_SEVERITY_LOW,
    FAILURE_SEVERITY_MEDIUM,
    FAILURE_SEVERITY_HIGH,
    FAILURE_SEVERITY_CRITICAL,
}

FAILURE_STATE_DETECTED = "detected"
FAILURE_STATE_REGISTERED = "registered"
FAILURE_STATE_CONTAINED = "contained"
FAILURE_STATE_ESCALATED = "escalated"
FAILURE_STATE_BLOCKED = "blocked"
FAILURE_STATE_RECOVERY_PENDING = "recovery_pending"

RECOVERY_STATUS_NOT_REQUIRED = "not_required"
RECOVERY_STATUS_RECOVERY_PENDING = "recovery_pending"

STATUS_FAILURE_REASONS = {
    "provider_error": "provider_error",
    "timeout": "provider_timeout",
    "invalid_response": "provider_invalid_response",
    "rejected": "provider_execution_rejected",
    "error": "provider_runtime_error",
    "failed": "provider_execution_failed",
}


@dataclass(frozen=True)
class ProviderFailureControlRequest:
    signal: Any | None = None
    provider_id: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    provider_request_id: str | None = None
    provider_session_id: str | None = None
    failure_type: str | None = None
    severity: str | None = None
    runtime_state: str = "active"
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderFailureControlResult:
    status: str
    success: bool
    failure_detected: bool
    runtime_protected: bool
    continuation_blocked: bool
    context_preserved: bool
    recovery_prepared: bool
    escalation_required: bool
    failure_id: str | None = None
    provider_id: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    provider_request_id: str | None = None
    provider_session_id: str | None = None
    failure_type: str | None = None
    failure_severity: str | None = None
    failure_status: str | None = None
    recovery_status: str = RECOVERY_STATUS_NOT_REQUIRED
    runtime_state: str | None = None
    execution_impact: str = "none"
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int = 0
    timestamps: dict[str, str | None] = field(default_factory=dict)
    lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success": self.success,
            "failure_detected": self.failure_detected,
            "runtime_protected": self.runtime_protected,
            "continuation_blocked": self.continuation_blocked,
            "context_preserved": self.context_preserved,
            "recovery_prepared": self.recovery_prepared,
            "escalation_required": self.escalation_required,
            "failure_id": self.failure_id,
            "provider_id": self.provider_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "provider_request_id": self.provider_request_id,
            "provider_session_id": self.provider_session_id,
            "failure_type": self.failure_type,
            "failure_severity": self.failure_severity,
            "failure_status": self.failure_status,
            "recovery_status": self.recovery_status,
            "runtime_state": self.runtime_state,
            "execution_impact": self.execution_impact,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "timestamps": dict(self.timestamps),
            "lifecycle": [dict(entry) for entry in self.lifecycle],
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class ProviderFailureControl:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def record(
        self,
        request: ProviderFailureControlRequest,
        runtime_active: bool = True,
        failure_control_permitted: bool = True,
    ) -> ProviderFailureControlResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        failure_id = str(uuid4())

        try:
            signal = self._as_dict(request.signal)
            reasons = self._failure_reasons(
                request=request,
                signal=signal,
                runtime_active=runtime_active,
                failure_control_permitted=failure_control_permitted,
            )
            if not reasons:
                result = self._clear_result(
                    request=request,
                    signal=signal,
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            failure_type = self._failure_type(request, signal, reasons)
            severity = self._severity(request, signal, reasons, failure_type)
            escalation_required = self._requires_escalation(severity, reasons)
            lifecycle = self._failure_lifecycle(escalation_required)
            result = self._failure_result(
                request=request,
                signal=signal,
                failure_id=failure_id,
                failure_type=failure_type,
                severity=severity,
                escalation_required=escalation_required,
                reasons=reasons,
                lifecycle=lifecycle,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._contained_error_result(
                request=request,
                failure_id=failure_id,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def _clear_result(
        self,
        request: ProviderFailureControlRequest,
        signal: dict[str, Any],
        started: float,
        started_at: datetime,
    ) -> ProviderFailureControlResult:
        return self._result(
            status="clear",
            success=True,
            failure_detected=False,
            runtime_protected=True,
            continuation_blocked=False,
            context_preserved=True,
            recovery_prepared=False,
            escalation_required=False,
            request=request,
            signal=signal,
            failure_status="clear",
            recovery_status=RECOVERY_STATUS_NOT_REQUIRED,
            execution_impact="none",
            started=started,
            started_at=started_at,
        )

    def _failure_result(
        self,
        request: ProviderFailureControlRequest,
        signal: dict[str, Any],
        failure_id: str,
        failure_type: str,
        severity: str,
        escalation_required: bool,
        reasons: list[str],
        lifecycle: tuple[dict[str, Any], ...],
        started: float,
        started_at: datetime,
    ) -> ProviderFailureControlResult:
        return self._result(
            status="escalated" if escalation_required else "blocked",
            success=False,
            failure_detected=True,
            runtime_protected=True,
            continuation_blocked=True,
            context_preserved=True,
            recovery_prepared=True,
            escalation_required=escalation_required,
            request=request,
            signal=signal,
            failure_id=failure_id,
            failure_type=failure_type,
            failure_severity=severity,
            failure_status=FAILURE_STATE_RECOVERY_PENDING,
            recovery_status=RECOVERY_STATUS_RECOVERY_PENDING,
            execution_impact="blocked",
            lifecycle=lifecycle,
            reasons=reasons,
            error=request.error or signal.get("error"),
            started=started,
            started_at=started_at,
        )

    def _contained_error_result(
        self,
        request: ProviderFailureControlRequest,
        failure_id: str,
        error: str,
        started: float,
        started_at: datetime,
    ) -> ProviderFailureControlResult:
        lifecycle = (
            self._lifecycle(FAILURE_STATE_DETECTED),
            self._lifecycle(FAILURE_STATE_REGISTERED),
            self._lifecycle(FAILURE_STATE_CONTAINED),
            self._lifecycle(FAILURE_STATE_ESCALATED),
            self._lifecycle(FAILURE_STATE_BLOCKED),
            self._lifecycle(FAILURE_STATE_RECOVERY_PENDING),
        )
        return self._result(
            status="error",
            success=False,
            failure_detected=True,
            runtime_protected=True,
            continuation_blocked=True,
            context_preserved=True,
            recovery_prepared=True,
            escalation_required=True,
            request=request,
            signal={},
            failure_id=failure_id,
            failure_type=FAILURE_TYPE_RUNTIME,
            failure_severity=FAILURE_SEVERITY_CRITICAL,
            failure_status=FAILURE_STATE_RECOVERY_PENDING,
            recovery_status=RECOVERY_STATUS_RECOVERY_PENDING,
            execution_impact="blocked",
            lifecycle=lifecycle,
            reasons=["provider_failure_control_error_contained"],
            error=error,
            started=started,
            started_at=started_at,
        )

    def _result(
        self,
        status: str,
        success: bool,
        failure_detected: bool,
        runtime_protected: bool,
        continuation_blocked: bool,
        context_preserved: bool,
        recovery_prepared: bool,
        escalation_required: bool,
        request: ProviderFailureControlRequest,
        signal: dict[str, Any],
        failure_id: str | None = None,
        failure_type: str | None = None,
        failure_severity: str | None = None,
        failure_status: str | None = None,
        recovery_status: str = RECOVERY_STATUS_NOT_REQUIRED,
        execution_impact: str = "none",
        lifecycle: tuple[dict[str, Any], ...] = (),
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> ProviderFailureControlResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        timestamps = self._timestamps(
            started_at=started_at,
            finished_at=finished_at,
            lifecycle=lifecycle,
        )
        return ProviderFailureControlResult(
            status=status,
            success=success,
            failure_detected=failure_detected,
            runtime_protected=runtime_protected,
            continuation_blocked=continuation_blocked,
            context_preserved=context_preserved,
            recovery_prepared=recovery_prepared,
            escalation_required=escalation_required,
            failure_id=failure_id,
            provider_id=self._first(
                request.provider_id,
                signal.get("provider_name"),
                signal.get("provider_id"),
            ),
            execution_id=self._first(
                request.execution_id,
                signal.get("execution_id"),
            ),
            task_id=self._first(request.task_id, signal.get("task_id")),
            provider_request_id=self._first(
                request.provider_request_id,
                signal.get("request_id"),
                signal.get("provider_request_id"),
            ),
            provider_session_id=self._first(
                request.provider_session_id,
                signal.get("provider_session_id"),
            ),
            failure_type=failure_type,
            failure_severity=failure_severity,
            failure_status=failure_status,
            recovery_status=recovery_status,
            runtime_state=request.runtime_state,
            execution_impact=execution_impact,
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            timestamps=timestamps,
            lifecycle=lifecycle,
            reasons=tuple(reasons or []),
            error=error,
            metadata=dict(request.metadata),
        )

    def _failure_reasons(
        self,
        request: ProviderFailureControlRequest,
        signal: dict[str, Any],
        runtime_active: bool,
        failure_control_permitted: bool,
    ) -> list[str]:
        reasons = [str(reason) for reason in request.reasons if reason]
        reasons.extend(str(reason) for reason in signal.get("reasons") or [])
        status = signal.get("status")
        success = signal.get("success")
        if status in STATUS_FAILURE_REASONS:
            reasons.append(STATUS_FAILURE_REASONS[status])
        if success is False and not reasons:
            reasons.append("provider_failure_detected")
        failure_status = signal.get("failure_status")
        if failure_status:
            reasons.extend(self._split_reasons(str(failure_status)))
        if request.failure_type and not reasons:
            reasons.append("provider_failure_declared")
        if request.error or signal.get("error"):
            if not reasons:
                reasons.append("provider_error")
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not failure_control_permitted:
            reasons.append("failure_control_not_permitted")
        return self._unique(reasons)

    def _failure_type(
        self,
        request: ProviderFailureControlRequest,
        signal: dict[str, Any],
        reasons: list[str],
    ) -> str:
        if request.failure_type in SUPPORTED_FAILURE_TYPES:
            return str(request.failure_type)
        text = " ".join(
            [
                *(reason.lower() for reason in reasons),
                str(signal.get("status") or "").lower(),
                str(signal.get("failure_status") or "").lower(),
            ]
        )
        if self._has(text, ("rate", "quota", "token", "overflow", "threshold", "max_", "limit", "size")):
            return FAILURE_TYPE_LIMIT
        if self._has(text, ("response", "output", "payload", "empty", "malformed", "corrupt", "invalid_response")):
            return FAILURE_TYPE_RESPONSE
        if self._has(text, ("unavailable", "connection", "timeout", "credential", "not_configured", "api_key")):
            return FAILURE_TYPE_CONNECTION
        if self._has(text, ("slow", "degraded", "unstable", "intermittent", "quality")):
            return FAILURE_TYPE_DEGRADATION
        if self._has(text, ("runtime", "internal")):
            return FAILURE_TYPE_RUNTIME
        return FAILURE_TYPE_EXECUTION

    def _severity(
        self,
        request: ProviderFailureControlRequest,
        signal: dict[str, Any],
        reasons: list[str],
        failure_type: str,
    ) -> str:
        if request.severity in SUPPORTED_SEVERITIES:
            return str(request.severity)
        text = " ".join(
            [
                *(reason.lower() for reason in reasons),
                str(signal.get("error") or "").lower(),
            ]
        )
        if self._has(text, ("poison", "corrupt", "context", "credential", "not_configured", "runtime_inactive", "not_permitted")):
            return FAILURE_SEVERITY_CRITICAL
        if failure_type in {FAILURE_TYPE_CONNECTION, FAILURE_TYPE_LIMIT}:
            return FAILURE_SEVERITY_HIGH
        if self._has(text, ("timeout", "unavailable", "provider_error", "quota", "rate", "max_")):
            return FAILURE_SEVERITY_HIGH
        if failure_type == FAILURE_TYPE_DEGRADATION:
            return FAILURE_SEVERITY_LOW
        return FAILURE_SEVERITY_MEDIUM

    def _requires_escalation(self, severity: str, reasons: list[str]) -> bool:
        if severity == FAILURE_SEVERITY_CRITICAL:
            return True
        return any(
            reason in {"invalid_credentials", "provider_not_configured"}
            for reason in reasons
        )

    def _failure_lifecycle(
        self,
        escalation_required: bool,
    ) -> tuple[dict[str, Any], ...]:
        states = [
            FAILURE_STATE_DETECTED,
            FAILURE_STATE_REGISTERED,
            FAILURE_STATE_CONTAINED,
        ]
        if escalation_required:
            states.append(FAILURE_STATE_ESCALATED)
        states.extend([FAILURE_STATE_BLOCKED, FAILURE_STATE_RECOVERY_PENDING])
        return tuple(self._lifecycle(state) for state in states)

    def _timestamps(
        self,
        started_at: datetime | None,
        finished_at: datetime,
        lifecycle: tuple[dict[str, Any], ...],
    ) -> dict[str, str | None]:
        by_state = {
            str(entry.get("state")): entry.get("at")
            for entry in lifecycle
            if entry.get("state")
        }
        return {
            "started_at": started_at.isoformat() if started_at else None,
            "finished_at": finished_at.isoformat(),
            "detected_at": by_state.get(FAILURE_STATE_DETECTED),
            "registered_at": by_state.get(FAILURE_STATE_REGISTERED),
            "contained_at": by_state.get(FAILURE_STATE_CONTAINED),
            "escalated_at": by_state.get(FAILURE_STATE_ESCALATED),
            "blocked_at": by_state.get(FAILURE_STATE_BLOCKED),
            "recovery_prepared_at": by_state.get(FAILURE_STATE_RECOVERY_PENDING),
        }

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, PromptExecutionResult):
            base = value.to_dict()
            provider = base.get("provider_result") or {}
            return {**provider, **{key: val for key, val in base.items() if val is not None}}
        if isinstance(value, (ProviderBridgeResult, ProviderResponseHandlingResult)):
            return value.to_dict()
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

    def _split_reasons(self, value: str) -> list[str]:
        return [
            item.strip()
            for item in value.replace(";", ",").split(",")
            if item.strip()
        ]

    def _has(self, text: str, needles: tuple[str, ...]) -> bool:
        return any(needle in text for needle in needles)

    def _first(self, *values: Any) -> str | None:
        for value in values:
            if value is not None and str(value):
                return str(value)
        return None

    def _lifecycle(self, state: str) -> dict[str, Any]:
        return {
            "state": state,
            "at": datetime.now(timezone.utc).isoformat(),
        }

    def _unique(self, reasons: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for reason in reasons:
            if reason and reason not in seen:
                seen.add(reason)
                unique.append(reason)
        return unique

    def _publish(self, result: ProviderFailureControlResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_provider_failure_control_result",
        ):
            self.status.mark_provider_failure_control_result(result.to_dict())

    def _log_result(self, result: ProviderFailureControlResult) -> None:
        if not result.failure_detected:
            logger.info("provider_failure_control: clear")
            return
        if result.escalation_required:
            logger.error(
                "provider_failure_control: escalated failure_id=%s provider=%s type=%s severity=%s reasons=%s",
                result.failure_id,
                result.provider_id,
                result.failure_type,
                result.failure_severity,
                ",".join(result.reasons),
            )
            return
        logger.warning(
            "provider_failure_control: blocked failure_id=%s provider=%s type=%s severity=%s reasons=%s",
            result.failure_id,
            result.provider_id,
            result.failure_type,
            result.failure_severity,
            ",".join(result.reasons),
        )
