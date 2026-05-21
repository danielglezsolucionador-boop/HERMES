"""
Dependency context builder for Hermes operational workflows.

This layer combines runtime dependencies, roadmap relationships, ecosystem
systems, architecture context, and governance context into a read-only
execution dependency context.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.apps_standards_reader import AppsStandardsReaderResult
from app.runner.knowledge_core_reader import KnowledgeCoreReaderResult
from app.runner.phases_roadmap_reader import PhasesRoadmapReaderResult

logger = logging.getLogger(__name__)

DEPENDENCY_CONTEXT_STATUS_BUILT = "built"
DEPENDENCY_CONTEXT_STATUS_BLOCKED = "blocked"
DEPENDENCY_CONTEXT_STATUS_ERROR = "error"


@dataclass(frozen=True)
class DependencyContextBuilderRequest:
    context_id: str | None = None
    runtime_dependencies: tuple[Any, ...] = field(default_factory=tuple)
    execution_relationships: tuple[Any, ...] = field(default_factory=tuple)
    architecture_context: dict[str, Any] = field(default_factory=dict)
    governance_context: dict[str, Any] = field(default_factory=dict)
    operational_relationships: tuple[Any, ...] = field(default_factory=tuple)
    continuity_status: str | None = None
    knowledge_core: KnowledgeCoreReaderResult | dict[str, Any] | Any | None = None
    phases_roadmap: (
        PhasesRoadmapReaderResult | dict[str, Any] | Any | None
    ) = None
    apps_standards: AppsStandardsReaderResult | dict[str, Any] | Any | None = None
    alter_dependency_structures_requested: bool = False
    break_execution_compatibility_requested: bool = False
    ignore_critical_dependencies_requested: bool = False
    overwrite_architecture_relationships_requested: bool = False
    modify_governance_dependencies_requested: bool = False
    minimize_dependency_impact_requested: bool = False
    hide_runtime_relationships_requested: bool = False
    ignore_execution_conflicts_requested: bool = False
    alter_dependency_history_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DependencyContextBuilderResult:
    status: str
    success: bool
    context_id: str
    runtime_dependencies: tuple[dict[str, Any], ...]
    execution_relationships: tuple[dict[str, Any], ...]
    architecture_context: dict[str, Any]
    governance_context: dict[str, Any]
    operational_relationships: tuple[dict[str, Any], ...]
    execution_compatibility: dict[str, Any]
    continuity_status: str
    dependency_integrity_valid: bool
    runtime_compatibility_valid: bool
    governance_alignment_valid: bool
    architecture_consistency_valid: bool
    operational_continuity_valid: bool
    runtime_integrity_preserved: bool
    architecture_consistency_preserved: bool
    operational_continuity_preserved: bool
    execution_traceability_preserved: bool
    governance_alignment_preserved: bool
    human_visibility_payload: dict[str, Any] = field(default_factory=dict)
    context_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "context_id": self.context_id,
            "runtime_dependencies": [
                dict(item) for item in self.runtime_dependencies
            ],
            "execution_relationships": [
                dict(item) for item in self.execution_relationships
            ],
            "architecture_context": dict(self.architecture_context),
            "governance_context": dict(self.governance_context),
            "operational_relationships": [
                dict(item) for item in self.operational_relationships
            ],
            "execution_compatibility": dict(self.execution_compatibility),
            "continuity_status": self.continuity_status,
            "dependency_integrity_valid": self.dependency_integrity_valid,
            "runtime_compatibility_valid": self.runtime_compatibility_valid,
            "governance_alignment_valid": self.governance_alignment_valid,
            "architecture_consistency_valid": (
                self.architecture_consistency_valid
            ),
            "operational_continuity_valid": (
                self.operational_continuity_valid
            ),
            "runtime_integrity_preserved": self.runtime_integrity_preserved,
            "architecture_consistency_preserved": (
                self.architecture_consistency_preserved
            ),
            "operational_continuity_preserved": (
                self.operational_continuity_preserved
            ),
            "execution_traceability_preserved": (
                self.execution_traceability_preserved
            ),
            "governance_alignment_preserved": (
                self.governance_alignment_preserved
            ),
            "human_visibility_payload": dict(self.human_visibility_payload),
            "context_lifecycle": [
                dict(entry) for entry in self.context_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class DependencyContextBuilder:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def build(
        self,
        request: DependencyContextBuilderRequest,
        building_permitted: bool = True,
    ) -> DependencyContextBuilderResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        context_id = request.context_id or str(uuid4())

        try:
            knowledge_core = self._result_dict(request.knowledge_core)
            phases_roadmap = self._result_dict(request.phases_roadmap)
            apps_standards = self._result_dict(request.apps_standards)
            runtime_dependencies = tuple(
                self._runtime_dependencies(
                    request,
                    knowledge_core,
                    apps_standards,
                )
            )
            execution_relationships = tuple(
                self._execution_relationships(request, phases_roadmap)
            )
            operational_relationships = tuple(
                self._operational_relationships(request, apps_standards)
            )
            architecture_context = self._architecture_context(
                request,
                knowledge_core,
                apps_standards,
            )
            governance_context = self._governance_context(
                request,
                knowledge_core,
                phases_roadmap,
                apps_standards,
            )
            continuity_status = self._continuity_status(
                request,
                phases_roadmap,
            )
            compatibility = self._execution_compatibility(
                runtime_dependencies,
                execution_relationships,
                architecture_context,
                governance_context,
                continuity_status,
            )
            reasons = self._validation_reasons(
                request=request,
                runtime_dependencies=runtime_dependencies,
                execution_relationships=execution_relationships,
                architecture_context=architecture_context,
                governance_context=governance_context,
                operational_relationships=operational_relationships,
                compatibility=compatibility,
                continuity_status=continuity_status,
                building_permitted=building_permitted,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    DEPENDENCY_CONTEXT_STATUS_BLOCKED
                    if blocked
                    else DEPENDENCY_CONTEXT_STATUS_BUILT
                ),
                success=not blocked,
                context_id=context_id,
                request=request,
                runtime_dependencies=runtime_dependencies,
                execution_relationships=execution_relationships,
                architecture_context=architecture_context,
                governance_context=governance_context,
                operational_relationships=operational_relationships,
                compatibility=compatibility,
                continuity_status=continuity_status,
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
                context_id=context_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def construct(
        self,
        request: DependencyContextBuilderRequest,
        building_permitted: bool = True,
    ) -> DependencyContextBuilderResult:
        return self.build(request, building_permitted=building_permitted)

    def _result(
        self,
        status: str,
        success: bool,
        context_id: str,
        request: DependencyContextBuilderRequest,
        runtime_dependencies: tuple[dict[str, Any], ...],
        execution_relationships: tuple[dict[str, Any], ...],
        architecture_context: dict[str, Any],
        governance_context: dict[str, Any],
        operational_relationships: tuple[dict[str, Any], ...],
        compatibility: dict[str, Any],
        continuity_status: str,
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> DependencyContextBuilderResult:
        finished_at = datetime.now(timezone.utc)
        dependency_valid = bool(runtime_dependencies)
        runtime_compatible = bool(compatibility.get("runtime_compatible"))
        governance_valid = bool(governance_context)
        architecture_valid = bool(architecture_context)
        continuity_valid = continuity_status in {"ready", "active", "authorized"}
        return DependencyContextBuilderResult(
            status=status,
            success=success,
            context_id=context_id,
            runtime_dependencies=runtime_dependencies,
            execution_relationships=execution_relationships,
            architecture_context=dict(architecture_context),
            governance_context=dict(governance_context),
            operational_relationships=operational_relationships,
            execution_compatibility=dict(compatibility),
            continuity_status=continuity_status,
            dependency_integrity_valid=dependency_valid,
            runtime_compatibility_valid=runtime_compatible,
            governance_alignment_valid=governance_valid,
            architecture_consistency_valid=architecture_valid,
            operational_continuity_valid=continuity_valid,
            runtime_integrity_preserved=success and dependency_valid,
            architecture_consistency_preserved=success and architecture_valid,
            operational_continuity_preserved=success and continuity_valid,
            execution_traceability_preserved=success
            and bool(execution_relationships),
            governance_alignment_preserved=success and governance_valid,
            human_visibility_payload=self._visibility_payload(
                runtime_dependencies,
                execution_relationships,
                compatibility,
                governance_context,
                architecture_context,
                continuity_status,
            ),
            context_lifecycle=(
                self._lifecycle("dependency_discovery"),
                self._lifecycle("context_analysis"),
                self._lifecycle("context_building"),
                self._lifecycle(status),
            ),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons or ["dependency_context_built"]),
            error=error,
            metadata=dict(request.metadata),
        )

    def _validation_reasons(
        self,
        request: DependencyContextBuilderRequest,
        runtime_dependencies: tuple[dict[str, Any], ...],
        execution_relationships: tuple[dict[str, Any], ...],
        architecture_context: dict[str, Any],
        governance_context: dict[str, Any],
        operational_relationships: tuple[dict[str, Any], ...],
        compatibility: dict[str, Any],
        continuity_status: str,
        building_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not building_permitted:
            reasons.append("dependency_context_building_not_permitted")
        if not runtime_dependencies:
            reasons.append("runtime_dependencies_required")
        if not execution_relationships:
            reasons.append("execution_relationships_required")
        if not architecture_context:
            reasons.append("architecture_context_required")
        if not governance_context:
            reasons.append("governance_context_required")
        if not operational_relationships:
            reasons.append("operational_relationships_required")
        if not compatibility.get("runtime_compatible"):
            reasons.append("runtime_compatibility_required")
        if continuity_status not in {"ready", "active", "authorized"}:
            reasons.append("operational_continuity_blocked")
        if request.alter_dependency_structures_requested:
            reasons.append("dependency_structure_alteration_blocked")
        if request.break_execution_compatibility_requested:
            reasons.append("execution_compatibility_break_blocked")
        if request.ignore_critical_dependencies_requested:
            reasons.append("critical_dependency_ignore_blocked")
        if request.overwrite_architecture_relationships_requested:
            reasons.append("architecture_dependency_overwrite_blocked")
        if request.modify_governance_dependencies_requested:
            reasons.append("governance_dependency_modification_blocked")
        if request.minimize_dependency_impact_requested:
            reasons.append("dependency_impact_minimization_blocked")
        if request.hide_runtime_relationships_requested:
            reasons.append("runtime_relationship_concealment_blocked")
        if request.ignore_execution_conflicts_requested:
            reasons.append("execution_conflict_ignore_blocked")
        if request.alter_dependency_history_requested:
            reasons.append("dependency_history_alteration_blocked")
        return self._unique(reasons)

    def _runtime_dependencies(
        self,
        request: DependencyContextBuilderRequest,
        knowledge_core: dict[str, Any],
        apps_standards: dict[str, Any],
    ) -> list[dict[str, Any]]:
        dependencies = [self._record(item) for item in request.runtime_dependencies]
        for source in (knowledge_core.get("dependency_context") or {}).get("sources") or []:
            dependencies.append({"name": str(source), "source": "knowledge_core"})
        for system in apps_standards.get("systems_detected") or []:
            if isinstance(system, dict):
                dependencies.append(
                    {
                        "name": str(system.get("name") or system.get("source")),
                        "source": "apps_standards",
                    }
                )
        return self._unique_records(dependencies, "name")

    def _execution_relationships(
        self,
        request: DependencyContextBuilderRequest,
        phases_roadmap: dict[str, Any],
    ) -> list[dict[str, Any]]:
        relationships = [
            self._record(item) for item in request.execution_relationships
        ]
        for item in phases_roadmap.get("dependency_relationships") or []:
            if isinstance(item, dict):
                relationships.append(dict(item))
        return self._unique_records(relationships, "subphase")

    def _operational_relationships(
        self,
        request: DependencyContextBuilderRequest,
        apps_standards: dict[str, Any],
    ) -> list[dict[str, Any]]:
        relationships = [
            self._record(item) for item in request.operational_relationships
        ]
        for system in apps_standards.get("systems_detected") or []:
            if isinstance(system, dict):
                relationships.append(
                    {
                        "name": str(system.get("name") or system.get("source")),
                        "relationship": "ecosystem_system",
                    }
                )
        return self._unique_records(relationships, "name")

    def _architecture_context(
        self,
        request: DependencyContextBuilderRequest,
        knowledge_core: dict[str, Any],
        apps_standards: dict[str, Any],
    ) -> dict[str, Any]:
        context = dict(request.architecture_context)
        if not context:
            context.update(knowledge_core.get("execution_context") or {})
        rules = apps_standards.get("architecture_rules") or []
        if rules:
            context["architecture_rules"] = list(rules)
        return context

    def _governance_context(
        self,
        request: DependencyContextBuilderRequest,
        knowledge_core: dict[str, Any],
        phases_roadmap: dict[str, Any],
        apps_standards: dict[str, Any],
    ) -> dict[str, Any]:
        context = dict(request.governance_context)
        for source in (
            knowledge_core.get("governance_context"),
            phases_roadmap.get("governance_context"),
            apps_standards.get("governance_context"),
        ):
            if isinstance(source, dict):
                context.update(source)
        return context

    def _continuity_status(
        self,
        request: DependencyContextBuilderRequest,
        phases_roadmap: dict[str, Any],
    ) -> str:
        return (
            request.continuity_status
            or phases_roadmap.get("continuation_status")
            or "blocked"
        )

    def _execution_compatibility(
        self,
        runtime_dependencies: tuple[dict[str, Any], ...],
        execution_relationships: tuple[dict[str, Any], ...],
        architecture_context: dict[str, Any],
        governance_context: dict[str, Any],
        continuity_status: str,
    ) -> dict[str, Any]:
        compatible = bool(
            runtime_dependencies
            and execution_relationships
            and architecture_context
            and governance_context
            and continuity_status in {"ready", "active", "authorized"}
        )
        return {
            "runtime_compatible": compatible,
            "dependency_count": len(runtime_dependencies),
            "relationship_count": len(execution_relationships),
            "continuity_status": continuity_status,
        }

    def _visibility_payload(
        self,
        runtime_dependencies: tuple[dict[str, Any], ...],
        execution_relationships: tuple[dict[str, Any], ...],
        compatibility: dict[str, Any],
        governance_context: dict[str, Any],
        architecture_context: dict[str, Any],
        continuity_status: str,
    ) -> dict[str, Any]:
        return {
            "dependencies_detected": [dict(item) for item in runtime_dependencies],
            "execution_relationships": [
                dict(item) for item in execution_relationships
            ],
            "runtime_compatibility": dict(compatibility),
            "governance_alignment": dict(governance_context),
            "architecture_consistency": dict(architecture_context),
            "operational_continuity": continuity_status,
        }

    def _record(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        return {"name": str(value)}

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
        context_id: str,
        request: DependencyContextBuilderRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> DependencyContextBuilderResult:
        finished_at = datetime.now(timezone.utc)
        return DependencyContextBuilderResult(
            status=DEPENDENCY_CONTEXT_STATUS_ERROR,
            success=False,
            context_id=context_id,
            runtime_dependencies=(),
            execution_relationships=(),
            architecture_context=dict(request.architecture_context),
            governance_context=dict(request.governance_context),
            operational_relationships=(),
            execution_compatibility={},
            continuity_status=request.continuity_status or "blocked",
            dependency_integrity_valid=False,
            runtime_compatibility_valid=False,
            governance_alignment_valid=False,
            architecture_consistency_valid=False,
            operational_continuity_valid=False,
            runtime_integrity_preserved=False,
            architecture_consistency_preserved=False,
            operational_continuity_preserved=False,
            execution_traceability_preserved=False,
            governance_alignment_preserved=False,
            human_visibility_payload={},
            context_lifecycle=(self._lifecycle(DEPENDENCY_CONTEXT_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("dependency_context_builder_error_contained",),
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

    def _unique_records(
        self,
        values: list[dict[str, Any]],
        key: str,
    ) -> list[dict[str, Any]]:
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for value in values:
            marker = str(value.get(key) or value)
            if marker not in seen:
                seen.add(marker)
                unique.append(value)
        return unique

    def _publish(self, result: DependencyContextBuilderResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_dependency_context_builder_result",
        ):
            self.status.mark_dependency_context_builder_result(result.to_dict())

    def _log_result(self, result: DependencyContextBuilderResult) -> None:
        if result.status == DEPENDENCY_CONTEXT_STATUS_ERROR:
            logger.error(
                "dependency_context_builder: error context_id=%s error=%s",
                result.context_id,
                result.error,
            )
            return
        if result.status == DEPENDENCY_CONTEXT_STATUS_BLOCKED:
            logger.warning(
                "dependency_context_builder: blocked context_id=%s reasons=%s",
                result.context_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "dependency_context_builder: built context_id=%s dependencies=%s",
            result.context_id,
            len(result.runtime_dependencies),
        )
