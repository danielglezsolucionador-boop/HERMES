"""
Operational observability base for Hermes runtime visibility.

This layer builds an honest observability snapshot from existing runtime,
execution, performance, governance, and resilience metrics. It does not create
background monitors or alter observability history.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

OBSERVABILITY_STATUS_OBSERVED = "observed"
OBSERVABILITY_STATUS_BLOCKED = "blocked"
OBSERVABILITY_STATUS_ERROR = "error"

SAFE_STATUSES = {"active", "online", "ready", "stable", "resumed", "ok"}
SAFE_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "governance_approved",
    "stable",
}


@dataclass(frozen=True)
class ObservabilityBaseRequest:
    observation_id: str | None = None
    workflow_id: str | None = None
    runtime_status: dict[str, Any] = field(default_factory=dict)
    execution_status: dict[str, Any] = field(default_factory=dict)
    performance_metrics: dict[str, Any] = field(default_factory=dict)
    governance_status: dict[str, Any] = field(default_factory=dict)
    continuity_status: dict[str, Any] = field(default_factory=dict)
    stress_tests: dict[str, Any] | Any | None = None
    failure_recovery: dict[str, Any] | Any | None = None
    restart_persistence: dict[str, Any] | Any | None = None
    long_running_validation: dict[str, Any] | Any | None = None
    anomaly_signals: tuple[str, ...] = field(default_factory=tuple)
    failure_conditions: tuple[str, ...] = field(default_factory=tuple)
    degradation_conditions: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    hide_runtime_degradation_requested: bool = False
    minimize_critical_anomalies_requested: bool = False
    falsify_operational_metrics_requested: bool = False
    ignore_execution_instability_requested: bool = False
    overwrite_observability_history_requested: bool = False
    alter_runtime_metrics_requested: bool = False
    hide_workflow_failures_requested: bool = False
    ignore_governance_conflicts_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ObservabilityBaseResult:
    status: str
    success: bool
    observation_id: str
    workflow_id: str | None
    runtime_visibility_valid: bool
    execution_visibility_valid: bool
    performance_metrics_valid: bool
    governance_transparency_valid: bool
    continuity_visibility_valid: bool
    workflow_traceability_valid: bool
    operational_stability_valid: bool
    observability_consistent: bool
    continuation_allowed: bool
    anomalies_detected: bool
    degradation_detected: bool
    observed_components: tuple[str, ...] = field(default_factory=tuple)
    anomaly_conditions: tuple[str, ...] = field(default_factory=tuple)
    observability_report: dict[str, Any] = field(default_factory=dict)
    human_visibility_payload: dict[str, Any] = field(default_factory=dict)
    observability_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "observation_id": self.observation_id,
            "workflow_id": self.workflow_id,
            "runtime_visibility_valid": self.runtime_visibility_valid,
            "execution_visibility_valid": self.execution_visibility_valid,
            "performance_metrics_valid": self.performance_metrics_valid,
            "governance_transparency_valid": (
                self.governance_transparency_valid
            ),
            "continuity_visibility_valid": self.continuity_visibility_valid,
            "workflow_traceability_valid": self.workflow_traceability_valid,
            "operational_stability_valid": self.operational_stability_valid,
            "observability_consistent": self.observability_consistent,
            "continuation_allowed": self.continuation_allowed,
            "anomalies_detected": self.anomalies_detected,
            "degradation_detected": self.degradation_detected,
            "observed_components": list(self.observed_components),
            "anomaly_conditions": list(self.anomaly_conditions),
            "observability_report": dict(self.observability_report),
            "human_visibility_payload": dict(self.human_visibility_payload),
            "observability_lifecycle": [
                dict(entry) for entry in self.observability_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class ObservabilityBase:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def observe(
        self,
        request: ObservabilityBaseRequest,
    ) -> ObservabilityBaseResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        observation_id = request.observation_id or str(uuid4())

        try:
            context = self._context(request)
            checks = self._checks(request, context)
            anomalies = tuple(self._anomaly_conditions(request, context, checks))
            components = tuple(self._observed_components(request, context))
            reasons = self._reasons(request, checks, anomalies)
            blocked = bool(reasons)
            result = self._result(
                status=(
                    OBSERVABILITY_STATUS_BLOCKED
                    if blocked
                    else OBSERVABILITY_STATUS_OBSERVED
                ),
                success=not blocked,
                observation_id=observation_id,
                request=request,
                context=context,
                checks=checks,
                anomaly_conditions=anomalies,
                observed_components=components,
                reasons=reasons or ["observability_snapshot_created"],
                error=";".join(reasons) if blocked else None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                observation_id=observation_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def _context(self, request: ObservabilityBaseRequest) -> dict[str, Any]:
        return {
            "stress_tests": self._as_dict(request.stress_tests),
            "failure_recovery": self._as_dict(request.failure_recovery),
            "restart_persistence": self._as_dict(request.restart_persistence),
            "long_running_validation": self._as_dict(
                request.long_running_validation
            ),
        }

    def _checks(
        self,
        request: ObservabilityBaseRequest,
        context: dict[str, Any],
    ) -> dict[str, bool]:
        return {
            "runtime_visibility": bool(
                request.runtime_status
                and self._status_safe(request.runtime_status)
            ),
            "execution_visibility": bool(
                request.execution_status
                and self._status_safe(request.execution_status)
            ),
            "performance_metrics": bool(
                request.performance_metrics
                and not request.performance_metrics.get("degradation_detected")
            ),
            "governance_transparency": bool(
                request.governance_status
                and self._governance_safe(request.governance_status)
            ),
            "continuity_visibility": bool(
                request.continuity_status
                and self._status_safe(request.continuity_status)
            ),
            "workflow_traceability": bool(
                request.workflow_id
                and request.continuity_status.get(
                    "workflow_traceability_preserved",
                    True,
                )
                is not False
            ),
            "operational_stability": bool(
                not request.anomaly_signals
                and not request.failure_conditions
                and not request.degradation_conditions
                and not request.blocking_conditions
                and not self._any_upstream_blocked(context)
            ),
        }

    def _anomaly_conditions(
        self,
        request: ObservabilityBaseRequest,
        context: dict[str, Any],
        checks: dict[str, bool],
    ) -> list[str]:
        anomalies = [
            *[str(item) for item in request.anomaly_signals],
            *[str(item) for item in request.failure_conditions],
            *[str(item) for item in request.degradation_conditions],
            *[str(item) for item in request.blocking_conditions],
        ]
        for name, valid in checks.items():
            if not valid:
                anomalies.append(f"{name}_failed")
        for name, result in context.items():
            if self._upstream_blocked(result):
                anomalies.append(f"{name}_{result.get('status')}")
            for key in (
                "failure_conditions",
                "anomaly_conditions",
                "restart_conditions",
            ):
                anomalies.extend(str(item) for item in result.get(key, []))
        return self._unique(anomalies)

    def _observed_components(
        self,
        request: ObservabilityBaseRequest,
        context: dict[str, Any],
    ) -> list[str]:
        components = []
        if request.runtime_status:
            components.append("runtime_status")
        if request.execution_status:
            components.append("execution_status")
        if request.performance_metrics:
            components.append("performance_metrics")
        if request.governance_status:
            components.append("governance_status")
        if request.continuity_status:
            components.append("continuity_status")
        components.extend(name for name, value in context.items() if value)
        return self._unique(components)

    def _reasons(
        self,
        request: ObservabilityBaseRequest,
        checks: dict[str, bool],
        anomaly_conditions: tuple[str, ...],
    ) -> list[str]:
        reasons: list[str] = []
        for name, valid in checks.items():
            if not valid:
                reasons.append(f"{name}_required")
        if anomaly_conditions:
            reasons.append("observability_anomalies_detected")
        if request.hide_runtime_degradation_requested:
            reasons.append("runtime_degradation_concealment_blocked")
        if request.minimize_critical_anomalies_requested:
            reasons.append("critical_anomaly_minimization_blocked")
        if request.falsify_operational_metrics_requested:
            reasons.append("operational_metric_falsification_blocked")
        if request.ignore_execution_instability_requested:
            reasons.append("execution_instability_ignore_blocked")
        if request.overwrite_observability_history_requested:
            reasons.append("observability_history_overwrite_blocked")
        if request.alter_runtime_metrics_requested:
            reasons.append("runtime_metric_alteration_blocked")
        if request.hide_workflow_failures_requested:
            reasons.append("workflow_failure_concealment_blocked")
        if request.ignore_governance_conflicts_requested:
            reasons.append("governance_conflict_ignore_blocked")
        return self._unique(reasons)

    def _result(
        self,
        status: str,
        success: bool,
        observation_id: str,
        request: ObservabilityBaseRequest,
        context: dict[str, Any],
        checks: dict[str, bool],
        anomaly_conditions: tuple[str, ...],
        observed_components: tuple[str, ...],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> ObservabilityBaseResult:
        finished_at = datetime.now(timezone.utc)
        consistent = success and all(checks.values())
        return ObservabilityBaseResult(
            status=status,
            success=success,
            observation_id=observation_id,
            workflow_id=request.workflow_id,
            runtime_visibility_valid=checks["runtime_visibility"],
            execution_visibility_valid=checks["execution_visibility"],
            performance_metrics_valid=checks["performance_metrics"],
            governance_transparency_valid=checks["governance_transparency"],
            continuity_visibility_valid=checks["continuity_visibility"],
            workflow_traceability_valid=checks["workflow_traceability"],
            operational_stability_valid=checks["operational_stability"],
            observability_consistent=consistent,
            continuation_allowed=consistent,
            anomalies_detected=bool(anomaly_conditions),
            degradation_detected=self._degradation_detected(
                request,
                context,
                anomaly_conditions,
            ),
            observed_components=observed_components,
            anomaly_conditions=anomaly_conditions,
            observability_report=self._report(
                checks,
                anomaly_conditions,
                observed_components,
            ),
            human_visibility_payload=self._visibility(
                request,
                context,
                anomaly_conditions,
            ),
            observability_lifecycle=(
                self._lifecycle("runtime_monitoring"),
                self._lifecycle("execution_tracking"),
                self._lifecycle("anomaly_detection"),
                self._lifecycle("operational_validation"),
                self._lifecycle("observability_reporting"),
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
        anomaly_conditions: tuple[str, ...],
        observed_components: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "checks": dict(checks),
            "observed_components": list(observed_components),
            "anomalies_detected": bool(anomaly_conditions),
            "anomaly_conditions": list(anomaly_conditions),
        }

    def _visibility(
        self,
        request: ObservabilityBaseRequest,
        context: dict[str, Any],
        anomaly_conditions: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "runtime_status": dict(request.runtime_status),
            "execution_continuity": dict(request.continuity_status),
            "anomalies_detected": bool(anomaly_conditions),
            "degradation_conditions": list(request.degradation_conditions),
            "governance_stability": dict(request.governance_status),
            "operational_metrics": dict(request.performance_metrics),
            "upstream_components": list(context.keys()),
        }

    def _error_result(
        self,
        observation_id: str,
        request: ObservabilityBaseRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> ObservabilityBaseResult:
        return self._result(
            status=OBSERVABILITY_STATUS_ERROR,
            success=False,
            observation_id=observation_id,
            request=request,
            context={},
            checks={
                "runtime_visibility": False,
                "execution_visibility": False,
                "performance_metrics": False,
                "governance_transparency": False,
                "continuity_visibility": False,
                "workflow_traceability": False,
                "operational_stability": False,
            },
            anomaly_conditions=tuple(request.anomaly_signals),
            observed_components=tuple(),
            reasons=["observability_base_error_contained"],
            error=error,
            started=started,
            started_at=started_at,
        )

    def _status_safe(self, value: dict[str, Any]) -> bool:
        status = (
            value.get("status")
            or value.get("runner_status")
            or value.get("runtime_status")
            or value.get("continuation_status")
            or value.get("state")
        )
        return self._normalize(status) in SAFE_STATUSES

    def _governance_safe(self, value: dict[str, Any]) -> bool:
        status = value.get("status") or value.get("governance_status")
        return self._normalize(status) in SAFE_GOVERNANCE_STATUSES

    def _degradation_detected(
        self,
        request: ObservabilityBaseRequest,
        context: dict[str, Any],
        anomaly_conditions: tuple[str, ...],
    ) -> bool:
        return bool(
            request.degradation_conditions
            or request.performance_metrics.get("degradation_detected")
            or any(
                bool(value.get("degradation_detected"))
                for value in context.values()
            )
            or anomaly_conditions
        )

    def _any_upstream_blocked(self, context: dict[str, Any]) -> bool:
        return any(self._upstream_blocked(value) for value in context.values())

    def _upstream_blocked(self, value: dict[str, Any]) -> bool:
        if not value:
            return False
        return self._normalize(value.get("status")) in {"blocked", "error"}

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

    def _publish(self, result: ObservabilityBaseResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_observability_base_result",
        ):
            self.status.mark_observability_base_result(result.to_dict())

    def _log_result(self, result: ObservabilityBaseResult) -> None:
        if result.status == OBSERVABILITY_STATUS_ERROR:
            logger.error(
                "observability_base: error observation_id=%s error=%s",
                result.observation_id,
                result.error,
            )
            return
        if result.status == OBSERVABILITY_STATUS_BLOCKED:
            logger.warning(
                "observability_base: blocked observation_id=%s reasons=%s",
                result.observation_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "observability_base: observed observation_id=%s workflow_id=%s",
            result.observation_id,
            result.workflow_id,
        )
