"""
Vulcan execution handoff for controlled Hermes backend workflows.

This layer structures honest technical handoffs after execution. It records
what changed, what was validated, known risks, blocking conditions, and final
operational state without altering runtime behavior.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.vulcan_prompt_protocol import VulcanPromptResult
from app.runner.vulcan_scope_enforcement import VulcanScopeResult

logger = logging.getLogger(__name__)

HANDOFF_STATUS_GENERATED = "generated"
HANDOFF_STATUS_BLOCKED = "blocked"
HANDOFF_STATUS_ERROR = "error"


@dataclass(frozen=True)
class VulcanHandoffRequest:
    handoff_id: str | None = None
    subphase_id: str | None = None
    execution_objective: str | None = None
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    implementation_summary: tuple[str, ...] = field(default_factory=tuple)
    validations_executed: tuple[str, ...] = field(default_factory=tuple)
    tests_executed: tuple[str, ...] = field(default_factory=tuple)
    risks_detected: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    not_implemented: tuple[str, ...] = field(default_factory=tuple)
    operational_status: str | None = None
    governance_status: str | None = None
    execution_continuity: str | None = None
    prompt_protocol: VulcanPromptResult | dict[str, Any] | Any | None = None
    scope_enforcement: VulcanScopeResult | dict[str, Any] | Any | None = None
    runtime_modifications: tuple[str, ...] = field(default_factory=tuple)
    validation_status: str | None = None
    conceal_errors_requested: bool = False
    minimize_runtime_risks_requested: bool = False
    falsify_validations_requested: bool = False
    invent_execution_status_requested: bool = False
    alter_runtime_reporting_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VulcanHandoffResult:
    status: str
    success: bool
    handoff_id: str
    subphase_id: str | None
    execution_objective: str | None
    modified_files: tuple[str, ...]
    implementation_summary: tuple[str, ...]
    validations_executed: tuple[str, ...]
    tests_executed: tuple[str, ...]
    risks_detected: tuple[str, ...]
    blocking_conditions: tuple[str, ...]
    not_implemented: tuple[str, ...]
    operational_status: str | None
    governance_status: str | None
    execution_continuity: str | None
    traceability_preserved: bool
    runtime_reporting_preserved: bool
    governance_consistency_preserved: bool
    validations_honest: bool
    risks_reported: bool
    blocking_conditions_reported: bool
    handoff_complete: bool
    handoff_text: str
    report_payload: dict[str, Any] = field(default_factory=dict)
    handoff_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "handoff_id": self.handoff_id,
            "subphase_id": self.subphase_id,
            "execution_objective": self.execution_objective,
            "modified_files": list(self.modified_files),
            "implementation_summary": list(self.implementation_summary),
            "validations_executed": list(self.validations_executed),
            "tests_executed": list(self.tests_executed),
            "risks_detected": list(self.risks_detected),
            "blocking_conditions": list(self.blocking_conditions),
            "not_implemented": list(self.not_implemented),
            "operational_status": self.operational_status,
            "governance_status": self.governance_status,
            "execution_continuity": self.execution_continuity,
            "traceability_preserved": self.traceability_preserved,
            "runtime_reporting_preserved": self.runtime_reporting_preserved,
            "governance_consistency_preserved": (
                self.governance_consistency_preserved
            ),
            "validations_honest": self.validations_honest,
            "risks_reported": self.risks_reported,
            "blocking_conditions_reported": (
                self.blocking_conditions_reported
            ),
            "handoff_complete": self.handoff_complete,
            "handoff_text": self.handoff_text,
            "report_payload": dict(self.report_payload),
            "handoff_lifecycle": [
                dict(entry) for entry in self.handoff_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class VulcanExecutionHandoff:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def generate(
        self,
        request: VulcanHandoffRequest,
        handoff_permitted: bool = True,
    ) -> VulcanHandoffResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        handoff_id = request.handoff_id or str(uuid4())

        try:
            prompt_protocol = self._result_dict(request.prompt_protocol)
            scope_enforcement = self._result_dict(request.scope_enforcement)
            modified_files = tuple(self._values(request.modified_files))
            implementation_summary = tuple(
                self._values(request.implementation_summary)
            )
            validations = tuple(self._values(request.validations_executed))
            tests = tuple(self._values(request.tests_executed))
            risks = tuple(self._values(request.risks_detected))
            blocking_conditions = tuple(
                self._values(request.blocking_conditions)
            )
            not_implemented = tuple(self._values(request.not_implemented))
            reasons = self._validation_reasons(
                request=request,
                prompt_protocol=prompt_protocol,
                scope_enforcement=scope_enforcement,
                modified_files=modified_files,
                implementation_summary=implementation_summary,
                validations=validations,
                tests=tests,
                risks=risks,
                blocking_conditions=blocking_conditions,
                handoff_permitted=handoff_permitted,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    HANDOFF_STATUS_BLOCKED
                    if blocked
                    else HANDOFF_STATUS_GENERATED
                ),
                success=not blocked,
                handoff_id=handoff_id,
                request=request,
                prompt_protocol=prompt_protocol,
                scope_enforcement=scope_enforcement,
                modified_files=modified_files,
                implementation_summary=implementation_summary,
                validations=validations,
                tests=tests,
                risks=risks,
                blocking_conditions=blocking_conditions,
                not_implemented=not_implemented,
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
                handoff_id=handoff_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def report(
        self,
        request: VulcanHandoffRequest,
        handoff_permitted: bool = True,
    ) -> VulcanHandoffResult:
        return self.generate(
            request,
            handoff_permitted=handoff_permitted,
        )

    def _result(
        self,
        status: str,
        success: bool,
        handoff_id: str,
        request: VulcanHandoffRequest,
        prompt_protocol: dict[str, Any],
        scope_enforcement: dict[str, Any],
        modified_files: tuple[str, ...],
        implementation_summary: tuple[str, ...],
        validations: tuple[str, ...],
        tests: tuple[str, ...],
        risks: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        not_implemented: tuple[str, ...],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> VulcanHandoffResult:
        finished_at = datetime.now(timezone.utc)
        traceability_preserved = bool(
            request.subphase_id and request.execution_objective and modified_files
        )
        runtime_reporting_preserved = not (
            request.alter_runtime_reporting_requested
            or request.invent_execution_status_requested
        )
        governance_consistency_preserved = (
            self._normalize(request.governance_status)
            not in {"unknown", "falsified", "ignored"}
        )
        validations_honest = not request.falsify_validations_requested
        risks_reported = bool(risks) and not request.minimize_runtime_risks_requested
        blocking_reported = bool(blocking_conditions)
        handoff_text = self._handoff_text(
            request=request,
            modified_files=modified_files,
            implementation_summary=implementation_summary,
            validations=validations,
            tests=tests,
            risks=risks,
            blocking_conditions=blocking_conditions,
            not_implemented=not_implemented,
        )
        return VulcanHandoffResult(
            status=status,
            success=success,
            handoff_id=handoff_id,
            subphase_id=request.subphase_id,
            execution_objective=request.execution_objective,
            modified_files=modified_files,
            implementation_summary=implementation_summary,
            validations_executed=validations,
            tests_executed=tests,
            risks_detected=risks,
            blocking_conditions=blocking_conditions,
            not_implemented=not_implemented,
            operational_status=request.operational_status,
            governance_status=request.governance_status,
            execution_continuity=request.execution_continuity,
            traceability_preserved=traceability_preserved,
            runtime_reporting_preserved=runtime_reporting_preserved,
            governance_consistency_preserved=governance_consistency_preserved,
            validations_honest=validations_honest,
            risks_reported=risks_reported,
            blocking_conditions_reported=blocking_reported,
            handoff_complete=success,
            handoff_text=handoff_text,
            report_payload=self._report_payload(
                handoff_id=handoff_id,
                request=request,
                prompt_protocol=prompt_protocol,
                scope_enforcement=scope_enforcement,
                modified_files=modified_files,
                validations=validations,
                tests=tests,
                risks=risks,
                blocking_conditions=blocking_conditions,
                reasons=reasons,
            ),
            handoff_lifecycle=(
                self._lifecycle("handoff_components_collected"),
                self._lifecycle("handoff_validation_completed"),
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
        request: VulcanHandoffRequest,
        prompt_protocol: dict[str, Any],
        scope_enforcement: dict[str, Any],
        modified_files: tuple[str, ...],
        implementation_summary: tuple[str, ...],
        validations: tuple[str, ...],
        tests: tuple[str, ...],
        risks: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        handoff_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not handoff_permitted:
            reasons.append("vulcan_handoff_not_permitted")
        if prompt_protocol and prompt_protocol.get("status") != "interpreted":
            reasons.append("vulcan_prompt_protocol_not_interpreted")
        if scope_enforcement and scope_enforcement.get("status") != "enforced":
            reasons.append("vulcan_scope_enforcement_not_enforced")
        if not request.subphase_id:
            reasons.append("subphase_id_required")
        if not request.execution_objective:
            reasons.append("execution_objective_required")
        if not modified_files:
            reasons.append("modified_files_required")
        if not implementation_summary:
            reasons.append("implementation_summary_required")
        if not validations:
            reasons.append("validations_executed_required")
        if not tests:
            reasons.append("tests_executed_required")
        if not risks:
            reasons.append("risks_detected_required")
        if not blocking_conditions:
            reasons.append("blocking_conditions_required")
        if not request.operational_status:
            reasons.append("operational_status_required")
        if not request.governance_status:
            reasons.append("governance_status_required")
        if not request.execution_continuity:
            reasons.append("execution_continuity_required")
        if request.conceal_errors_requested:
            reasons.append("error_concealment_blocked")
        if request.minimize_runtime_risks_requested:
            reasons.append("risk_minimization_blocked")
        if request.falsify_validations_requested:
            reasons.append("validation_falsification_blocked")
        if request.invent_execution_status_requested:
            reasons.append("invented_execution_status_blocked")
        if request.alter_runtime_reporting_requested:
            reasons.append("runtime_reporting_alteration_blocked")
        if self._normalize(request.validation_status) in {"failed", "falsified"}:
            reasons.append("validation_status_blocks_handoff")
        return self._unique(reasons)

    def _handoff_text(
        self,
        request: VulcanHandoffRequest,
        modified_files: tuple[str, ...],
        implementation_summary: tuple[str, ...],
        validations: tuple[str, ...],
        tests: tuple[str, ...],
        risks: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        not_implemented: tuple[str, ...],
    ) -> str:
        return "\n".join(
            [
                f"SUBFASE: {request.subphase_id or ''}",
                f"OBJETIVO: {request.execution_objective or ''}",
                "ARCHIVOS TOCADOS:",
                *self._bullets(modified_files),
                "SE IMPLEMENTO:",
                *self._bullets(implementation_summary),
                "VALIDACIONES:",
                *self._bullets(validations),
                "TESTS:",
                *self._bullets(tests),
                "RIESGOS:",
                *self._bullets(risks),
                "BLOCKING CONDITIONS:",
                *self._bullets(blocking_conditions),
                "QUE NO SE IMPLEMENTO:",
                *self._bullets(not_implemented or ("none",)),
                f"ESTADO OPERACIONAL: {request.operational_status or ''}",
                f"GOVERNANCE STATUS: {request.governance_status or ''}",
                f"CONTINUIDAD: {request.execution_continuity or ''}",
            ]
        )

    def _report_payload(
        self,
        handoff_id: str,
        request: VulcanHandoffRequest,
        prompt_protocol: dict[str, Any],
        scope_enforcement: dict[str, Any],
        modified_files: tuple[str, ...],
        validations: tuple[str, ...],
        tests: tuple[str, ...],
        risks: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        reasons: list[str],
    ) -> dict[str, Any]:
        return {
            "handoff_id": handoff_id,
            "subphase_id": request.subphase_id,
            "execution_objective": request.execution_objective,
            "prompt_protocol_id": prompt_protocol.get("protocol_id"),
            "scope_enforcement_id": scope_enforcement.get("enforcement_id"),
            "modified_files": list(modified_files),
            "runtime_modifications": list(request.runtime_modifications),
            "validations_executed": list(validations),
            "tests_executed": list(tests),
            "risks_detected": list(risks),
            "blocking_conditions": list(blocking_conditions),
            "operational_status": request.operational_status,
            "governance_status": request.governance_status,
            "execution_continuity": request.execution_continuity,
            "blocked_reasons": list(reasons),
        }

    def _result_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, (VulcanPromptResult, VulcanScopeResult)):
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

    def _bullets(self, values: tuple[str, ...]) -> list[str]:
        return [f"- {value}" for value in values]

    def _error_result(
        self,
        handoff_id: str,
        request: VulcanHandoffRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> VulcanHandoffResult:
        finished_at = datetime.now(timezone.utc)
        return VulcanHandoffResult(
            status=HANDOFF_STATUS_ERROR,
            success=False,
            handoff_id=handoff_id,
            subphase_id=request.subphase_id,
            execution_objective=request.execution_objective,
            modified_files=tuple(request.modified_files),
            implementation_summary=tuple(request.implementation_summary),
            validations_executed=tuple(request.validations_executed),
            tests_executed=tuple(request.tests_executed),
            risks_detected=tuple(request.risks_detected),
            blocking_conditions=tuple(request.blocking_conditions),
            not_implemented=tuple(request.not_implemented),
            operational_status=request.operational_status,
            governance_status=request.governance_status,
            execution_continuity=request.execution_continuity,
            traceability_preserved=False,
            runtime_reporting_preserved=False,
            governance_consistency_preserved=False,
            validations_honest=False,
            risks_reported=False,
            blocking_conditions_reported=False,
            handoff_complete=False,
            handoff_text="",
            report_payload={
                "handoff_id": handoff_id,
                "blocked_reasons": ["vulcan_execution_handoff_error_contained"],
            },
            handoff_lifecycle=(self._lifecycle(HANDOFF_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("vulcan_execution_handoff_error_contained",),
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

    def _publish(self, result: VulcanHandoffResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_vulcan_execution_handoff_result",
        ):
            self.status.mark_vulcan_execution_handoff_result(result.to_dict())

    def _log_result(self, result: VulcanHandoffResult) -> None:
        if result.status == HANDOFF_STATUS_ERROR:
            logger.error(
                "vulcan_execution_handoff: error handoff_id=%s error=%s",
                result.handoff_id,
                result.error,
            )
            return
        if result.status == HANDOFF_STATUS_BLOCKED:
            logger.warning(
                "vulcan_execution_handoff: blocked handoff_id=%s reasons=%s",
                result.handoff_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "vulcan_execution_handoff: generated handoff_id=%s subphase=%s",
            result.handoff_id,
            result.subphase_id,
        )
