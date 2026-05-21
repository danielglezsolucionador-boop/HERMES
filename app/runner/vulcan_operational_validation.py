"""
Vulcan operational validation for controlled Hermes backend workflows.

This layer validates runtime, imports, architecture, execution consistency,
governance, and security before a Vulcan workflow is considered complete. It
does not run commands or mutate runtime state.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.vulcan_execution_handoff import VulcanHandoffResult
from app.runner.vulcan_prompt_protocol import VulcanPromptResult
from app.runner.vulcan_scope_enforcement import VulcanScopeResult

logger = logging.getLogger(__name__)

VALIDATION_STATUS_VALIDATED = "validated"
VALIDATION_STATUS_BLOCKED = "blocked"
VALIDATION_STATUS_ERROR = "error"

PASSING_STATUSES = {
    "active",
    "approved",
    "clean",
    "clear",
    "ok",
    "online",
    "passed",
    "safe",
    "stable",
    "success",
    "valid",
    "validated",
}

FAILING_STATUSES = {
    "blocked",
    "broken",
    "corrupt",
    "critical",
    "error",
    "failed",
    "failing",
    "invalid",
    "unsafe",
}

CLEAR_BLOCKING_CONDITIONS = {
    "clear",
    "none",
    "no_blockers",
    "no_blocking_conditions",
}


@dataclass(frozen=True)
class VulcanOperationalValidationRequest:
    validation_id: str | None = None
    subphase_id: str | None = None
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    runtime_validation: Any | None = None
    import_validation: Any | None = None
    architecture_validation: Any | None = None
    execution_validation: Any | None = None
    governance_validation: Any | None = None
    security_validation: Any | None = None
    validations_executed: tuple[str, ...] = field(default_factory=tuple)
    tests_executed: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    prompt_protocol: VulcanPromptResult | dict[str, Any] | Any | None = None
    scope_enforcement: VulcanScopeResult | dict[str, Any] | Any | None = None
    execution_handoff: VulcanHandoffResult | dict[str, Any] | Any | None = None
    runtime_status: str | None = None
    governance_status: str | None = None
    security_status: str | None = None
    architecture_status: str | None = None
    continuation_requested: bool = True
    falsify_validations_requested: bool = False
    ignore_runtime_failures_requested: bool = False
    hide_inconsistencies_requested: bool = False
    minimize_risks_requested: bool = False
    approve_corrupt_workflow_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VulcanOperationalValidationResult:
    status: str
    success: bool
    validation_id: str
    subphase_id: str | None
    modified_files: tuple[str, ...]
    validations_executed: tuple[str, ...]
    tests_executed: tuple[str, ...]
    blocking_conditions: tuple[str, ...]
    runtime_valid: bool
    imports_valid: bool
    architecture_valid: bool
    execution_consistent: bool
    governance_compliant: bool
    security_safe: bool
    blocking_conditions_clear: bool
    runtime_integrity_preserved: bool
    architecture_consistency_preserved: bool
    governance_consistency_preserved: bool
    operational_continuity_preserved: bool
    technical_reporting_honest: bool
    continuation_authorized: bool
    continuation_status: str
    report_payload: dict[str, Any] = field(default_factory=dict)
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
            "subphase_id": self.subphase_id,
            "modified_files": list(self.modified_files),
            "validations_executed": list(self.validations_executed),
            "tests_executed": list(self.tests_executed),
            "blocking_conditions": list(self.blocking_conditions),
            "runtime_valid": self.runtime_valid,
            "imports_valid": self.imports_valid,
            "architecture_valid": self.architecture_valid,
            "execution_consistent": self.execution_consistent,
            "governance_compliant": self.governance_compliant,
            "security_safe": self.security_safe,
            "blocking_conditions_clear": self.blocking_conditions_clear,
            "runtime_integrity_preserved": self.runtime_integrity_preserved,
            "architecture_consistency_preserved": (
                self.architecture_consistency_preserved
            ),
            "governance_consistency_preserved": (
                self.governance_consistency_preserved
            ),
            "operational_continuity_preserved": (
                self.operational_continuity_preserved
            ),
            "technical_reporting_honest": self.technical_reporting_honest,
            "continuation_authorized": self.continuation_authorized,
            "continuation_status": self.continuation_status,
            "report_payload": dict(self.report_payload),
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


class VulcanOperationalValidation:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def validate(
        self,
        request: VulcanOperationalValidationRequest,
        validation_permitted: bool = True,
    ) -> VulcanOperationalValidationResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        validation_id = request.validation_id or str(uuid4())

        try:
            prompt_protocol = self._result_dict(request.prompt_protocol)
            scope_enforcement = self._result_dict(request.scope_enforcement)
            execution_handoff = self._result_dict(request.execution_handoff)
            modified_files = tuple(self._values(request.modified_files))
            validations = tuple(self._values(request.validations_executed))
            tests = tuple(self._values(request.tests_executed))
            blocking_conditions = tuple(
                self._values(request.blocking_conditions)
            )
            validation_states = self._validation_states(request)
            reasons = self._validation_reasons(
                request=request,
                prompt_protocol=prompt_protocol,
                scope_enforcement=scope_enforcement,
                execution_handoff=execution_handoff,
                modified_files=modified_files,
                validations=validations,
                tests=tests,
                blocking_conditions=blocking_conditions,
                validation_states=validation_states,
                validation_permitted=validation_permitted,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    VALIDATION_STATUS_BLOCKED
                    if blocked
                    else VALIDATION_STATUS_VALIDATED
                ),
                success=not blocked,
                validation_id=validation_id,
                request=request,
                prompt_protocol=prompt_protocol,
                scope_enforcement=scope_enforcement,
                execution_handoff=execution_handoff,
                modified_files=modified_files,
                validations=validations,
                tests=tests,
                blocking_conditions=blocking_conditions,
                validation_states=validation_states,
                reasons=reasons,
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

    def assess(
        self,
        request: VulcanOperationalValidationRequest,
        validation_permitted: bool = True,
    ) -> VulcanOperationalValidationResult:
        return self.validate(
            request,
            validation_permitted=validation_permitted,
        )

    def _result(
        self,
        status: str,
        success: bool,
        validation_id: str,
        request: VulcanOperationalValidationRequest,
        prompt_protocol: dict[str, Any],
        scope_enforcement: dict[str, Any],
        execution_handoff: dict[str, Any],
        modified_files: tuple[str, ...],
        validations: tuple[str, ...],
        tests: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        validation_states: dict[str, bool],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> VulcanOperationalValidationResult:
        finished_at = datetime.now(timezone.utc)
        runtime_valid = validation_states["runtime"]
        imports_valid = validation_states["imports"]
        architecture_valid = validation_states["architecture"]
        execution_consistent = validation_states["execution"]
        governance_compliant = validation_states["governance"]
        security_safe = validation_states["security"]
        blocking_clear = not self._blocking_active(blocking_conditions)
        honest = not (
            request.falsify_validations_requested
            or request.ignore_runtime_failures_requested
            or request.hide_inconsistencies_requested
            or request.minimize_risks_requested
            or request.approve_corrupt_workflow_requested
        )
        continuation_authorized = success and request.continuation_requested
        return VulcanOperationalValidationResult(
            status=status,
            success=success,
            validation_id=validation_id,
            subphase_id=request.subphase_id,
            modified_files=modified_files,
            validations_executed=validations,
            tests_executed=tests,
            blocking_conditions=blocking_conditions,
            runtime_valid=runtime_valid,
            imports_valid=imports_valid,
            architecture_valid=architecture_valid,
            execution_consistent=execution_consistent,
            governance_compliant=governance_compliant,
            security_safe=security_safe,
            blocking_conditions_clear=blocking_clear,
            runtime_integrity_preserved=runtime_valid,
            architecture_consistency_preserved=architecture_valid,
            governance_consistency_preserved=governance_compliant,
            operational_continuity_preserved=(
                runtime_valid
                and imports_valid
                and execution_consistent
                and security_safe
                and blocking_clear
            ),
            technical_reporting_honest=honest,
            continuation_authorized=continuation_authorized,
            continuation_status=(
                "authorized" if continuation_authorized else "blocked"
            ),
            report_payload=self._report_payload(
                validation_id=validation_id,
                request=request,
                prompt_protocol=prompt_protocol,
                scope_enforcement=scope_enforcement,
                execution_handoff=execution_handoff,
                validation_states=validation_states,
                reasons=reasons,
            ),
            validation_lifecycle=(
                self._lifecycle("validation_preparation"),
                self._lifecycle("technical_validation"),
                self._lifecycle("governance_validation"),
                self._lifecycle(status),
            ),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons),
            error=error,
            metadata=dict(request.metadata),
        )

    def _validation_reasons(
        self,
        request: VulcanOperationalValidationRequest,
        prompt_protocol: dict[str, Any],
        scope_enforcement: dict[str, Any],
        execution_handoff: dict[str, Any],
        modified_files: tuple[str, ...],
        validations: tuple[str, ...],
        tests: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        validation_states: dict[str, bool],
        validation_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not validation_permitted:
            reasons.append("vulcan_operational_validation_not_permitted")
        if prompt_protocol and prompt_protocol.get("status") != "interpreted":
            reasons.append("vulcan_prompt_protocol_not_interpreted")
        if scope_enforcement and scope_enforcement.get("status") != "enforced":
            reasons.append("vulcan_scope_enforcement_not_enforced")
        if execution_handoff and execution_handoff.get("status") != "generated":
            reasons.append("vulcan_execution_handoff_not_generated")
        if not request.subphase_id:
            reasons.append("subphase_id_required")
        if not modified_files:
            reasons.append("modified_files_required")
        if not validations:
            reasons.append("validations_executed_required")
        if not tests:
            reasons.append("tests_executed_required")
        for key, is_valid in validation_states.items():
            if not is_valid:
                reasons.append(f"{key}_validation_failed")
        if self._blocking_active(blocking_conditions):
            reasons.append("blocking_conditions_active")
        if self._normalize(request.runtime_status) in FAILING_STATUSES:
            reasons.append("runtime_status_unsafe")
        if self._normalize(request.governance_status) in FAILING_STATUSES:
            reasons.append("governance_status_blocked")
        if self._normalize(request.security_status) in FAILING_STATUSES:
            reasons.append("security_status_blocked")
        if self._normalize(request.architecture_status) in FAILING_STATUSES:
            reasons.append("architecture_status_unsafe")
        if request.falsify_validations_requested:
            reasons.append("false_validation_blocked")
        if request.ignore_runtime_failures_requested:
            reasons.append("runtime_failure_ignored_blocked")
        if request.hide_inconsistencies_requested:
            reasons.append("inconsistency_concealment_blocked")
        if request.minimize_risks_requested:
            reasons.append("risk_minimization_blocked")
        if request.approve_corrupt_workflow_requested:
            reasons.append("corrupt_workflow_approval_blocked")
        return self._unique(reasons)

    def _validation_states(
        self,
        request: VulcanOperationalValidationRequest,
    ) -> dict[str, bool]:
        return {
            "runtime": self._passed(request.runtime_validation),
            "imports": self._passed(request.import_validation),
            "architecture": self._passed(request.architecture_validation),
            "execution": self._passed(request.execution_validation),
            "governance": self._passed(request.governance_validation),
            "security": self._passed(request.security_validation),
        }

    def _passed(self, value: Any) -> bool:
        normalized = self._validation_value(value)
        if normalized in PASSING_STATUSES:
            return True
        if normalized in FAILING_STATUSES:
            return False
        return False

    def _validation_value(self, value: Any) -> str | None:
        if isinstance(value, bool):
            return "passed" if value else "failed"
        if isinstance(value, dict):
            for key in ("status", "validation_status", "state", "result"):
                if key in value:
                    return self._normalize(value[key])
            return None
        return self._normalize(value)

    def _blocking_active(self, blocking_conditions: tuple[str, ...]) -> bool:
        if not blocking_conditions:
            return False
        return any(
            (self._normalize(condition) or "") not in CLEAR_BLOCKING_CONDITIONS
            for condition in blocking_conditions
        )

    def _report_payload(
        self,
        validation_id: str,
        request: VulcanOperationalValidationRequest,
        prompt_protocol: dict[str, Any],
        scope_enforcement: dict[str, Any],
        execution_handoff: dict[str, Any],
        validation_states: dict[str, bool],
        reasons: list[str],
    ) -> dict[str, Any]:
        return {
            "validation_id": validation_id,
            "subphase_id": request.subphase_id,
            "prompt_protocol_id": prompt_protocol.get("protocol_id"),
            "scope_enforcement_id": scope_enforcement.get("enforcement_id"),
            "handoff_id": execution_handoff.get("handoff_id"),
            "validation_states": dict(validation_states),
            "runtime_status": request.runtime_status,
            "governance_status": request.governance_status,
            "security_status": request.security_status,
            "architecture_status": request.architecture_status,
            "continuation_requested": request.continuation_requested,
            "blocked_reasons": list(reasons),
        }

    def _result_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(
            value,
            (VulcanPromptResult, VulcanScopeResult, VulcanHandoffResult),
        ):
            return value.to_dict()
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

    def _values(self, values: tuple[str, ...]) -> list[str]:
        return self._unique(
            [str(value).strip() for value in values if str(value).strip()]
        )

    def _error_result(
        self,
        validation_id: str,
        request: VulcanOperationalValidationRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> VulcanOperationalValidationResult:
        finished_at = datetime.now(timezone.utc)
        return VulcanOperationalValidationResult(
            status=VALIDATION_STATUS_ERROR,
            success=False,
            validation_id=validation_id,
            subphase_id=request.subphase_id,
            modified_files=tuple(request.modified_files),
            validations_executed=tuple(request.validations_executed),
            tests_executed=tuple(request.tests_executed),
            blocking_conditions=tuple(request.blocking_conditions),
            runtime_valid=False,
            imports_valid=False,
            architecture_valid=False,
            execution_consistent=False,
            governance_compliant=False,
            security_safe=False,
            blocking_conditions_clear=False,
            runtime_integrity_preserved=False,
            architecture_consistency_preserved=False,
            governance_consistency_preserved=False,
            operational_continuity_preserved=False,
            technical_reporting_honest=False,
            continuation_authorized=False,
            continuation_status="blocked",
            report_payload={
                "validation_id": validation_id,
                "blocked_reasons": [
                    "vulcan_operational_validation_error_contained"
                ],
            },
            validation_lifecycle=(self._lifecycle(VALIDATION_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("vulcan_operational_validation_error_contained",),
            error=error,
            metadata=dict(request.metadata),
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

    def _publish(self, result: VulcanOperationalValidationResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_vulcan_operational_validation_result",
        ):
            self.status.mark_vulcan_operational_validation_result(
                result.to_dict()
            )

    def _log_result(self, result: VulcanOperationalValidationResult) -> None:
        if result.status == VALIDATION_STATUS_ERROR:
            logger.error(
                "vulcan_operational_validation: error validation_id=%s error=%s",
                result.validation_id,
                result.error,
            )
            return
        if result.status == VALIDATION_STATUS_BLOCKED:
            logger.warning(
                "vulcan_operational_validation: blocked validation_id=%s reasons=%s",
                result.validation_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "vulcan_operational_validation: validated validation_id=%s subphase=%s",
            result.validation_id,
            result.subphase_id,
        )
