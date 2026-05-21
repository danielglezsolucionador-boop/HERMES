"""
Knowledge Core validation for Hermes operational workflows.

This layer validates roadmap, phases, standards, dependencies, governance, and
execution continuity before operational context is used. It does not alter
official roadmap, standards, governance, or dependency structures.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.apps_standards_reader import AppsStandardsReaderResult
from app.runner.dependency_context_builder import DependencyContextBuilderResult
from app.runner.knowledge_core_reader import KnowledgeCoreReaderResult
from app.runner.phases_roadmap_reader import PhasesRoadmapReaderResult

logger = logging.getLogger(__name__)

KNOWLEDGE_VALIDATION_STATUS_VALIDATED = "validated"
KNOWLEDGE_VALIDATION_STATUS_BLOCKED = "blocked"
KNOWLEDGE_VALIDATION_STATUS_ERROR = "error"


@dataclass(frozen=True)
class KnowledgeCoreValidationRequest:
    validation_id: str | None = None
    knowledge_core: KnowledgeCoreReaderResult | dict[str, Any] | Any | None = None
    phases_roadmap: (
        PhasesRoadmapReaderResult | dict[str, Any] | Any | None
    ) = None
    apps_standards: AppsStandardsReaderResult | dict[str, Any] | Any | None = None
    dependency_context: (
        DependencyContextBuilderResult | dict[str, Any] | Any | None
    ) = None
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    detected_inconsistencies: tuple[str, ...] = field(default_factory=tuple)
    use_corrupt_context_requested: bool = False
    ignore_roadmap_inconsistencies_requested: bool = False
    alter_governance_context_requested: bool = False
    overwrite_standards_requested: bool = False
    approve_invalid_dependencies_requested: bool = False
    hide_inconsistencies_requested: bool = False
    minimize_dependency_conflicts_requested: bool = False
    ignore_governance_issues_requested: bool = False
    alter_execution_history_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeCoreValidationResult:
    status: str
    success: bool
    validation_id: str
    roadmap_valid: bool
    phase_valid: bool
    standards_valid: bool
    dependency_valid: bool
    governance_valid: bool
    execution_continuity_valid: bool
    architecture_consistency_preserved: bool
    operational_continuity_preserved: bool
    execution_consistency_preserved: bool
    context_approved: bool
    blocking_conditions: tuple[str, ...]
    detected_inconsistencies: tuple[str, ...]
    validation_report: dict[str, Any] = field(default_factory=dict)
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
            "roadmap_valid": self.roadmap_valid,
            "phase_valid": self.phase_valid,
            "standards_valid": self.standards_valid,
            "dependency_valid": self.dependency_valid,
            "governance_valid": self.governance_valid,
            "execution_continuity_valid": self.execution_continuity_valid,
            "architecture_consistency_preserved": (
                self.architecture_consistency_preserved
            ),
            "operational_continuity_preserved": (
                self.operational_continuity_preserved
            ),
            "execution_consistency_preserved": (
                self.execution_consistency_preserved
            ),
            "context_approved": self.context_approved,
            "blocking_conditions": list(self.blocking_conditions),
            "detected_inconsistencies": list(self.detected_inconsistencies),
            "validation_report": dict(self.validation_report),
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


class KnowledgeCoreValidation:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def validate(
        self,
        request: KnowledgeCoreValidationRequest,
        validation_permitted: bool = True,
    ) -> KnowledgeCoreValidationResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        validation_id = request.validation_id or str(uuid4())

        try:
            knowledge_core = self._result_dict(request.knowledge_core)
            phases_roadmap = self._result_dict(request.phases_roadmap)
            apps_standards = self._result_dict(request.apps_standards)
            dependency_context = self._result_dict(request.dependency_context)
            checks = self._checks(
                knowledge_core,
                phases_roadmap,
                apps_standards,
                dependency_context,
            )
            inconsistencies = tuple(
                self._inconsistencies(request, checks)
            )
            blocking_conditions = tuple(
                self._blocking_conditions(request, inconsistencies)
            )
            reasons = self._validation_reasons(
                request=request,
                checks=checks,
                inconsistencies=inconsistencies,
                blocking_conditions=blocking_conditions,
                validation_permitted=validation_permitted,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    KNOWLEDGE_VALIDATION_STATUS_BLOCKED
                    if blocked
                    else KNOWLEDGE_VALIDATION_STATUS_VALIDATED
                ),
                success=not blocked,
                validation_id=validation_id,
                request=request,
                checks=checks,
                inconsistencies=inconsistencies,
                blocking_conditions=blocking_conditions,
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

    def inspect(
        self,
        request: KnowledgeCoreValidationRequest,
        validation_permitted: bool = True,
    ) -> KnowledgeCoreValidationResult:
        return self.validate(
            request,
            validation_permitted=validation_permitted,
        )

    def _result(
        self,
        status: str,
        success: bool,
        validation_id: str,
        request: KnowledgeCoreValidationRequest,
        checks: dict[str, bool],
        inconsistencies: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> KnowledgeCoreValidationResult:
        finished_at = datetime.now(timezone.utc)
        context_approved = success and all(checks.values()) and not blocking_conditions
        return KnowledgeCoreValidationResult(
            status=status,
            success=success,
            validation_id=validation_id,
            roadmap_valid=checks["roadmap"],
            phase_valid=checks["phase"],
            standards_valid=checks["standards"],
            dependency_valid=checks["dependency"],
            governance_valid=checks["governance"],
            execution_continuity_valid=checks["execution_continuity"],
            architecture_consistency_preserved=success and checks["standards"],
            operational_continuity_preserved=success
            and checks["execution_continuity"],
            execution_consistency_preserved=success and checks["phase"],
            context_approved=context_approved,
            blocking_conditions=blocking_conditions,
            detected_inconsistencies=inconsistencies,
            validation_report=self._report(checks, inconsistencies, blocking_conditions),
            validation_lifecycle=(
                self._lifecycle("knowledge_analysis"),
                self._lifecycle("context_validation"),
                self._lifecycle("inconsistency_detection"),
                self._lifecycle(status),
            ),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons or ["knowledge_core_context_validated"]),
            error=error,
            metadata=dict(request.metadata),
        )

    def _checks(
        self,
        knowledge_core: dict[str, Any],
        phases_roadmap: dict[str, Any],
        apps_standards: dict[str, Any],
        dependency_context: dict[str, Any],
    ) -> dict[str, bool]:
        return {
            "roadmap": bool(
                knowledge_core.get("roadmap_consistency_valid")
                and phases_roadmap.get("roadmap_coherence_preserved")
            ),
            "phase": bool(phases_roadmap.get("phase_consistency_valid")),
            "standards": bool(
                apps_standards.get("standards_legitimacy_valid")
                and apps_standards.get("architecture_compatibility_valid")
            ),
            "dependency": bool(
                dependency_context.get("dependency_integrity_valid")
                and dependency_context.get("runtime_compatibility_valid")
            ),
            "governance": bool(
                knowledge_core.get("governance_alignment_valid")
                and phases_roadmap.get("governance_alignment_valid")
                and apps_standards.get("governance_alignment_valid")
                and dependency_context.get("governance_alignment_valid")
            ),
            "execution_continuity": bool(
                dependency_context.get("operational_continuity_valid")
                and phases_roadmap.get("execution_continuity_valid")
            ),
        }

    def _inconsistencies(
        self,
        request: KnowledgeCoreValidationRequest,
        checks: dict[str, bool],
    ) -> list[str]:
        inconsistencies = [str(item) for item in request.detected_inconsistencies]
        for name, valid in checks.items():
            if not valid:
                inconsistencies.append(f"{name}_validation_failed")
        return self._unique(inconsistencies)

    def _blocking_conditions(
        self,
        request: KnowledgeCoreValidationRequest,
        inconsistencies: tuple[str, ...],
    ) -> list[str]:
        blocking = [str(item) for item in request.blocking_conditions]
        blocking.extend(inconsistencies)
        return self._unique([item for item in blocking if item])

    def _validation_reasons(
        self,
        request: KnowledgeCoreValidationRequest,
        checks: dict[str, bool],
        inconsistencies: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        validation_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not validation_permitted:
            reasons.append("knowledge_core_validation_not_permitted")
        for name, valid in checks.items():
            if not valid:
                reasons.append(f"{name}_invalid")
        if blocking_conditions:
            reasons.append("knowledge_blocking_conditions_active")
        if request.use_corrupt_context_requested:
            reasons.append("corrupt_context_usage_blocked")
        if request.ignore_roadmap_inconsistencies_requested:
            reasons.append("roadmap_inconsistency_ignore_blocked")
        if request.alter_governance_context_requested:
            reasons.append("governance_context_alteration_blocked")
        if request.overwrite_standards_requested:
            reasons.append("standards_overwrite_blocked")
        if request.approve_invalid_dependencies_requested:
            reasons.append("invalid_dependency_approval_blocked")
        if request.hide_inconsistencies_requested and inconsistencies:
            reasons.append("knowledge_inconsistency_concealment_blocked")
        if request.minimize_dependency_conflicts_requested:
            reasons.append("dependency_conflict_minimization_blocked")
        if request.ignore_governance_issues_requested:
            reasons.append("governance_issue_ignore_blocked")
        if request.alter_execution_history_requested:
            reasons.append("execution_history_alteration_blocked")
        return self._unique(reasons)

    def _report(
        self,
        checks: dict[str, bool],
        inconsistencies: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "validations_executed": list(checks.keys()),
            "checks": dict(checks),
            "inconsistencies_detected": list(inconsistencies),
            "blocking_conditions": list(blocking_conditions),
            "context_approval_status": (
                "approved"
                if all(checks.values()) and not blocking_conditions
                else "blocked"
            ),
        }

    def _result_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(
            value,
            (
                KnowledgeCoreReaderResult,
                PhasesRoadmapReaderResult,
                AppsStandardsReaderResult,
                DependencyContextBuilderResult,
            ),
        ):
            return value.to_dict()
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

    def _error_result(
        self,
        validation_id: str,
        request: KnowledgeCoreValidationRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> KnowledgeCoreValidationResult:
        finished_at = datetime.now(timezone.utc)
        return KnowledgeCoreValidationResult(
            status=KNOWLEDGE_VALIDATION_STATUS_ERROR,
            success=False,
            validation_id=validation_id,
            roadmap_valid=False,
            phase_valid=False,
            standards_valid=False,
            dependency_valid=False,
            governance_valid=False,
            execution_continuity_valid=False,
            architecture_consistency_preserved=False,
            operational_continuity_preserved=False,
            execution_consistency_preserved=False,
            context_approved=False,
            blocking_conditions=tuple(request.blocking_conditions),
            detected_inconsistencies=tuple(request.detected_inconsistencies),
            validation_report={
                "context_approval_status": "error",
                "blocking_conditions": [
                    "knowledge_core_validation_error_contained"
                ],
            },
            validation_lifecycle=(self._lifecycle(KNOWLEDGE_VALIDATION_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("knowledge_core_validation_error_contained",),
            error=error,
            metadata=dict(request.metadata),
        )

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

    def _publish(self, result: KnowledgeCoreValidationResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_knowledge_core_validation_result",
        ):
            self.status.mark_knowledge_core_validation_result(result.to_dict())

    def _log_result(self, result: KnowledgeCoreValidationResult) -> None:
        if result.status == KNOWLEDGE_VALIDATION_STATUS_ERROR:
            logger.error(
                "knowledge_core_validation: error validation_id=%s error=%s",
                result.validation_id,
                result.error,
            )
            return
        if result.status == KNOWLEDGE_VALIDATION_STATUS_BLOCKED:
            logger.warning(
                "knowledge_core_validation: blocked validation_id=%s reasons=%s",
                result.validation_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "knowledge_core_validation: validated validation_id=%s approved=%s",
            result.validation_id,
            result.context_approved,
        )
