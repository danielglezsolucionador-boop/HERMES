"""
Read-only Knowledge Core reader for Hermes operational workflows.

This layer discovers authorized documentation sources, reads bounded markdown
context, and builds an execution context without modifying official documents,
roadmaps, standards, or governance records.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

KNOWLEDGE_STATUS_LOADED = "loaded"
KNOWLEDGE_STATUS_BLOCKED = "blocked"
KNOWLEDGE_STATUS_ERROR = "error"

REQUIRED_COMPONENTS = (
    "phase_documentation",
    "roadmap_context",
    "technical_standards",
    "ecosystem_structure",
    "execution_history",
    "dependency_context",
    "governance_context",
)

DEFAULT_EXTENSIONS = (".md", ".txt")

COMPONENT_HINTS = {
    "phase_documentation": ("phase", "phases", "subphase"),
    "roadmap_context": ("roadmap", "workflow", "pipeline"),
    "technical_standards": ("standard", "rules", "validation", "protocol"),
    "ecosystem_structure": ("ecosystem", "agent", "registry"),
    "execution_history": ("memory", "history", "execution"),
    "dependency_context": ("dependency", "runtime", "task", "runner"),
    "governance_context": ("governance", "approval", "authority"),
}


@dataclass(frozen=True)
class KnowledgeCoreReaderRequest:
    read_id: str | None = None
    source_roots: tuple[str, ...] = field(default_factory=tuple)
    source_authorizations: dict[str, bool] = field(default_factory=dict)
    allowed_extensions: tuple[str, ...] = DEFAULT_EXTENSIONS
    max_files: int = 200
    max_bytes_per_file: int = 64_000
    required_components: tuple[str, ...] = REQUIRED_COMPONENTS
    current_workflow: str | None = None
    completed_workflows: tuple[str, ...] = field(default_factory=tuple)
    modify_documentation_requested: bool = False
    alter_roadmap_requested: bool = False
    overwrite_governance_context_requested: bool = False
    invent_context_requested: bool = False
    ignore_critical_dependencies_requested: bool = False
    minimize_governance_conflicts_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeCoreReaderResult:
    status: str
    success: bool
    read_id: str
    source_roots: tuple[str, ...]
    knowledge_sources: tuple[dict[str, Any], ...]
    components_found: dict[str, bool]
    documents_read: int
    total_bytes_read: int
    execution_context: dict[str, Any]
    roadmap_context: dict[str, Any]
    dependency_context: dict[str, Any]
    governance_context: dict[str, Any]
    source_legitimacy_valid: bool
    roadmap_consistency_valid: bool
    standards_compatible: bool
    dependency_integrity_valid: bool
    governance_alignment_valid: bool
    context_continuity_preserved: bool
    architecture_consistency_preserved: bool
    ecosystem_coherence_preserved: bool
    operational_traceability_preserved: bool
    read_only_preserved: bool
    human_visibility_payload: dict[str, Any] = field(default_factory=dict)
    read_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "read_id": self.read_id,
            "source_roots": list(self.source_roots),
            "knowledge_sources": [
                dict(source) for source in self.knowledge_sources
            ],
            "components_found": dict(self.components_found),
            "documents_read": self.documents_read,
            "total_bytes_read": self.total_bytes_read,
            "execution_context": dict(self.execution_context),
            "roadmap_context": dict(self.roadmap_context),
            "dependency_context": dict(self.dependency_context),
            "governance_context": dict(self.governance_context),
            "source_legitimacy_valid": self.source_legitimacy_valid,
            "roadmap_consistency_valid": self.roadmap_consistency_valid,
            "standards_compatible": self.standards_compatible,
            "dependency_integrity_valid": self.dependency_integrity_valid,
            "governance_alignment_valid": self.governance_alignment_valid,
            "context_continuity_preserved": (
                self.context_continuity_preserved
            ),
            "architecture_consistency_preserved": (
                self.architecture_consistency_preserved
            ),
            "ecosystem_coherence_preserved": (
                self.ecosystem_coherence_preserved
            ),
            "operational_traceability_preserved": (
                self.operational_traceability_preserved
            ),
            "read_only_preserved": self.read_only_preserved,
            "human_visibility_payload": dict(self.human_visibility_payload),
            "read_lifecycle": [
                dict(entry) for entry in self.read_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class KnowledgeCoreReader:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def read(
        self,
        request: KnowledgeCoreReaderRequest,
        reading_permitted: bool = True,
    ) -> KnowledgeCoreReaderResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        read_id = request.read_id or str(uuid4())

        try:
            roots = self._resolve_roots(request)
            authorized_roots = tuple(
                root
                for root in roots
                if str(root) not in self._unauthorized_roots(request, roots)
            )
            sources = self._discover_sources(request, authorized_roots)
            components = self._components_found(request, sources)
            contexts = self._contexts(request, sources, components)
            reasons = self._validation_reasons(
                request=request,
                roots=roots,
                sources=sources,
                components=components,
                reading_permitted=reading_permitted,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    KNOWLEDGE_STATUS_BLOCKED
                    if blocked
                    else KNOWLEDGE_STATUS_LOADED
                ),
                success=not blocked,
                read_id=read_id,
                request=request,
                roots=roots,
                sources=sources,
                components=components,
                contexts=contexts,
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
                read_id=read_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def load(
        self,
        request: KnowledgeCoreReaderRequest,
        reading_permitted: bool = True,
    ) -> KnowledgeCoreReaderResult:
        return self.read(request, reading_permitted=reading_permitted)

    def _result(
        self,
        status: str,
        success: bool,
        read_id: str,
        request: KnowledgeCoreReaderRequest,
        roots: tuple[Path, ...],
        sources: tuple[dict[str, Any], ...],
        components: dict[str, bool],
        contexts: dict[str, dict[str, Any]],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> KnowledgeCoreReaderResult:
        finished_at = datetime.now(timezone.utc)
        source_legitimacy = bool(roots) and not self._unauthorized_roots(
            request,
            roots,
        )
        roadmap_valid = components.get("roadmap_context", False)
        standards_valid = components.get("technical_standards", False)
        dependency_valid = components.get("dependency_context", False)
        governance_valid = components.get("governance_context", False)
        read_only = not (
            request.modify_documentation_requested
            or request.alter_roadmap_requested
            or request.overwrite_governance_context_requested
        )
        return KnowledgeCoreReaderResult(
            status=status,
            success=success,
            read_id=read_id,
            source_roots=tuple(str(root) for root in roots),
            knowledge_sources=sources,
            components_found=dict(components),
            documents_read=len(sources),
            total_bytes_read=sum(int(source["size_bytes"]) for source in sources),
            execution_context=dict(contexts["execution_context"]),
            roadmap_context=dict(contexts["roadmap_context"]),
            dependency_context=dict(contexts["dependency_context"]),
            governance_context=dict(contexts["governance_context"]),
            source_legitimacy_valid=source_legitimacy,
            roadmap_consistency_valid=roadmap_valid,
            standards_compatible=standards_valid,
            dependency_integrity_valid=dependency_valid,
            governance_alignment_valid=governance_valid,
            context_continuity_preserved=success and roadmap_valid,
            architecture_consistency_preserved=success and standards_valid,
            ecosystem_coherence_preserved=success
            and components.get("ecosystem_structure", False),
            operational_traceability_preserved=success
            and components.get("execution_history", False),
            read_only_preserved=read_only,
            human_visibility_payload=self._visibility_payload(
                roots,
                sources,
                components,
                contexts,
            ),
            read_lifecycle=(
                self._lifecycle("source_discovery"),
                self._lifecycle("knowledge_reading"),
                self._lifecycle("context_interpretation"),
                self._lifecycle(status),
            ),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons or ["knowledge_core_loaded"]),
            error=error,
            metadata=dict(request.metadata),
        )

    def _validation_reasons(
        self,
        request: KnowledgeCoreReaderRequest,
        roots: tuple[Path, ...],
        sources: tuple[dict[str, Any], ...],
        components: dict[str, bool],
        reading_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not reading_permitted:
            reasons.append("knowledge_core_reading_not_permitted")
        if not roots:
            reasons.append("knowledge_source_roots_required")
        for root in self._unauthorized_roots(request, roots):
            reasons.append(f"knowledge_source_unauthorized:{root}")
        if not sources:
            reasons.append("knowledge_sources_not_found")
        for component in request.required_components:
            if not components.get(component, False):
                reasons.append(f"missing_knowledge_component:{component}")
        if request.modify_documentation_requested:
            reasons.append("knowledge_documentation_modification_blocked")
        if request.alter_roadmap_requested:
            reasons.append("knowledge_roadmap_alteration_blocked")
        if request.overwrite_governance_context_requested:
            reasons.append("governance_context_overwrite_blocked")
        if request.invent_context_requested:
            reasons.append("knowledge_context_invention_blocked")
        if request.ignore_critical_dependencies_requested:
            reasons.append("critical_dependency_ignored_blocked")
        if request.minimize_governance_conflicts_requested:
            reasons.append("governance_conflict_minimization_blocked")
        return self._unique(reasons)

    def _resolve_roots(self, request: KnowledgeCoreReaderRequest) -> tuple[Path, ...]:
        roots: list[Path] = []
        for raw_root in request.source_roots:
            raw = str(raw_root).strip()
            if not raw:
                continue
            root = Path(raw).expanduser().resolve()
            if root.exists() and root.is_dir():
                roots.append(root)
        return tuple(self._unique_paths(roots))

    def _discover_sources(
        self,
        request: KnowledgeCoreReaderRequest,
        roots: tuple[Path, ...],
    ) -> tuple[dict[str, Any], ...]:
        extensions = {
            extension.lower()
            for extension in request.allowed_extensions
            if extension
        }
        limit = max(1, int(request.max_files or 1))
        sources: list[dict[str, Any]] = []
        for root in roots:
            for path in sorted(root.rglob("*")):
                if len(sources) >= limit:
                    return tuple(sources)
                if not path.is_file() or path.suffix.lower() not in extensions:
                    continue
                source = self._source_record(
                    path=path,
                    root=root,
                    max_bytes=max(1, int(request.max_bytes_per_file or 1)),
                )
                if source:
                    sources.append(source)
        return tuple(sources)

    def _source_record(
        self,
        path: Path,
        root: Path,
        max_bytes: int,
    ) -> dict[str, Any] | None:
        try:
            size = path.stat().st_size
            content = path.read_text(encoding="utf-8", errors="replace")[
                :max_bytes
            ]
        except OSError:
            return None
        title = self._title(content, path)
        components = self._components_for(path, content)
        return {
            "path": str(path),
            "relative_path": str(path.relative_to(root)),
            "root": str(root),
            "title": title,
            "size_bytes": size,
            "components": list(components),
        }

    def _components_found(
        self,
        request: KnowledgeCoreReaderRequest,
        sources: tuple[dict[str, Any], ...],
    ) -> dict[str, bool]:
        components = {component: False for component in request.required_components}
        for source in sources:
            for component in source.get("components") or []:
                if component in components:
                    components[component] = True
        return components

    def _contexts(
        self,
        request: KnowledgeCoreReaderRequest,
        sources: tuple[dict[str, Any], ...],
        components: dict[str, bool],
    ) -> dict[str, dict[str, Any]]:
        roadmap_sources = self._sources_for(sources, "roadmap_context")
        dependency_sources = self._sources_for(sources, "dependency_context")
        governance_sources = self._sources_for(sources, "governance_context")
        return {
            "execution_context": {
                "current_workflow": request.current_workflow,
                "completed_workflows": list(request.completed_workflows),
                "source_count": len(sources),
                "components_found": dict(components),
            },
            "roadmap_context": {
                "sources": roadmap_sources,
                "roadmap_loaded": bool(roadmap_sources),
            },
            "dependency_context": {
                "sources": dependency_sources,
                "dependencies_loaded": bool(dependency_sources),
            },
            "governance_context": {
                "sources": governance_sources,
                "governance_loaded": bool(governance_sources),
            },
        }

    def _visibility_payload(
        self,
        roots: tuple[Path, ...],
        sources: tuple[dict[str, Any], ...],
        components: dict[str, bool],
        contexts: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "knowledge_roots": [str(root) for root in roots],
            "knowledge_sources": [
                {
                    "relative_path": source["relative_path"],
                    "components": list(source["components"]),
                    "title": source["title"],
                }
                for source in sources[:25]
            ],
            "roadmap_context": dict(contexts["roadmap_context"]),
            "dependency_context": dict(contexts["dependency_context"]),
            "governance_context": dict(contexts["governance_context"]),
            "components_found": dict(components),
        }

    def _components_for(self, path: Path, content: str) -> tuple[str, ...]:
        haystack = f"{path.as_posix()} {content[:2000]}".lower()
        components = [
            component
            for component, hints in COMPONENT_HINTS.items()
            if any(hint in haystack for hint in hints)
        ]
        return tuple(self._unique(components))

    def _sources_for(
        self,
        sources: tuple[dict[str, Any], ...],
        component: str,
    ) -> list[str]:
        return [
            str(source["relative_path"])
            for source in sources
            if component in (source.get("components") or [])
        ]

    def _unauthorized_roots(
        self,
        request: KnowledgeCoreReaderRequest,
        roots: tuple[Path, ...],
    ) -> list[str]:
        unauthorized: list[str] = []
        for root in roots:
            root_key = str(root)
            allowed = request.source_authorizations.get(root_key, True)
            if allowed is False:
                unauthorized.append(root_key)
        return unauthorized

    def _title(self, content: str, path: Path) -> str:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip() or path.stem
        return path.stem

    def _error_result(
        self,
        read_id: str,
        request: KnowledgeCoreReaderRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> KnowledgeCoreReaderResult:
        finished_at = datetime.now(timezone.utc)
        return KnowledgeCoreReaderResult(
            status=KNOWLEDGE_STATUS_ERROR,
            success=False,
            read_id=read_id,
            source_roots=tuple(request.source_roots),
            knowledge_sources=(),
            components_found={},
            documents_read=0,
            total_bytes_read=0,
            execution_context={},
            roadmap_context={},
            dependency_context={},
            governance_context={},
            source_legitimacy_valid=False,
            roadmap_consistency_valid=False,
            standards_compatible=False,
            dependency_integrity_valid=False,
            governance_alignment_valid=False,
            context_continuity_preserved=False,
            architecture_consistency_preserved=False,
            ecosystem_coherence_preserved=False,
            operational_traceability_preserved=False,
            read_only_preserved=False,
            human_visibility_payload={},
            read_lifecycle=(self._lifecycle(KNOWLEDGE_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("knowledge_core_reader_error_contained",),
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

    def _publish(self, result: KnowledgeCoreReaderResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_knowledge_core_reader_result",
        ):
            self.status.mark_knowledge_core_reader_result(result.to_dict())

    def _log_result(self, result: KnowledgeCoreReaderResult) -> None:
        if result.status == KNOWLEDGE_STATUS_ERROR:
            logger.error(
                "knowledge_core_reader: error read_id=%s error=%s",
                result.read_id,
                result.error,
            )
            return
        if result.status == KNOWLEDGE_STATUS_BLOCKED:
            logger.warning(
                "knowledge_core_reader: blocked read_id=%s reasons=%s",
                result.read_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "knowledge_core_reader: loaded read_id=%s sources=%s",
            result.read_id,
            result.documents_read,
        )
