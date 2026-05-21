"""
Read-only phases and roadmap reader for Hermes operational workflows.

This layer interprets authorized phase documentation into execution order,
subphase context, dependencies, and continuity status without modifying the
official roadmap or inventing subphases.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.runner.knowledge_core_reader import KnowledgeCoreReaderResult

logger = logging.getLogger(__name__)

ROADMAP_STATUS_INTERPRETED = "interpreted"
ROADMAP_STATUS_BLOCKED = "blocked"
ROADMAP_STATUS_ERROR = "error"

PHASE_FILE_PATTERN = re.compile(r"^(?P<order>\d+(?:\.\d+)*)(?:[_-].*)?\.md$")


@dataclass(frozen=True)
class PhasesRoadmapReaderRequest:
    roadmap_id: str | None = None
    roadmap_sources: tuple[str, ...] = field(default_factory=tuple)
    source_authorizations: dict[str, bool] = field(default_factory=dict)
    allowed_extensions: tuple[str, ...] = (".md",)
    max_files: int = 300
    current_subphase: str | None = None
    completed_subphases: tuple[str, ...] = field(default_factory=tuple)
    knowledge_core: KnowledgeCoreReaderResult | dict[str, Any] | Any | None = None
    governance_context: dict[str, Any] = field(default_factory=dict)
    modify_roadmap_requested: bool = False
    invent_subphase_requested: bool = False
    alter_priorities_requested: bool = False
    ignore_dependencies_requested: bool = False
    overwrite_governance_planning_requested: bool = False
    hide_blocking_conditions_requested: bool = False
    minimize_governance_conflicts_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PhasesRoadmapReaderResult:
    status: str
    success: bool
    roadmap_id: str
    roadmap_sources: tuple[str, ...]
    phase_structure: tuple[dict[str, Any], ...]
    subphase_structure: tuple[str, ...]
    execution_order: tuple[str, ...]
    priority_context: dict[str, Any]
    dependency_relationships: tuple[dict[str, Any], ...]
    governance_context: dict[str, Any]
    continuation_status: str
    roadmap_legitimacy_valid: bool
    phase_consistency_valid: bool
    dependency_integrity_valid: bool
    governance_alignment_valid: bool
    execution_continuity_valid: bool
    roadmap_coherence_preserved: bool
    operational_continuity_preserved: bool
    execution_traceability_preserved: bool
    human_visibility_payload: dict[str, Any] = field(default_factory=dict)
    roadmap_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "roadmap_id": self.roadmap_id,
            "roadmap_sources": list(self.roadmap_sources),
            "phase_structure": [
                dict(phase) for phase in self.phase_structure
            ],
            "subphase_structure": list(self.subphase_structure),
            "execution_order": list(self.execution_order),
            "priority_context": dict(self.priority_context),
            "dependency_relationships": [
                dict(item) for item in self.dependency_relationships
            ],
            "governance_context": dict(self.governance_context),
            "continuation_status": self.continuation_status,
            "roadmap_legitimacy_valid": self.roadmap_legitimacy_valid,
            "phase_consistency_valid": self.phase_consistency_valid,
            "dependency_integrity_valid": self.dependency_integrity_valid,
            "governance_alignment_valid": self.governance_alignment_valid,
            "execution_continuity_valid": self.execution_continuity_valid,
            "roadmap_coherence_preserved": self.roadmap_coherence_preserved,
            "operational_continuity_preserved": (
                self.operational_continuity_preserved
            ),
            "execution_traceability_preserved": (
                self.execution_traceability_preserved
            ),
            "human_visibility_payload": dict(self.human_visibility_payload),
            "roadmap_lifecycle": [
                dict(entry) for entry in self.roadmap_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class PhasesRoadmapReader:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def read(
        self,
        request: PhasesRoadmapReaderRequest,
        reading_permitted: bool = True,
    ) -> PhasesRoadmapReaderResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        roadmap_id = request.roadmap_id or str(uuid4())

        try:
            knowledge_core = self._result_dict(request.knowledge_core)
            roots = self._resolve_sources(request, knowledge_core)
            authorized_roots = tuple(
                root
                for root in roots
                if str(root) not in self._unauthorized_sources(request, roots)
            )
            phase_files = self._discover_phase_files(request, authorized_roots)
            execution_order = tuple(
                self._subphase_name(path) for path in phase_files
            )
            phase_structure = self._phase_structure(phase_files)
            dependencies = self._dependencies(execution_order)
            priority_context = self._priority_context(request, execution_order)
            continuation_status = self._continuation_status(
                request,
                execution_order,
            )
            governance_context = self._governance_context(
                request,
                knowledge_core,
            )
            reasons = self._validation_reasons(
                request=request,
                roots=roots,
                phase_files=phase_files,
                execution_order=execution_order,
                governance_context=governance_context,
                reading_permitted=reading_permitted,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    ROADMAP_STATUS_BLOCKED
                    if blocked
                    else ROADMAP_STATUS_INTERPRETED
                ),
                success=not blocked,
                roadmap_id=roadmap_id,
                request=request,
                roots=roots,
                phase_structure=phase_structure,
                execution_order=execution_order,
                priority_context=priority_context,
                dependencies=dependencies,
                governance_context=governance_context,
                continuation_status=continuation_status,
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
                roadmap_id=roadmap_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def interpret(
        self,
        request: PhasesRoadmapReaderRequest,
        reading_permitted: bool = True,
    ) -> PhasesRoadmapReaderResult:
        return self.read(request, reading_permitted=reading_permitted)

    def _result(
        self,
        status: str,
        success: bool,
        roadmap_id: str,
        request: PhasesRoadmapReaderRequest,
        roots: tuple[Path, ...],
        phase_structure: tuple[dict[str, Any], ...],
        execution_order: tuple[str, ...],
        priority_context: dict[str, Any],
        dependencies: tuple[dict[str, Any], ...],
        governance_context: dict[str, Any],
        continuation_status: str,
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> PhasesRoadmapReaderResult:
        finished_at = datetime.now(timezone.utc)
        roadmap_legitimate = bool(roots) and not self._unauthorized_sources(
            request,
            roots,
        )
        phase_consistent = bool(phase_structure) and bool(execution_order)
        dependency_valid = self._dependencies_valid(
            request,
            execution_order,
        )
        governance_valid = bool(governance_context)
        continuity_valid = continuation_status in {
            "ready",
            "roadmap_completed",
        }
        return PhasesRoadmapReaderResult(
            status=status,
            success=success,
            roadmap_id=roadmap_id,
            roadmap_sources=tuple(str(root) for root in roots),
            phase_structure=phase_structure,
            subphase_structure=execution_order,
            execution_order=execution_order,
            priority_context=dict(priority_context),
            dependency_relationships=dependencies,
            governance_context=dict(governance_context),
            continuation_status=continuation_status,
            roadmap_legitimacy_valid=roadmap_legitimate,
            phase_consistency_valid=phase_consistent,
            dependency_integrity_valid=dependency_valid,
            governance_alignment_valid=governance_valid,
            execution_continuity_valid=continuity_valid,
            roadmap_coherence_preserved=success and phase_consistent,
            operational_continuity_preserved=success and continuity_valid,
            execution_traceability_preserved=success and bool(execution_order),
            human_visibility_payload=self._visibility_payload(
                execution_order,
                priority_context,
                dependencies,
                governance_context,
            ),
            roadmap_lifecycle=(
                self._lifecycle("roadmap_discovery"),
                self._lifecycle("phase_interpretation"),
                self._lifecycle("execution_prioritization"),
                self._lifecycle(status),
            ),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons or ["roadmap_interpreted"]),
            error=error,
            metadata=dict(request.metadata),
        )

    def _validation_reasons(
        self,
        request: PhasesRoadmapReaderRequest,
        roots: tuple[Path, ...],
        phase_files: tuple[Path, ...],
        execution_order: tuple[str, ...],
        governance_context: dict[str, Any],
        reading_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not reading_permitted:
            reasons.append("roadmap_reading_not_permitted")
        if not roots:
            reasons.append("roadmap_sources_required")
        for root in self._unauthorized_sources(request, roots):
            reasons.append(f"roadmap_source_unauthorized:{root}")
        if not phase_files:
            reasons.append("phase_documentation_not_found")
        if not execution_order:
            reasons.append("subphase_structure_not_found")
        if request.current_subphase and request.current_subphase not in execution_order:
            reasons.append("current_subphase_not_in_roadmap")
        for completed in request.completed_subphases:
            if completed not in execution_order:
                reasons.append(f"completed_subphase_unknown:{completed}")
        if not governance_context:
            reasons.append("governance_context_required")
        if request.modify_roadmap_requested:
            reasons.append("roadmap_modification_blocked")
        if request.invent_subphase_requested:
            reasons.append("subphase_invention_blocked")
        if request.alter_priorities_requested:
            reasons.append("execution_priority_alteration_blocked")
        if request.ignore_dependencies_requested:
            reasons.append("roadmap_dependency_ignore_blocked")
        if request.overwrite_governance_planning_requested:
            reasons.append("governance_planning_overwrite_blocked")
        if request.hide_blocking_conditions_requested:
            reasons.append("roadmap_blocking_conditions_concealment_blocked")
        if request.minimize_governance_conflicts_requested:
            reasons.append("roadmap_governance_conflict_minimization_blocked")
        return self._unique(reasons)

    def _resolve_sources(
        self,
        request: PhasesRoadmapReaderRequest,
        knowledge_core: dict[str, Any],
    ) -> tuple[Path, ...]:
        raw_sources = list(request.roadmap_sources)
        if not raw_sources:
            raw_sources.extend(str(item) for item in knowledge_core.get("source_roots") or [])
        roots: list[Path] = []
        for raw_source in raw_sources:
            raw = str(raw_source).strip()
            if not raw:
                continue
            source = Path(raw).expanduser().resolve()
            if source.exists():
                roots.append(source)
        return tuple(self._unique_paths(roots))

    def _discover_phase_files(
        self,
        request: PhasesRoadmapReaderRequest,
        roots: tuple[Path, ...],
    ) -> tuple[Path, ...]:
        extensions = {
            extension.lower()
            for extension in request.allowed_extensions
            if extension
        }
        files: list[Path] = []
        limit = max(1, int(request.max_files or 1))
        for root in roots:
            candidates = [root] if root.is_file() else sorted(root.rglob("*"))
            for path in candidates:
                if len(files) >= limit:
                    return tuple(sorted(files, key=self._order_key))
                if not path.is_file() or path.suffix.lower() not in extensions:
                    continue
                if self._looks_like_phase_doc(path):
                    files.append(path)
        return tuple(sorted(self._unique_paths(files), key=self._order_key))

    def _looks_like_phase_doc(self, path: Path) -> bool:
        name = path.name.lower()
        return bool(PHASE_FILE_PATTERN.match(path.name)) or "phase" in name

    def _phase_structure(
        self,
        phase_files: tuple[Path, ...],
    ) -> tuple[dict[str, Any], ...]:
        phases: dict[str, dict[str, Any]] = {}
        for path in phase_files:
            subphase = self._subphase_name(path)
            phase_id = subphase.split(".", 1)[0] if "." in subphase else subphase
            phase = phases.setdefault(
                phase_id,
                {
                    "phase_id": phase_id,
                    "subphases": [],
                    "source_paths": [],
                },
            )
            phase["subphases"].append(subphase)
            phase["source_paths"].append(str(path))
        return tuple(phases[key] for key in sorted(phases, key=self._phase_key))

    def _dependencies(
        self,
        execution_order: tuple[str, ...],
    ) -> tuple[dict[str, Any], ...]:
        dependencies: list[dict[str, Any]] = []
        previous: str | None = None
        for subphase in execution_order:
            dependencies.append(
                {
                    "subphase": subphase,
                    "depends_on": [previous] if previous else [],
                }
            )
            previous = subphase
        return tuple(dependencies)

    def _priority_context(
        self,
        request: PhasesRoadmapReaderRequest,
        execution_order: tuple[str, ...],
    ) -> dict[str, Any]:
        completed = set(request.completed_subphases)
        pending = [item for item in execution_order if item not in completed]
        next_subphase = self._next_subphase(request.current_subphase, execution_order)
        return {
            "current_subphase": request.current_subphase,
            "next_subphase": next_subphase,
            "pending_subphases": pending,
            "completed_subphases": list(request.completed_subphases),
            "total_subphases": len(execution_order),
        }

    def _continuation_status(
        self,
        request: PhasesRoadmapReaderRequest,
        execution_order: tuple[str, ...],
    ) -> str:
        if not execution_order:
            return "blocked"
        if not request.current_subphase:
            return "ready"
        if request.current_subphase not in execution_order:
            return "blocked"
        return "ready" if self._next_subphase(
            request.current_subphase,
            execution_order,
        ) else "roadmap_completed"

    def _governance_context(
        self,
        request: PhasesRoadmapReaderRequest,
        knowledge_core: dict[str, Any],
    ) -> dict[str, Any]:
        if request.governance_context:
            return dict(request.governance_context)
        return dict(knowledge_core.get("governance_context") or {})

    def _visibility_payload(
        self,
        execution_order: tuple[str, ...],
        priority_context: dict[str, Any],
        dependencies: tuple[dict[str, Any], ...],
        governance_context: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "roadmap_status": "loaded" if execution_order else "missing",
            "subphases_detected": list(execution_order),
            "execution_continuity": dict(priority_context),
            "dependencies_roadmap": [dict(item) for item in dependencies],
            "governance_alignment": dict(governance_context),
            "operational_priorities": list(
                priority_context.get("pending_subphases") or []
            )[:10],
        }

    def _dependencies_valid(
        self,
        request: PhasesRoadmapReaderRequest,
        execution_order: tuple[str, ...],
    ) -> bool:
        known = set(execution_order)
        return all(item in known for item in request.completed_subphases)

    def _next_subphase(
        self,
        current_subphase: str | None,
        execution_order: tuple[str, ...],
    ) -> str | None:
        if not execution_order:
            return None
        if not current_subphase:
            return execution_order[0]
        if current_subphase not in execution_order:
            return None
        index = execution_order.index(current_subphase) + 1
        return execution_order[index] if index < len(execution_order) else None

    def _subphase_name(self, path: Path) -> str:
        return path.name

    def _order_key(self, path: Path) -> tuple[Any, ...]:
        match = PHASE_FILE_PATTERN.match(path.name)
        if not match:
            return ((9999,), path.name.lower())
        numeric = tuple(int(part) for part in match.group("order").split("."))
        return (numeric, path.name.lower())

    def _phase_key(self, value: str) -> tuple[Any, ...]:
        parts = [int(part) for part in value.split(".") if part.isdigit()]
        return (tuple(parts or [9999]), value)

    def _unauthorized_sources(
        self,
        request: PhasesRoadmapReaderRequest,
        roots: tuple[Path, ...],
    ) -> list[str]:
        unauthorized: list[str] = []
        for root in roots:
            root_key = str(root)
            allowed = request.source_authorizations.get(root_key, True)
            if allowed is False:
                unauthorized.append(root_key)
        return unauthorized

    def _result_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, KnowledgeCoreReaderResult):
            return value.to_dict()
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

    def _error_result(
        self,
        roadmap_id: str,
        request: PhasesRoadmapReaderRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> PhasesRoadmapReaderResult:
        finished_at = datetime.now(timezone.utc)
        return PhasesRoadmapReaderResult(
            status=ROADMAP_STATUS_ERROR,
            success=False,
            roadmap_id=roadmap_id,
            roadmap_sources=tuple(request.roadmap_sources),
            phase_structure=(),
            subphase_structure=(),
            execution_order=(),
            priority_context={},
            dependency_relationships=(),
            governance_context=dict(request.governance_context),
            continuation_status="blocked",
            roadmap_legitimacy_valid=False,
            phase_consistency_valid=False,
            dependency_integrity_valid=False,
            governance_alignment_valid=False,
            execution_continuity_valid=False,
            roadmap_coherence_preserved=False,
            operational_continuity_preserved=False,
            execution_traceability_preserved=False,
            human_visibility_payload={},
            roadmap_lifecycle=(self._lifecycle(ROADMAP_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("phases_roadmap_reader_error_contained",),
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

    def _unique_paths(self, values: list[Path]) -> list[Path]:
        seen: set[str] = set()
        unique: list[Path] = []
        for value in values:
            key = str(value)
            if key not in seen:
                seen.add(key)
                unique.append(value)
        return unique

    def _publish(self, result: PhasesRoadmapReaderResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_phases_roadmap_reader_result",
        ):
            self.status.mark_phases_roadmap_reader_result(result.to_dict())

    def _log_result(self, result: PhasesRoadmapReaderResult) -> None:
        if result.status == ROADMAP_STATUS_ERROR:
            logger.error(
                "phases_roadmap_reader: error roadmap_id=%s error=%s",
                result.roadmap_id,
                result.error,
            )
            return
        if result.status == ROADMAP_STATUS_BLOCKED:
            logger.warning(
                "phases_roadmap_reader: blocked roadmap_id=%s reasons=%s",
                result.roadmap_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "phases_roadmap_reader: interpreted roadmap_id=%s subphases=%s",
            result.roadmap_id,
            len(result.execution_order),
        )
