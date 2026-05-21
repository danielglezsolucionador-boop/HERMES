"""
Operational stress test validation for Hermes runtime stability.

This layer evaluates bounded stress-test reports and blocks unsafe
continuation when runtime, memory, execution, or governance degradation is
detected. It does not start background loops or mutate runtime core behavior.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

STRESS_TEST_STATUS_PASSED = "passed"
STRESS_TEST_STATUS_BLOCKED = "blocked"
STRESS_TEST_STATUS_ERROR = "error"

SAFE_RUNTIME_STATUSES = {"active", "online", "ready", "stable", "resumed"}
SAFE_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "governance_approved",
    "stable",
}
SAFE_CONTINUATION_STATUSES = {
    "ready",
    "active",
    "continued",
    "resumed",
    "authorized_by_human",
    "recovery_validated",
}
SAFE_RECOVERY_STATUSES = {
    None,
    "",
    "ready",
    "standby",
    "not_required",
    "available",
    "recovered",
}


@dataclass(frozen=True)
class StressTestRequest:
    stress_id: str | None = None
    workflow_id: str | None = None
    runtime_status: str | None = "online"
    continuation_status: str | None = "ready"
    governance_status: str | None = "approved"
    recovery_status: str | None = "ready"
    runtime_state: dict[str, Any] = field(default_factory=dict)
    runtime_load: float | None = None
    max_runtime_load: float = 0.85
    workflow_concurrency: int = 0
    max_workflow_concurrency: int = 10
    duration_seconds: float = 0.0
    min_duration_seconds: float = 0.0
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
    workflow_validation: dict[str, Any] | Any | None = None
    workflow_recovery_control: dict[str, Any] | Any | None = None
    failure_conditions: tuple[str, ...] = field(default_factory=tuple)
    degradation_signals: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    ignore_runtime_degradation_requested: bool = False
    minimize_performance_failures_requested: bool = False
    hide_execution_instability_requested: bool = False
    overwrite_operational_limits_requested: bool = False
    continue_corrupt_runtime_requested: bool = False
    falsify_stress_results_requested: bool = False
    alter_stress_metrics_requested: bool = False
    ignore_failure_conditions_requested: bool = False
    minimize_instability_risks_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StressTestResult:
    status: str
    success: bool
    stress_id: str
    workflow_id: str | None
    runtime_status: str | None
    continuation_status: str | None
    governance_status: str | None
    recovery_status: str | None
    runtime_load: float | None
    workflow_concurrency: int
    duration_seconds: float
    execution_cycles: int
    successful_cycles: int
    failed_cycles: int
    memory_usage_mb: float | None
    memory_growth_mb: float
    runtime_integrity_valid: bool
    execution_continuity_valid: bool
    performance_status_valid: bool
    memory_stability_valid: bool
    governance_stability_valid: bool
    recovery_status_valid: bool
    operational_resilience_valid: bool
    stress_safe: bool
    continuation_allowed: bool
    degradation_detected: bool
    failure_conditions: tuple[str, ...] = field(default_factory=tuple)
    bottlenecks: tuple[str, ...] = field(default_factory=tuple)
    stress_report: dict[str, Any] = field(default_factory=dict)
    human_visibility_payload: dict[str, Any] = field(default_factory=dict)
    stress_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "stress_id": self.stress_id,
            "workflow_id": self.workflow_id,
            "runtime_status": self.runtime_status,
            "continuation_status": self.continuation_status,
            "governance_status": self.governance_status,
            "recovery_status": self.recovery_status,
            "runtime_load": self.runtime_load,
            "workflow_concurrency": self.workflow_concurrency,
            "duration_seconds": self.duration_seconds,
            "execution_cycles": self.execution_cycles,
            "successful_cycles": self.successful_cycles,
            "failed_cycles": self.failed_cycles,
            "memory_usage_mb": self.memory_usage_mb,
            "memory_growth_mb": self.memory_growth_mb,
            "runtime_integrity_valid": self.runtime_integrity_valid,
            "execution_continuity_valid": self.execution_continuity_valid,
            "performance_status_valid": self.performance_status_valid,
            "memory_stability_valid": self.memory_stability_valid,
            "governance_stability_valid": self.governance_stability_valid,
            "recovery_status_valid": self.recovery_status_valid,
            "operational_resilience_valid": self.operational_resilience_valid,
            "stress_safe": self.stress_safe,
            "continuation_allowed": self.continuation_allowed,
            "degradation_detected": self.degradation_detected,
            "failure_conditions": list(self.failure_conditions),
            "bottlenecks": list(self.bottlenecks),
            "stress_report": dict(self.stress_report),
            "human_visibility_payload": dict(self.human_visibility_payload),
            "stress_lifecycle": [
                dict(entry) for entry in self.stress_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class StressTests:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def run(self, request: StressTestRequest) -> StressTestResult:
        return self.evaluate(request)

    def evaluate(self, request: StressTestRequest) -> StressTestResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        stress_id = request.stress_id or str(uuid4())

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
                    STRESS_TEST_STATUS_BLOCKED
                    if blocked
                    else STRESS_TEST_STATUS_PASSED
                ),
                success=not blocked,
                stress_id=stress_id,
                request=request,
                context=context,
                checks=checks,
                failure_conditions=failure_conditions,
                bottlenecks=bottlenecks,
                reasons=reasons or ["stress_test_completed"],
                error=";".join(reasons) if blocked else None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                stress_id=stress_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def _context(self, request: StressTestRequest) -> dict[str, Any]:
        workflow_validation = self._as_dict(request.workflow_validation)
        recovery = self._as_dict(request.workflow_recovery_control)
        return {
            "workflow_id": (
                request.workflow_id
                or workflow_validation.get("workflow_id")
                or recovery.get("workflow_id")
            ),
            "runtime_status": request.runtime_status,
            "continuation_status": (
                request.continuation_status
                or workflow_validation.get("continuation_status")
                or recovery.get("continuation_status")
            ),
            "governance_status": (
                request.governance_status
                or workflow_validation.get("governance_status")
                or recovery.get("governance_status")
            ),
            "recovery_status": request.recovery_status
            or recovery.get("status")
            or recovery.get("recovery_status"),
            "workflow_validation": workflow_validation,
            "workflow_recovery_control": recovery,
        }

    def _checks(
        self,
        request: StressTestRequest,
        context: dict[str, Any],
    ) -> dict[str, bool]:
        runtime_status = self._normalize(context["runtime_status"])
        continuation_status = self._normalize(context["continuation_status"])
        governance_status = self._normalize(context["governance_status"])
        recovery_status = self._normalize(context["recovery_status"])
        workflow_validation = context["workflow_validation"]
        return {
            "runtime_integrity": bool(
                runtime_status in SAFE_RUNTIME_STATUSES
                and self._runtime_state_safe(request.runtime_state)
                and self._runtime_load_safe(request)
            ),
            "execution_continuity": bool(
                continuation_status in SAFE_CONTINUATION_STATUSES
                and request.execution_cycles > 0
                and request.successful_cycles >= 0
                and request.failed_cycles <= request.max_failed_cycles
                and request.successful_cycles + request.failed_cycles
                <= request.execution_cycles
            ),
            "performance_status": bool(
                self._performance_safe(request)
                and request.workflow_concurrency
                <= request.max_workflow_concurrency
            ),
            "memory_stability": bool(
                self._memory_safe(request)
                and request.memory_growth_mb <= request.max_memory_growth_mb
            ),
            "governance_stability": bool(
                governance_status in SAFE_GOVERNANCE_STATUSES
                and self._workflow_validation_safe(workflow_validation)
            ),
            "recovery_status": recovery_status in SAFE_RECOVERY_STATUSES,
            "operational_resilience": bool(
                not request.failure_conditions
                and not request.degradation_signals
                and not request.blocking_conditions
            ),
        }

    def _failure_conditions(
        self,
        request: StressTestRequest,
        context: dict[str, Any],
        checks: dict[str, bool],
    ) -> list[str]:
        failures = [
            *[str(item) for item in request.failure_conditions],
            *[str(item) for item in request.degradation_signals],
            *[str(item) for item in request.blocking_conditions],
        ]
        for name, valid in checks.items():
            if not valid:
                failures.append(f"{name}_failed")
        if not self._runtime_load_safe(request):
            failures.append("runtime_load_degraded")
        if request.workflow_concurrency > request.max_workflow_concurrency:
            failures.append("workflow_concurrency_exceeded")
        if request.failed_cycles > request.max_failed_cycles:
            failures.append("execution_failures_detected")
        if not self._performance_safe(request):
            failures.append("execution_slowdown_detected")
        if not self._memory_safe(request):
            failures.append("memory_usage_degraded")
        if request.memory_growth_mb > request.max_memory_growth_mb:
            failures.append("memory_growth_degraded")
        if self._normalize(context["governance_status"]) not in (
            SAFE_GOVERNANCE_STATUSES
        ):
            failures.append("governance_instability_detected")
        if self._normalize(context["recovery_status"]) not in (
            SAFE_RECOVERY_STATUSES
        ):
            failures.append("recovery_status_unavailable")
        if not self._workflow_validation_safe(context["workflow_validation"]):
            failures.append("workflow_validation_failed")
        return self._unique(failures)

    def _reasons(
        self,
        request: StressTestRequest,
        checks: dict[str, bool],
        failure_conditions: tuple[str, ...],
    ) -> list[str]:
        reasons: list[str] = []
        for name, valid in checks.items():
            if not valid:
                reasons.append(f"{name}_required")
        if failure_conditions:
            reasons.append("stress_failure_conditions_detected")
        if request.ignore_runtime_degradation_requested:
            reasons.append("runtime_degradation_ignore_blocked")
        if request.minimize_performance_failures_requested:
            reasons.append("performance_failure_minimization_blocked")
        if request.hide_execution_instability_requested:
            reasons.append("execution_instability_concealment_blocked")
        if request.overwrite_operational_limits_requested:
            reasons.append("operational_limit_overwrite_blocked")
        if request.continue_corrupt_runtime_requested:
            reasons.append("corrupt_runtime_continuation_blocked")
        if request.falsify_stress_results_requested:
            reasons.append("stress_result_falsification_blocked")
        if request.alter_stress_metrics_requested:
            reasons.append("stress_metric_alteration_blocked")
        if request.ignore_failure_conditions_requested and failure_conditions:
            reasons.append("failure_condition_ignore_blocked")
        if request.minimize_instability_risks_requested and failure_conditions:
            reasons.append("instability_risk_minimization_blocked")
        return self._unique(reasons)

    def _result(
        self,
        status: str,
        success: bool,
        stress_id: str,
        request: StressTestRequest,
        context: dict[str, Any],
        checks: dict[str, bool],
        failure_conditions: tuple[str, ...],
        bottlenecks: tuple[str, ...],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> StressTestResult:
        finished_at = datetime.now(timezone.utc)
        stress_safe = success and all(checks.values())
        return StressTestResult(
            status=status,
            success=success,
            stress_id=stress_id,
            workflow_id=context["workflow_id"],
            runtime_status=context["runtime_status"],
            continuation_status=context["continuation_status"],
            governance_status=context["governance_status"],
            recovery_status=context["recovery_status"],
            runtime_load=request.runtime_load,
            workflow_concurrency=request.workflow_concurrency,
            duration_seconds=request.duration_seconds,
            execution_cycles=request.execution_cycles,
            successful_cycles=request.successful_cycles,
            failed_cycles=request.failed_cycles,
            memory_usage_mb=request.memory_usage_mb,
            memory_growth_mb=request.memory_growth_mb,
            runtime_integrity_valid=checks["runtime_integrity"],
            execution_continuity_valid=checks["execution_continuity"],
            performance_status_valid=checks["performance_status"],
            memory_stability_valid=checks["memory_stability"],
            governance_stability_valid=checks["governance_stability"],
            recovery_status_valid=checks["recovery_status"],
            operational_resilience_valid=checks["operational_resilience"],
            stress_safe=stress_safe,
            continuation_allowed=stress_safe,
            degradation_detected=bool(failure_conditions),
            failure_conditions=failure_conditions,
            bottlenecks=bottlenecks,
            stress_report=self._report(checks, failure_conditions, bottlenecks),
            human_visibility_payload=self._visibility(
                request=request,
                context=context,
                checks=checks,
                failure_conditions=failure_conditions,
            ),
            stress_lifecycle=(
                self._lifecycle("load_initialization"),
                self._lifecycle("continuous_execution_validation"),
                self._lifecycle("performance_validation"),
                self._lifecycle("failure_detection"),
                self._lifecycle("stress_reporting"),
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
        request: StressTestRequest,
        context: dict[str, Any],
        checks: dict[str, bool],
        failure_conditions: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "runtime_performance": {
                "runtime_load": request.runtime_load,
                "avg_execution_ms": request.avg_execution_ms,
                "memory_usage_mb": request.memory_usage_mb,
            },
            "execution_continuity": checks["execution_continuity"],
            "degradation_detected": bool(failure_conditions),
            "failure_conditions": list(failure_conditions),
            "governance_stability": checks["governance_stability"],
            "operational_resilience": checks["operational_resilience"],
            "workflow_id": context["workflow_id"],
        }

    def _error_result(
        self,
        stress_id: str,
        request: StressTestRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> StressTestResult:
        return self._result(
            status=STRESS_TEST_STATUS_ERROR,
            success=False,
            stress_id=stress_id,
            request=request,
            context={
                "workflow_id": request.workflow_id,
                "runtime_status": request.runtime_status,
                "continuation_status": request.continuation_status,
                "governance_status": request.governance_status,
                "recovery_status": request.recovery_status,
            },
            checks={
                "runtime_integrity": False,
                "execution_continuity": False,
                "performance_status": False,
                "memory_stability": False,
                "governance_stability": False,
                "recovery_status": False,
                "operational_resilience": False,
            },
            failure_conditions=tuple(request.failure_conditions),
            bottlenecks=tuple(),
            reasons=["stress_test_error_contained"],
            error=error,
            started=started,
            started_at=started_at,
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

    def _runtime_load_safe(self, request: StressTestRequest) -> bool:
        if request.runtime_load is None:
            return True
        return request.runtime_load <= request.max_runtime_load

    def _performance_safe(self, request: StressTestRequest) -> bool:
        if request.max_execution_ms <= 0:
            return True
        return request.avg_execution_ms <= request.max_execution_ms

    def _memory_safe(self, request: StressTestRequest) -> bool:
        if request.memory_usage_mb is None:
            return True
        return request.memory_usage_mb <= request.max_memory_mb

    def _workflow_validation_safe(self, result: dict[str, Any]) -> bool:
        if not result:
            return True
        status = self._normalize(result.get("status"))
        return bool(
            result.get("success") is True
            and status in {"validated", "passed"}
            and result.get("workflow_safe", True) is not False
        )

    def _bottlenecks(
        self,
        failure_conditions: tuple[str, ...],
    ) -> list[str]:
        candidates = {
            "runtime_load_degraded": "runtime_load",
            "workflow_concurrency_exceeded": "workflow_concurrency",
            "execution_slowdown_detected": "execution_latency",
            "memory_usage_degraded": "memory_usage",
            "memory_growth_degraded": "memory_growth",
        }
        return self._unique(
            [
                candidates[condition]
                for condition in failure_conditions
                if condition in candidates
            ]
        )

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

    def _publish(self, result: StressTestResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_stress_test_result",
        ):
            self.status.mark_stress_test_result(result.to_dict())

    def _log_result(self, result: StressTestResult) -> None:
        if result.status == STRESS_TEST_STATUS_ERROR:
            logger.error(
                "stress_tests: error stress_id=%s error=%s",
                result.stress_id,
                result.error,
            )
            return
        if result.status == STRESS_TEST_STATUS_BLOCKED:
            logger.warning(
                "stress_tests: blocked stress_id=%s reasons=%s",
                result.stress_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "stress_tests: passed stress_id=%s workflow_id=%s",
            result.stress_id,
            result.workflow_id,
        )
