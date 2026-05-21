"""
Long-running runtime validation for Hermes operations.

This layer validates reported long-running execution metrics and blocks unsafe
continuation when persistent degradation appears. It does not start background
work, schedule loops, or mutate runtime core behavior.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

LONG_RUNNING_STATUS_VALIDATED = "validated"
LONG_RUNNING_STATUS_BLOCKED = "blocked"
LONG_RUNNING_STATUS_ERROR = "error"

SAFE_RUNTIME_STATUSES = {"active", "online", "ready", "stable", "resumed"}
SAFE_CONTINUATION_STATUSES = {
    "ready",
    "active",
    "continued",
    "resumed",
    "authorized_by_human",
    "recovery_validated",
}
SAFE_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "governance_approved",
    "stable",
}
SAFE_RECOVERY_STATUSES = {
    "ready",
    "standby",
    "not_required",
    "available",
    "recovered",
    "restored",
    "recovery_validated",
}


@dataclass(frozen=True)
class LongRunningValidationRequest:
    validation_id: str | None = None
    workflow_id: str | None = None
    runtime_duration_seconds: float = 0.0
    min_runtime_duration_seconds: float = 0.0
    runtime_status: str | None = "online"
    continuation_status: str | None = "ready"
    governance_status: str | None = "approved"
    recovery_status: str | None = "recovered"
    runtime_state: dict[str, Any] = field(default_factory=dict)
    execution_cycles: int = 0
    successful_cycles: int = 0
    failed_cycles: int = 0
    max_failed_cycles: int = 0
    avg_execution_ms: int = 0
    max_execution_ms: int = 0
    memory_usage_mb: float | None = None
    max_memory_mb: float = 512.0
    memory_growth_mb: float = 0.0
    max_memory_growth_mb: float = 64.0
    stress_test: dict[str, Any] | Any | None = None
    failure_recovery: dict[str, Any] | Any | None = None
    restart_persistence: dict[str, Any] | Any | None = None
    failure_conditions: tuple[str, ...] = field(default_factory=tuple)
    degradation_signals: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    ignore_runtime_degradation_requested: bool = False
    minimize_instability_risks_requested: bool = False
    hide_execution_slowdown_requested: bool = False
    overwrite_operational_limits_requested: bool = False
    continue_corrupt_runtime_requested: bool = False
    falsify_runtime_duration_requested: bool = False
    alter_runtime_metrics_requested: bool = False
    ignore_persistent_degradation_requested: bool = False
    minimize_instability_conditions_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LongRunningValidationResult:
    status: str
    success: bool
    validation_id: str
    workflow_id: str | None
    runtime_duration_seconds: float
    runtime_status: str | None
    continuation_status: str | None
    governance_status: str | None
    recovery_status: str | None
    execution_cycles: int
    successful_cycles: int
    failed_cycles: int
    runtime_duration_valid: bool
    runtime_integrity_valid: bool
    execution_continuity_valid: bool
    performance_stability_valid: bool
    memory_consistency_valid: bool
    governance_stability_valid: bool
    recovery_status_valid: bool
    operational_resilience_valid: bool
    long_running_safe: bool
    continuation_allowed: bool
    degradation_detected: bool
    workflow_traceability_preserved: bool
    governance_consistency_preserved: bool
    failure_conditions: tuple[str, ...] = field(default_factory=tuple)
    bottlenecks: tuple[str, ...] = field(default_factory=tuple)
    validation_report: dict[str, Any] = field(default_factory=dict)
    human_visibility_payload: dict[str, Any] = field(default_factory=dict)
    validation_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "validation_id": self.validation_id,
            "workflow_id": self.workflow_id,
            "runtime_duration_seconds": self.runtime_duration_seconds,
            "runtime_status": self.runtime_status,
            "continuation_status": self.continuation_status,
            "governance_status": self.governance_status,
            "recovery_status": self.recovery_status,
            "execution_cycles": self.execution_cycles,
            "successful_cycles": self.successful_cycles,
            "failed_cycles": self.failed_cycles,
            "runtime_duration_valid": self.runtime_duration_valid,
            "runtime_integrity_valid": self.runtime_integrity_valid,
            "execution_continuity_valid": self.execution_continuity_valid,
            "performance_stability_valid": self.performance_stability_valid,
            "memory_consistency_valid": self.memory_consistency_valid,
            "governance_stability_valid": self.governance_stability_valid,
            "recovery_status_valid": self.recovery_status_valid,
            "operational_resilience_valid": self.operational_resilience_valid,
            "long_running_safe": self.long_running_safe,
            "continuation_allowed": self.continuation_allowed,
            "degradation_detected": self.degradation_detected,
            "workflow_traceability_preserved": (
                self.workflow_traceability_preserved
            ),
            "governance_consistency_preserved": (
                self.governance_consistency_preserved
            ),
            "failure_conditions": list(self.failure_conditions),
            "bottlenecks": list(self.bottlenecks),
            "validation_report": dict(self.validation_report),
            "human_visibility_payload": dict(self.human_visibility_payload),
            "validation_lifecycle": [
                dict(entry) for entry in self.validation_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class LongRunningValidation:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def validate(
        self,
        request: LongRunningValidationRequest,
    ) -> LongRunningValidationResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        validation_id = request.validation_id or str(uuid4())

        try:
            context = self._context(request)
            checks = self._checks(request, context)
            failure_conditions = tuple(
                self._failure_conditions(request, context, checks)
            )
            bottlenecks = tuple(self._bottlenecks(failure_conditions))
            reasons = self._reasons(request, checks, failure_conditions)
            blocked = bool(reasons)
            result = self._result(
                status=(
                    LONG_RUNNING_STATUS_BLOCKED
                    if blocked
                    else LONG_RUNNING_STATUS_VALIDATED
                ),
                success=not blocked,
                validation_id=validation_id,
                request=request,
                context=context,
                checks=checks,
                failure_conditions=failure_conditions,
                bottlenecks=bottlenecks,
                reasons=reasons or ["long_running_validation_completed"],
                error=";".join(reasons) if blocked else None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                validation_id=validation_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def _context(
        self,
        request: LongRunningValidationRequest,
    ) -> dict[str, Any]:
        stress = self._as_dict(request.stress_test)
        failure_recovery = self._as_dict(request.failure_recovery)
        restart_persistence = self._as_dict(request.restart_persistence)
        return {
            "workflow_id": (
                request.workflow_id
                or stress.get("workflow_id")
                or failure_recovery.get("workflow_id")
                or restart_persistence.get("workflow_id")
            ),
            "runtime_status": request.runtime_status,
            "continuation_status": (
                request.continuation_status
                or restart_persistence.get("continuation_status")
                or failure_recovery.get("continuation_status")
            ),
            "governance_status": (
                request.governance_status
                or restart_persistence.get("governance_status")
                or failure_recovery.get("governance_status")
            ),
            "recovery_status": (
                request.recovery_status
                or restart_persistence.get("recovery_status")
                or failure_recovery.get("recovery_status")
            ),
            "stress": stress,
            "failure_recovery": failure_recovery,
            "restart_persistence": restart_persistence,
        }

    def _checks(
        self,
        request: LongRunningValidationRequest,
        context: dict[str, Any],
    ) -> dict[str, bool]:
        return {
            "runtime_duration": (
                request.runtime_duration_seconds
                >= request.min_runtime_duration_seconds
            ),
            "runtime_integrity": bool(
                self._normalize(context["runtime_status"])
                in SAFE_RUNTIME_STATUSES
                and self._runtime_state_safe(request.runtime_state)
                and not self._upstream_blocked(context["failure_recovery"])
            ),
            "execution_continuity": bool(
                context["workflow_id"]
                and self._normalize(context["continuation_status"])
                in SAFE_CONTINUATION_STATUSES
                and request.execution_cycles > 0
                and request.successful_cycles + request.failed_cycles
                <= request.execution_cycles
                and request.failed_cycles <= request.max_failed_cycles
            ),
            "performance_stability": self._performance_safe(request),
            "memory_consistency": bool(
                self._memory_safe(request)
                and request.memory_growth_mb <= request.max_memory_growth_mb
            ),
            "governance_stability": (
                self._normalize(context["governance_status"])
                in SAFE_GOVERNANCE_STATUSES
            ),
            "recovery_status": (
                self._normalize(context["recovery_status"])
                in SAFE_RECOVERY_STATUSES
            ),
            "operational_resilience": bool(
                not request.failure_conditions
                and not request.degradation_signals
                and not request.blocking_conditions
                and not self._upstream_blocked(context["stress"])
                and not self._upstream_blocked(context["restart_persistence"])
            ),
        }

    def _failure_conditions(
        self,
        request: LongRunningValidationRequest,
        context: dict[str, Any],
        checks: dict[str, bool],
    ) -> list[str]:
        failures = [
            *[str(item) for item in request.failure_conditions],
            *[str(item) for item in request.degradation_signals],
            *[str(item) for item in request.blocking_conditions],
        ]
        for key in ("stress", "failure_recovery", "restart_persistence"):
            upstream = context[key]
            if self._upstream_blocked(upstream):
                failures.append(f"{key}_{upstream.get('status')}")
            failures.extend(
                str(item) for item in upstream.get("failure_conditions", [])
            )
            failures.extend(
                str(item) for item in upstream.get("restart_conditions", [])
            )
        for name, valid in checks.items():
            if not valid:
                failures.append(f"{name}_failed")
        if not self._performance_safe(request):
            failures.append("execution_slowdown_detected")
        if not self._memory_safe(request):
            failures.append("memory_usage_degraded")
        if request.memory_growth_mb > request.max_memory_growth_mb:
            failures.append("memory_growth_degraded")
        return self._unique(failures)

    def _reasons(
        self,
        request: LongRunningValidationRequest,
        checks: dict[str, bool],
        failure_conditions: tuple[str, ...],
    ) -> list[str]:
        reasons: list[str] = []
        for name, valid in checks.items():
            if not valid:
                reasons.append(f"{name}_required")
        if failure_conditions:
            reasons.append("long_running_degradation_detected")
        if request.ignore_runtime_degradation_requested:
            reasons.append("runtime_degradation_ignore_blocked")
        if request.minimize_instability_risks_requested:
            reasons.append("instability_risk_minimization_blocked")
        if request.hide_execution_slowdown_requested:
            reasons.append("execution_slowdown_concealment_blocked")
        if request.overwrite_operational_limits_requested:
            reasons.append("operational_limit_overwrite_blocked")
        if request.continue_corrupt_runtime_requested:
            reasons.append("corrupt_runtime_continuation_blocked")
        if request.falsify_runtime_duration_requested:
            reasons.append("runtime_duration_falsification_blocked")
        if request.alter_runtime_metrics_requested:
            reasons.append("runtime_metric_alteration_blocked")
        if request.ignore_persistent_degradation_requested:
            reasons.append("persistent_degradation_ignore_blocked")
        if request.minimize_instability_conditions_requested:
            reasons.append("instability_condition_minimization_blocked")
        return self._unique(reasons)

    def _result(
        self,
        status: str,
        success: bool,
        validation_id: str,
        request: LongRunningValidationRequest,
        context: dict[str, Any],
        checks: dict[str, bool],
        failure_conditions: tuple[str, ...],
        bottlenecks: tuple[str, ...],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> LongRunningValidationResult:
        finished_at = datetime.now(timezone.utc)
        long_running_safe = success and all(checks.values())
        return LongRunningValidationResult(
            status=status,
            success=success,
            validation_id=validation_id,
            workflow_id=context["workflow_id"],
            runtime_duration_seconds=request.runtime_duration_seconds,
            runtime_status=context["runtime_status"],
            continuation_status=context["continuation_status"],
            governance_status=context["governance_status"],
            recovery_status=context["recovery_status"],
            execution_cycles=request.execution_cycles,
            successful_cycles=request.successful_cycles,
            failed_cycles=request.failed_cycles,
            runtime_duration_valid=checks["runtime_duration"],
            runtime_integrity_valid=checks["runtime_integrity"],
            execution_continuity_valid=checks["execution_continuity"],
            performance_stability_valid=checks["performance_stability"],
            memory_consistency_valid=checks["memory_consistency"],
            governance_stability_valid=checks["governance_stability"],
            recovery_status_valid=checks["recovery_status"],
            operational_resilience_valid=checks["operational_resilience"],
            long_running_safe=long_running_safe,
            continuation_allowed=long_running_safe,
            degradation_detected=bool(failure_conditions),
            workflow_traceability_preserved=success,
            governance_consistency_preserved=success
            and checks["governance_stability"],
            failure_conditions=failure_conditions,
            bottlenecks=bottlenecks,
            validation_report=self._report(
                checks,
                failure_conditions,
                bottlenecks,
            ),
            human_visibility_payload=self._visibility(
                request,
                context,
                checks,
                failure_conditions,
            ),
            validation_lifecycle=(
                self._lifecycle("execution_initialization"),
                self._lifecycle("continuous_execution_validation"),
                self._lifecycle("stability_validation"),
                self._lifecycle("degradation_detection"),
                self._lifecycle("long_running_reporting"),
            ),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons),
            error=error,
            metadata=dict(request.metadata),
        )

    def _report(
        self,
        checks: dict[str, bool],
        failure_conditions: tuple[str, ...],
        bottlenecks: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "checks": dict(checks),
            "degradation_detected": bool(failure_conditions),
            "failure_conditions": list(failure_conditions),
            "bottlenecks": list(bottlenecks),
            "continuation_status": (
                "allowed"
                if all(checks.values()) and not failure_conditions
                else "blocked"
            ),
        }

    def _visibility(
        self,
        request: LongRunningValidationRequest,
        context: dict[str, Any],
        checks: dict[str, bool],
        failure_conditions: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "runtime_duration": request.runtime_duration_seconds,
            "execution_continuity": checks["execution_continuity"],
            "degradation_detected": bool(failure_conditions),
            "failure_conditions": list(failure_conditions),
            "governance_stability": checks["governance_stability"],
            "operational_resilience": checks["operational_resilience"],
            "workflow_id": context["workflow_id"],
        }

    def _error_result(
        self,
        validation_id: str,
        request: LongRunningValidationRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> LongRunningValidationResult:
        return self._result(
            status=LONG_RUNNING_STATUS_ERROR,
            success=False,
            validation_id=validation_id,
            request=request,
            context={
                "workflow_id": request.workflow_id,
                "runtime_status": request.runtime_status,
                "continuation_status": request.continuation_status,
                "governance_status": request.governance_status,
                "recovery_status": request.recovery_status,
            },
            checks={
                "runtime_duration": False,
                "runtime_integrity": False,
                "execution_continuity": False,
                "performance_stability": False,
                "memory_consistency": False,
                "governance_stability": False,
                "recovery_status": False,
                "operational_resilience": False,
            },
            failure_conditions=tuple(request.failure_conditions),
            bottlenecks=tuple(),
            reasons=["long_running_validation_error_contained"],
            error=error,
            started=started,
            started_at=started_at,
        )

    def _runtime_state_safe(self, runtime_state: dict[str, Any]) -> bool:
        if not runtime_state:
            return True
        values = (
            runtime_state.get("state"),
            runtime_state.get("status"),
            runtime_state.get("loop_state"),
        )
        return any(
            self._normalize(value) in SAFE_RUNTIME_STATUSES
            for value in values
        )

    def _performance_safe(
        self,
        request: LongRunningValidationRequest,
    ) -> bool:
        if request.max_execution_ms <= 0:
            return True
        return request.avg_execution_ms <= request.max_execution_ms

    def _memory_safe(self, request: LongRunningValidationRequest) -> bool:
        if request.memory_usage_mb is None:
            return True
        return request.memory_usage_mb <= request.max_memory_mb

    def _upstream_blocked(self, result: dict[str, Any]) -> bool:
        if not result:
            return False
        return self._normalize(result.get("status")) in {"blocked", "error"}

    def _bottlenecks(
        self,
        failure_conditions: tuple[str, ...],
    ) -> list[str]:
        candidates = {
            "execution_slowdown_detected": "execution_latency",
            "memory_usage_degraded": "memory_usage",
            "memory_growth_degraded": "memory_growth",
            "runtime_integrity_failed": "runtime_integrity",
        }
        return self._unique(
            [
                candidates[condition]
                for condition in failure_conditions
                if condition in candidates
            ]
        )

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

    def _normalize(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower().replace("-", "_").replace(" ", "_")

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

    def _publish(self, result: LongRunningValidationResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_long_running_validation_result",
        ):
            self.status.mark_long_running_validation_result(result.to_dict())

    def _log_result(self, result: LongRunningValidationResult) -> None:
        if result.status == LONG_RUNNING_STATUS_ERROR:
            logger.error(
                "long_running_validation: error validation_id=%s error=%s",
                result.validation_id,
                result.error,
            )
            return
        if result.status == LONG_RUNNING_STATUS_BLOCKED:
            logger.warning(
                "long_running_validation: blocked validation_id=%s reasons=%s",
                result.validation_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "long_running_validation: validated validation_id=%s workflow_id=%s",
            result.validation_id,
            result.workflow_id,
        )
