"""
Operational safety checks for Hermes orchestration runtime.

This layer inspects orchestration coordination signals and runtime visibility
to prevent unsafe orchestration flow. It does not schedule work, retry work,
recover executions, call providers, or mutate database state.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.config import settings

logger = logging.getLogger(__name__)

CONFLICT_REASONS = {
    "runtime_owner_mismatch",
    "execution_task_mismatch",
    "dependency_unsatisfied",
    "invalid_execution_sequence",
    "duplicate_dependency",
    "dependency_self_reference",
    "max_active_orchestrations_reached",
    "max_orchestration_load_reached",
    "coordination_not_permitted",
}
DEPENDENCY_CORRUPTION_REASONS = {
    "orphan_dependency",
    "missing_dependency_state",
    "invalid_dependency_order",
    "duplicate_dependency",
    "dependency_self_reference",
    "dependency_loop_detected",
    "dependency_chain_loop_detected",
    "max_execution_dependencies_reached",
    "max_dependency_chain_reached",
}
SEQUENCING_REASONS = {
    "invalid_execution_order",
    "invalid_execution_sequence",
    "invalid_dependency_order",
}
RUNAWAY_REASONS = {
    "orchestration_saturation_detected",
    "orchestration_load_degraded",
    "dependency_runaway_detected",
    "max_active_orchestrations_reached",
    "max_orchestration_load_reached",
    "max_execution_dependencies_reached",
    "max_dependency_chain_reached",
    "max_orchestration_safety_retries_reached",
}
TIMEOUT_REASONS = {
    "max_orchestration_duration_reached",
    "coordination_overhead_exceeded",
    "orchestration_timeout_detected",
    "orchestration_safety_overhead_exceeded",
}
ERROR_REASONS = {
    "orchestration_error_contained",
    "coordination_error_contained",
    "orchestration_failed",
}


@dataclass(frozen=True)
class OrchestrationSafetyResult:
    status: str
    success: bool
    safety_state: str
    allows_orchestration: bool
    runtime_protected: bool = True
    conflict_detected: bool = False
    dependency_corruption_detected: bool = False
    sequencing_violation_detected: bool = False
    runaway_detected: bool = False
    timeout_detected: bool = False
    retry_allowed: bool = True
    retry_attempts: int = 0
    max_retries: int = 0
    safety_id: str | None = None
    orchestration_id: str | None = None
    coordination_id: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    runtime_owner: str | None = None
    orchestration_status: str | None = None
    coordination_state: str | None = None
    dependency_status: str | None = None
    execution_sequence: int = 0
    dependency_count: int = 0
    max_execution_dependencies: int = 0
    max_dependency_chain: int = 0
    active_orchestrations: int = 0
    max_active_orchestrations: int = 0
    runtime_orchestration_load: float | None = None
    max_orchestration_load: float = 0.0
    coordination_duration_ms: int = 0
    max_orchestration_duration_ms: int = 0
    coordination_overhead_ms: int = 0
    max_coordination_overhead_ms: int = 0
    checked_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    duration_ms: int = 0
    dependencies: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success": self.success,
            "safety_state": self.safety_state,
            "allows_orchestration": self.allows_orchestration,
            "runtime_protected": self.runtime_protected,
            "conflict_detected": self.conflict_detected,
            "dependency_corruption_detected": (
                self.dependency_corruption_detected
            ),
            "sequencing_violation_detected": (
                self.sequencing_violation_detected
            ),
            "runaway_detected": self.runaway_detected,
            "timeout_detected": self.timeout_detected,
            "retry_allowed": self.retry_allowed,
            "retry_attempts": self.retry_attempts,
            "max_retries": self.max_retries,
            "safety_id": self.safety_id,
            "orchestration_id": self.orchestration_id,
            "coordination_id": self.coordination_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "runtime_owner": self.runtime_owner,
            "orchestration_status": self.orchestration_status,
            "coordination_state": self.coordination_state,
            "dependency_status": self.dependency_status,
            "execution_sequence": self.execution_sequence,
            "dependency_count": self.dependency_count,
            "max_execution_dependencies": self.max_execution_dependencies,
            "max_dependency_chain": self.max_dependency_chain,
            "active_orchestrations": self.active_orchestrations,
            "max_active_orchestrations": self.max_active_orchestrations,
            "runtime_orchestration_load": self.runtime_orchestration_load,
            "max_orchestration_load": self.max_orchestration_load,
            "coordination_duration_ms": self.coordination_duration_ms,
            "max_orchestration_duration_ms": (
                self.max_orchestration_duration_ms
            ),
            "coordination_overhead_ms": self.coordination_overhead_ms,
            "max_coordination_overhead_ms": self.max_coordination_overhead_ms,
            "checked_at": self.checked_at,
            "duration_ms": self.duration_ms,
            "dependencies": [dict(item) for item in self.dependencies],
            "metadata": dict(self.metadata),
            "reasons": list(self.reasons),
            "error": self.error,
        }


class OrchestrationSafety:
    def __init__(
        self,
        max_retries: int = settings.ORCHESTRATION_SAFETY_MAX_RETRIES,
        max_orchestration_duration_ms: int = (
            settings.ORCHESTRATION_MAX_DURATION_MS
        ),
        max_coordination_overhead_ms: int = settings.ORCHESTRATION_MAX_OVERHEAD_MS,
    ) -> None:
        self.max_retries = max(0, int(max_retries or 0))
        self.max_orchestration_duration_ms = max(
            1,
            int(max_orchestration_duration_ms or 1),
        )
        self.max_coordination_overhead_ms = max(
            1,
            int(max_coordination_overhead_ms or 1),
        )

    async def inspect(
        self,
        orchestration_result: Any | None = None,
        orchestration_visibility: dict[str, Any] | None = None,
        runtime_active: bool = True,
        retry_attempts: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> OrchestrationSafetyResult:
        return self.evaluate(
            orchestration_result=orchestration_result,
            orchestration_visibility=orchestration_visibility,
            runtime_active=runtime_active,
            retry_attempts=retry_attempts,
            metadata=metadata,
        )

    def evaluate(
        self,
        orchestration_result: Any | None = None,
        orchestration_visibility: dict[str, Any] | None = None,
        runtime_active: bool = True,
        retry_attempts: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> OrchestrationSafetyResult:
        started = time.perf_counter()
        try:
            result = self._as_dict(orchestration_result)
            visibility = dict(orchestration_visibility or {})
            metadata = dict(metadata or result.get("metadata") or {})
            attempts = self._retry_attempts(
                retry_attempts=retry_attempts,
                metadata=metadata,
                result=result,
            )
            reasons = self._safety_reasons(
                result=result,
                visibility=visibility,
                runtime_active=runtime_active,
                retry_attempts=attempts,
                started=started,
            )
            unique_reasons = self._unique(reasons)
            allows_orchestration = not unique_reasons
            status = "safe" if allows_orchestration else "blocked"
            safety_state = "safe" if allows_orchestration else "blocked"

            output = self._result(
                status=status,
                success=allows_orchestration,
                safety_state=safety_state,
                allows_orchestration=allows_orchestration,
                result=result,
                visibility=visibility,
                retry_attempts=attempts,
                metadata=metadata,
                reasons=unique_reasons,
                error=result.get("error"),
                started=started,
            )
            self._log_result(output)
            return output
        except Exception as exc:
            output = self._result(
                status="error",
                success=False,
                safety_state="error",
                allows_orchestration=False,
                retry_attempts=max(0, int(retry_attempts or 0)),
                metadata=metadata,
                reasons=["orchestration_safety_error_contained"],
                error=str(exc),
                started=started,
            )
            self._log_result(output)
            return output

    def _safety_reasons(
        self,
        result: dict[str, Any],
        visibility: dict[str, Any],
        runtime_active: bool,
        retry_attempts: int,
        started: float,
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        reasons.extend(str(reason) for reason in (result.get("reasons") or []))
        if result.get("status") in {"failed", "error"}:
            reasons.append("orchestration_error_contained")
        if result.get("conflict_detected"):
            reasons.append("orchestration_conflict_detected")
        if result.get("linkage_valid") is False:
            reasons.append("orchestration_linkage_invalid")
        if result.get("ownership_consistent") is False:
            reasons.append("orchestration_ownership_conflict")
        if result.get("dependency_valid") is False:
            reasons.append("dependency_corruption_detected")
        if result.get("sequencing_valid") is False:
            reasons.append("sequencing_violation_detected")
        reasons.extend(self._dependency_reasons(result))
        reasons.extend(self._visibility_reasons(result, visibility))
        reasons.extend(self._timeout_reasons(result, visibility))
        if retry_attempts >= self.max_retries and retry_attempts > 0:
            reasons.append("max_orchestration_safety_retries_reached")
        if self._duration_ms(started) > self.max_coordination_overhead_ms:
            reasons.append("orchestration_safety_overhead_exceeded")
        return self._unique(reasons)

    def _dependency_reasons(self, result: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        dependencies = self._dependencies(result)
        current_execution_id = result.get("execution_id")
        current_task_id = result.get("task_id")
        current_sequence = self._int(
            result.get("execution_sequence") or result.get("execution_order"),
            0,
        )
        seen: set[str] = set()
        for dependency in dependencies:
            key = self._dependency_key(dependency)
            if not key:
                reasons.append("orphan_dependency")
            elif key in seen:
                reasons.append("duplicate_dependency")
            else:
                seen.add(key)
            if self._is_self_reference(
                dependency,
                current_execution_id,
                current_task_id,
            ):
                reasons.append("dependency_self_reference")
            if self._dependency_chain_has_loop(
                dependency,
                current_execution_id,
                current_task_id,
            ):
                reasons.append("dependency_loop_detected")
            if not dependency.get("state"):
                reasons.append("missing_dependency_state")
            order = self._int(dependency.get("execution_order"), 0)
            if order < 0:
                reasons.append("invalid_dependency_order")
            if current_sequence > 0 and order >= current_sequence:
                reasons.append("invalid_execution_sequence")
            chain_depth = self._dependency_chain_depth(dependency)
            max_chain = self._int(result.get("max_dependency_chain"), 0)
            if max_chain > 0 and chain_depth > max_chain:
                reasons.append("max_dependency_chain_reached")
        return reasons

    def _visibility_reasons(
        self,
        result: dict[str, Any],
        visibility: dict[str, Any],
    ) -> list[str]:
        reasons: list[str] = []
        active = self._int(
            visibility.get("active_orchestrations"),
            self._int(result.get("active_orchestrations"), 0),
        )
        max_active = self._int(
            visibility.get("max_active_orchestrations"),
            self._int(result.get("max_active_orchestrations"), 0),
        )
        if max_active > 0 and active > max_active:
            reasons.append("orchestration_saturation_detected")

        runtime_load = self._maybe_float(
            visibility.get("runtime_orchestration_load")
            if visibility.get("runtime_orchestration_load") is not None
            else result.get("runtime_orchestration_load")
        )
        max_load = self._maybe_float(
            visibility.get("max_orchestration_load")
            if visibility.get("max_orchestration_load") is not None
            else result.get("max_orchestration_load")
        )
        if (
            runtime_load is not None
            and max_load is not None
            and max_load > 0
            and runtime_load > max_load
        ):
            reasons.append("orchestration_load_degraded")

        dependency_count = self._int(result.get("dependency_count"), 0)
        max_dependencies = self._int(
            visibility.get("max_execution_dependencies"),
            self._int(result.get("max_execution_dependencies"), 0),
        )
        if max_dependencies > 0 and dependency_count > max_dependencies:
            reasons.append("dependency_runaway_detected")
        return reasons

    def _timeout_reasons(
        self,
        result: dict[str, Any],
        visibility: dict[str, Any],
    ) -> list[str]:
        reasons: list[str] = []
        max_duration = self._int(
            result.get("max_orchestration_duration_ms")
            or visibility.get("max_orchestration_duration_ms"),
            self.max_orchestration_duration_ms,
        )
        duration = self._int(result.get("coordination_duration_ms"), 0)
        if max_duration > 0 and duration > max_duration:
            reasons.append("orchestration_timeout_detected")

        max_overhead = self._int(
            result.get("max_coordination_overhead_ms")
            or visibility.get("max_coordination_overhead_ms"),
            self.max_coordination_overhead_ms,
        )
        overhead = self._int(result.get("coordination_overhead_ms"), 0)
        if max_overhead > 0 and overhead > max_overhead:
            reasons.append("coordination_overhead_exceeded")
        return reasons

    def _result(
        self,
        status: str,
        success: bool,
        safety_state: str,
        allows_orchestration: bool,
        result: dict[str, Any] | None = None,
        visibility: dict[str, Any] | None = None,
        retry_attempts: int = 0,
        metadata: dict[str, Any] | None = None,
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
    ) -> OrchestrationSafetyResult:
        result = result or {}
        visibility = visibility or {}
        reasons = reasons or []
        active = self._int(
            visibility.get("active_orchestrations"),
            self._int(result.get("active_orchestrations"), 0),
        )
        max_active = self._int(
            visibility.get("max_active_orchestrations"),
            self._int(result.get("max_active_orchestrations"), 0),
        )
        runtime_load = self._maybe_float(
            visibility.get("runtime_orchestration_load")
            if visibility.get("runtime_orchestration_load") is not None
            else result.get("runtime_orchestration_load")
        )
        max_load = self._maybe_float(
            visibility.get("max_orchestration_load")
            if visibility.get("max_orchestration_load") is not None
            else result.get("max_orchestration_load")
        )
        orchestration_id = result.get("orchestration_id")
        coordination_id = result.get("coordination_id") or orchestration_id
        return OrchestrationSafetyResult(
            status=status,
            success=success,
            safety_state=safety_state,
            allows_orchestration=allows_orchestration,
            runtime_protected=True,
            conflict_detected=self._has_any(reasons, CONFLICT_REASONS)
            or "orchestration_conflict_detected" in reasons,
            dependency_corruption_detected=self._has_any(
                reasons,
                DEPENDENCY_CORRUPTION_REASONS,
            )
            or "dependency_corruption_detected" in reasons,
            sequencing_violation_detected=self._has_any(
                reasons,
                SEQUENCING_REASONS,
            )
            or "sequencing_violation_detected" in reasons,
            runaway_detected=self._has_any(reasons, RUNAWAY_REASONS),
            timeout_detected=self._has_any(reasons, TIMEOUT_REASONS),
            retry_allowed=retry_attempts < self.max_retries,
            retry_attempts=max(0, int(retry_attempts or 0)),
            max_retries=self.max_retries,
            safety_id=str(uuid4()) if status != "safe" else None,
            orchestration_id=orchestration_id,
            coordination_id=coordination_id,
            execution_id=result.get("execution_id"),
            task_id=result.get("task_id"),
            runtime_owner=result.get("runtime_owner")
            or visibility.get("runtime_owner"),
            orchestration_status=result.get("status"),
            coordination_state=result.get("coordination_state")
            or result.get("orchestration_state"),
            dependency_status=result.get("dependency_status")
            or result.get("dependency_state"),
            execution_sequence=self._int(
                result.get("execution_sequence") or result.get("execution_order"),
                0,
            ),
            dependency_count=self._int(result.get("dependency_count"), 0),
            max_execution_dependencies=self._int(
                visibility.get("max_execution_dependencies"),
                self._int(result.get("max_execution_dependencies"), 0),
            ),
            max_dependency_chain=self._int(
                visibility.get("max_dependency_chain"),
                self._int(result.get("max_dependency_chain"), 0),
            ),
            active_orchestrations=max(0, active),
            max_active_orchestrations=max(0, max_active),
            runtime_orchestration_load=runtime_load,
            max_orchestration_load=max(0.0, float(max_load or 0.0)),
            coordination_duration_ms=self._int(
                result.get("coordination_duration_ms"),
                0,
            ),
            max_orchestration_duration_ms=self._int(
                result.get("max_orchestration_duration_ms")
                or visibility.get("max_orchestration_duration_ms"),
                self.max_orchestration_duration_ms,
            ),
            coordination_overhead_ms=self._int(
                result.get("coordination_overhead_ms"),
                0,
            ),
            max_coordination_overhead_ms=self._int(
                result.get("max_coordination_overhead_ms")
                or visibility.get("max_coordination_overhead_ms"),
                self.max_coordination_overhead_ms,
            ),
            duration_ms=self._duration_ms(started),
            dependencies=tuple(self._safe_dependencies(result)),
            metadata=dict(metadata or {}),
            reasons=tuple(reasons),
            error=error,
        )

    def _dependencies(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        dependencies = result.get("dependencies") or []
        output: list[dict[str, Any]] = []
        for dependency in dependencies:
            output.append(dependency if isinstance(dependency, dict) else {})
        return output

    def _safe_dependencies(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            return self._dependencies(result)
        except Exception:
            return []

    def _dependency_key(self, dependency: dict[str, Any]) -> str | None:
        for key in ("dependency_id", "execution_id", "task_id"):
            value = dependency.get(key)
            if value:
                return f"{key}:{value}"
        return None

    def _is_self_reference(
        self,
        dependency: dict[str, Any],
        execution_id: Any,
        task_id: Any,
    ) -> bool:
        return bool(
            (
                dependency.get("execution_id")
                and execution_id
                and str(dependency.get("execution_id")) == str(execution_id)
            )
            or (
                dependency.get("task_id")
                and task_id
                and str(dependency.get("task_id")) == str(task_id)
            )
        )

    def _dependency_chain_has_loop(
        self,
        dependency: dict[str, Any],
        execution_id: Any,
        task_id: Any,
    ) -> bool:
        chain = dependency.get("dependency_chain") or []
        if not isinstance(chain, (list, tuple)):
            chain = [chain]
        normalized = [str(item) for item in chain if item is not None]
        if len(normalized) != len(set(normalized)):
            return True
        current = {str(value) for value in (execution_id, task_id) if value}
        return bool(current.intersection(normalized))

    def _dependency_chain_depth(self, dependency: dict[str, Any]) -> int:
        chain = dependency.get("dependency_chain")
        chain_length = len(chain) if isinstance(chain, (list, tuple)) else 0
        return max(self._int(dependency.get("chain_depth"), 1), chain_length)

    def _retry_attempts(
        self,
        retry_attempts: int,
        metadata: dict[str, Any],
        result: dict[str, Any],
    ) -> int:
        raw_attempts = (
            retry_attempts
            or metadata.get("orchestration_retry_attempts")
            or metadata.get("coordination_retry_attempts")
            or result.get("retry_attempts")
            or 0
        )
        return max(0, self._int(raw_attempts, 0))

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

    def _int(self, value: Any, default: int) -> int:
        try:
            if value is None:
                return int(default)
            return int(value)
        except (TypeError, ValueError):
            return int(default)

    def _maybe_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _duration_ms(self, started: float | None) -> int:
        return int((time.perf_counter() - started) * 1000) if started else 0

    def _has_any(self, reasons: list[str], candidates: set[str]) -> bool:
        return any(reason in candidates for reason in reasons)

    def _unique(self, reasons: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for reason in reasons:
            if reason and reason not in seen:
                seen.add(reason)
                unique.append(reason)
        return unique

    def _log_result(self, result: OrchestrationSafetyResult) -> None:
        if result.status == "safe":
            logger.debug(
                "orchestration_safety: safe active_orchestrations=%s load=%s",
                result.active_orchestrations,
                result.runtime_orchestration_load,
            )
            return
        if result.status == "error":
            logger.error(
                "orchestration_safety: error reasons=%s error=%s",
                ",".join(result.reasons),
                result.error,
            )
            return
        logger.warning(
            "orchestration_safety: blocked coordination_id=%s reasons=%s",
            result.coordination_id,
            ",".join(result.reasons),
        )
