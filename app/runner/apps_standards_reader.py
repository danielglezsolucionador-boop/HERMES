"""
Read-only apps and standards reader for Hermes operational workflows.

This layer interprets authorized ecosystem application and standards documents
without redefining official standards, responsibilities, permissions, or
governance structures.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.runner.knowledge_core_reader import KnowledgeCoreReaderResult

logger = logging.getLogger(__name__)

APPS_STANDARDS_STATUS_INTERPRETED = "interpreted"
APPS_STANDARDS_STATUS_BLOCKED = "blocked"
APPS_STANDARDS_STATUS_ERROR = "error"

DEFAULT_EXTENSIONS = (".md", ".txt")


@dataclass(frozen=True)
class AppsStandardsReaderRequest:
    read_id: str | None = None
    standards_sources: tuple[str, ...] = field(default_factory=tuple)
    source_authorizations: dict[str, bool] = field(default_factory=dict)
    allowed_extensions: tuple[str, ...] = DEFAULT_EXTENSIONS
    max_files: int = 300
    knowledge_core: KnowledgeCoreReaderResult | dict[str, Any] | Any | None = None
    governance_context: dict[str, Any] = field(default_factory=dict)
    redefine_standards_requested: bool = False
    alter_responsibilities_requested: bool = False
    invent_architecture_rules_requested: bool = False
    modify_governance_structures_requested: bool = False
    overwrite_ecosystem_consistency_requested: bool = False
    invent_execution_permissions_requested: bool = False
    ignore_authority_boundaries_requested: bool = False
    minimize_governance_conflicts_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AppsStandardsReaderResult:
    status: str
    success: bool
    read_id: str
    standards_sources: tuple[str, ...]
    systems_detected: tuple[dict[str, Any], ...]
    organizational_roles: tuple[str, ...]
    technical_standards: tuple[dict[str, Any], ...]
    architecture_rules: tuple[str, ...]
    operational_responsibilities: tuple[str, ...]
    governance_context: dict[str, Any]
    execution_compatibility: dict[str, Any]
    standards_legitimacy_valid: bool
    architecture_compatibility_valid: bool
    governance_alignment_valid: bool
    execution_permissions_valid: bool
    ecosystem_consistency_valid: bool
    architecture_integrity_preserved: bool
    operational_continuity_preserved: bool
    execution_traceability_preserved: bool
    human_visibility_payload: dict[str, Any] = field(default_factory=dict)
    reader_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "standards_sources": list(self.standards_sources),
            "systems_detected": [
                dict(system) for system in self.systems_detected
            ],
            "organizational_roles": list(self.organizational_roles),
            "technical_standards": [
                dict(standard) for standard in self.technical_standards
            ],
            "architecture_rules": list(self.architecture_rules),
            "operational_responsibilities": list(
                self.operational_responsibilities
            ),
            "governance_context": dict(self.governance_context),
            "execution_compatibility": dict(self.execution_compatibility),
            "standards_legitimacy_valid": self.standards_legitimacy_valid,
            "architecture_compatibility_valid": (
                self.architecture_compatibility_valid
            ),
            "governance_alignment_valid": self.governance_alignment_valid,
            "execution_permissions_valid": (
                self.execution_permissions_valid
            ),
            "ecosystem_consistency_valid": self.ecosystem_consistency_valid,
            "architecture_integrity_preserved": (
                self.architecture_integrity_preserved
            ),
            "operational_continuity_preserved": (
                self.operational_continuity_preserved
            ),
            "execution_traceability_preserved": (
                self.execution_traceability_preserved
            ),
            "human_visibility_payload": dict(self.human_visibility_payload),
            "reader_lifecycle": [
                dict(entry) for entry in self.reader_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class AppsStandardsReader:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def read(
        self,
        request: AppsStandardsReaderRequest,
        reading_permitted: bool = True,
    ) -> AppsStandardsReaderResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        read_id = request.read_id or str(uuid4())

        try:
            knowledge_core = self._result_dict(request.knowledge_core)
            roots = self._resolve_sources(request, knowledge_core)
            authorized_roots = tuple(
                root
                for root in roots
                if str(root) not in self._unauthorized_sources(request, roots)
            )
            documents = self._read_documents(request, authorized_roots)
            systems = tuple(self._systems(documents))
            roles = tuple(self._roles(documents))
            standards = tuple(self._standards(documents))
            architecture_rules = tuple(self._architecture_rules(documents))
            responsibilities = tuple(self._responsibilities(documents))
            governance_context = self._governance_context(
                request,
                knowledge_core,
                documents,
            )
            compatibility = self._execution_compatibility(
                systems,
                standards,
                architecture_rules,
                governance_context,
            )
            reasons = self._validation_reasons(
                request=request,
                roots=roots,
                documents=documents,
                systems=systems,
                standards=standards,
                architecture_rules=architecture_rules,
                responsibilities=responsibilities,
                governance_context=governance_context,
                compatibility=compatibility,
                reading_permitted=reading_permitted,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    APPS_STANDARDS_STATUS_BLOCKED
                    if blocked
                    else APPS_STANDARDS_STATUS_INTERPRETED
                ),
                success=not blocked,
                read_id=read_id,
                request=request,
                roots=roots,
                systems=systems,
                roles=roles,
                standards=standards,
                architecture_rules=architecture_rules,
                responsibilities=responsibilities,
                governance_context=governance_context,
                compatibility=compatibility,
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

    def interpret(
        self,
        request: AppsStandardsReaderRequest,
        reading_permitted: bool = True,
    ) -> AppsStandardsReaderResult:
        return self.read(request, reading_permitted=reading_permitted)

    def _result(
        self,
        status: str,
        success: bool,
        read_id: str,
        request: AppsStandardsReaderRequest,
        roots: tuple[Path, ...],
        systems: tuple[dict[str, Any], ...],
        roles: tuple[str, ...],
        standards: tuple[dict[str, Any], ...],
        architecture_rules: tuple[str, ...],
        responsibilities: tuple[str, ...],
        governance_context: dict[str, Any],
        compatibility: dict[str, Any],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> AppsStandardsReaderResult:
        finished_at = datetime.now(timezone.utc)
        standards_valid = bool(standards) and not self._unauthorized_sources(
            request,
            roots,
        )
        architecture_valid = bool(architecture_rules)
        governance_valid = bool(governance_context)
        permissions_valid = bool(compatibility.get("execution_permissions"))
        ecosystem_valid = bool(systems) and bool(responsibilities)
        return AppsStandardsReaderResult(
            status=status,
            success=success,
            read_id=read_id,
            standards_sources=tuple(str(root) for root in roots),
            systems_detected=systems,
            organizational_roles=roles,
            technical_standards=standards,
            architecture_rules=architecture_rules,
            operational_responsibilities=responsibilities,
            governance_context=dict(governance_context),
            execution_compatibility=dict(compatibility),
            standards_legitimacy_valid=standards_valid,
            architecture_compatibility_valid=architecture_valid,
            governance_alignment_valid=governance_valid,
            execution_permissions_valid=permissions_valid,
            ecosystem_consistency_valid=ecosystem_valid,
            architecture_integrity_preserved=success and architecture_valid,
            operational_continuity_preserved=success and ecosystem_valid,
            execution_traceability_preserved=success and bool(roots),
            human_visibility_payload=self._visibility_payload(
                systems,
                standards,
                governance_context,
                compatibility,
                responsibilities,
            ),
            reader_lifecycle=(
                self._lifecycle("system_discovery"),
                self._lifecycle("standards_reading"),
                self._lifecycle("role_interpretation"),
                self._lifecycle(status),
            ),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons or ["apps_and_standards_interpreted"]),
            error=error,
            metadata=dict(request.metadata),
        )

    def _validation_reasons(
        self,
        request: AppsStandardsReaderRequest,
        roots: tuple[Path, ...],
        documents: tuple[dict[str, Any], ...],
        systems: tuple[dict[str, Any], ...],
        standards: tuple[dict[str, Any], ...],
        architecture_rules: tuple[str, ...],
        responsibilities: tuple[str, ...],
        governance_context: dict[str, Any],
        compatibility: dict[str, Any],
        reading_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not reading_permitted:
            reasons.append("apps_standards_reading_not_permitted")
        if not roots:
            reasons.append("standards_sources_required")
        for root in self._unauthorized_sources(request, roots):
            reasons.append(f"standards_source_unauthorized:{root}")
        if not documents:
            reasons.append("standards_documents_not_found")
        if not systems:
            reasons.append("ecosystem_applications_not_found")
        if not standards:
            reasons.append("technical_standards_not_found")
        if not architecture_rules:
            reasons.append("architecture_rules_not_found")
        if not responsibilities:
            reasons.append("operational_responsibilities_not_found")
        if not governance_context:
            reasons.append("governance_alignment_required")
        if not compatibility.get("execution_permissions"):
            reasons.append("execution_permissions_required")
        if request.redefine_standards_requested:
            reasons.append("standards_override_blocked")
        if request.alter_responsibilities_requested:
            reasons.append("responsibilities_alteration_blocked")
        if request.invent_architecture_rules_requested:
            reasons.append("architecture_rule_invention_blocked")
        if request.modify_governance_structures_requested:
            reasons.append("governance_structure_modification_blocked")
        if request.overwrite_ecosystem_consistency_requested:
            reasons.append("ecosystem_consistency_overwrite_blocked")
        if request.invent_execution_permissions_requested:
            reasons.append("execution_permission_invention_blocked")
        if request.ignore_authority_boundaries_requested:
            reasons.append("authority_boundary_ignore_blocked")
        if request.minimize_governance_conflicts_requested:
            reasons.append("governance_conflict_minimization_blocked")
        return self._unique(reasons)

    def _resolve_sources(
        self,
        request: AppsStandardsReaderRequest,
        knowledge_core: dict[str, Any],
    ) -> tuple[Path, ...]:
        raw_sources = list(request.standards_sources)
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

    def _read_documents(
        self,
        request: AppsStandardsReaderRequest,
        roots: tuple[Path, ...],
    ) -> tuple[dict[str, Any], ...]:
        extensions = {
            extension.lower()
            for extension in request.allowed_extensions
            if extension
        }
        documents: list[dict[str, Any]] = []
        limit = max(1, int(request.max_files or 1))
        for root in roots:
            candidates = [root] if root.is_file() else sorted(root.rglob("*"))
            for path in candidates:
                if len(documents) >= limit:
                    return tuple(documents)
                if not path.is_file() or path.suffix.lower() not in extensions:
                    continue
                document = self._document(path, root)
                if document:
                    documents.append(document)
        return tuple(documents)

    def _document(self, path: Path, root: Path) -> dict[str, Any] | None:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        return {
            "path": str(path),
            "relative_path": str(path.relative_to(root)),
            "title": self._title(content, path),
            "content": content[:4000],
        }

    def _systems(self, documents: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
        systems: list[dict[str, Any]] = []
        for document in documents:
            text = self._haystack(document)
            if any(word in text for word in ("app", "application", "agent", "system", "ecosystem")):
                systems.append(
                    {
                        "name": document["title"],
                        "source": document["relative_path"],
                    }
                )
        return systems

    def _roles(self, documents: tuple[dict[str, Any], ...]) -> list[str]:
        roles: list[str] = []
        for document in documents:
            text = self._haystack(document)
            for role in ("CEO", "CEREBRO", "VULCAN", "SENTINEL", "CENTINELA", "HERMES"):
                if role.lower() in text:
                    roles.append(role)
        return self._unique(roles)

    def _standards(
        self,
        documents: tuple[dict[str, Any], ...],
    ) -> list[dict[str, Any]]:
        standards: list[dict[str, Any]] = []
        for document in documents:
            text = self._haystack(document)
            if any(word in text for word in ("standard", "rule", "protocol", "validation")):
                standards.append(
                    {
                        "name": document["title"],
                        "source": document["relative_path"],
                    }
                )
        return standards

    def _architecture_rules(self, documents: tuple[dict[str, Any], ...]) -> list[str]:
        rules: list[str] = []
        for document in documents:
            text = self._haystack(document)
            if any(word in text for word in ("architecture", "runtime", "compatibility")):
                rules.append(document["title"])
        return self._unique(rules)

    def _responsibilities(self, documents: tuple[dict[str, Any], ...]) -> list[str]:
        responsibilities: list[str] = []
        for document in documents:
            text = self._haystack(document)
            if any(word in text for word in ("responsibility", "responsibilities", "authority", "owner")):
                responsibilities.append(document["title"])
        return self._unique(responsibilities)

    def _governance_context(
        self,
        request: AppsStandardsReaderRequest,
        knowledge_core: dict[str, Any],
        documents: tuple[dict[str, Any], ...],
    ) -> dict[str, Any]:
        if request.governance_context:
            return dict(request.governance_context)
        context = dict(knowledge_core.get("governance_context") or {})
        governance_sources = [
            document["relative_path"]
            for document in documents
            if "governance" in self._haystack(document)
        ]
        if governance_sources:
            context["governance_sources"] = governance_sources
        return context

    def _execution_compatibility(
        self,
        systems: tuple[dict[str, Any], ...],
        standards: tuple[dict[str, Any], ...],
        architecture_rules: tuple[str, ...],
        governance_context: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "systems_detected": len(systems),
            "standards_detected": len(standards),
            "architecture_rules_detected": len(architecture_rules),
            "governance_loaded": bool(governance_context),
            "execution_permissions": bool(standards and governance_context),
            "compatible": bool(systems and standards and architecture_rules),
        }

    def _visibility_payload(
        self,
        systems: tuple[dict[str, Any], ...],
        standards: tuple[dict[str, Any], ...],
        governance_context: dict[str, Any],
        compatibility: dict[str, Any],
        responsibilities: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            "systems_detected": [dict(system) for system in systems],
            "standards_applied": [dict(standard) for standard in standards],
            "governance_alignment": dict(governance_context),
            "architecture_consistency": compatibility.get("compatible", False),
            "execution_compatibility": dict(compatibility),
            "operational_responsibilities": list(responsibilities),
        }

    def _unauthorized_sources(
        self,
        request: AppsStandardsReaderRequest,
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

    def _title(self, content: str, path: Path) -> str:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip() or path.stem
        return path.stem

    def _haystack(self, document: dict[str, Any]) -> str:
        return (
            f"{document.get('relative_path', '')} "
            f"{document.get('title', '')} "
            f"{document.get('content', '')}"
        ).lower()

    def _error_result(
        self,
        read_id: str,
        request: AppsStandardsReaderRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> AppsStandardsReaderResult:
        finished_at = datetime.now(timezone.utc)
        return AppsStandardsReaderResult(
            status=APPS_STANDARDS_STATUS_ERROR,
            success=False,
            read_id=read_id,
            standards_sources=tuple(request.standards_sources),
            systems_detected=(),
            organizational_roles=(),
            technical_standards=(),
            architecture_rules=(),
            operational_responsibilities=(),
            governance_context=dict(request.governance_context),
            execution_compatibility={},
            standards_legitimacy_valid=False,
            architecture_compatibility_valid=False,
            governance_alignment_valid=False,
            execution_permissions_valid=False,
            ecosystem_consistency_valid=False,
            architecture_integrity_preserved=False,
            operational_continuity_preserved=False,
            execution_traceability_preserved=False,
            human_visibility_payload={},
            reader_lifecycle=(self._lifecycle(APPS_STANDARDS_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("apps_standards_reader_error_contained",),
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

    def _publish(self, result: AppsStandardsReaderResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_apps_standards_reader_result",
        ):
            self.status.mark_apps_standards_reader_result(result.to_dict())

    def _log_result(self, result: AppsStandardsReaderResult) -> None:
        if result.status == APPS_STANDARDS_STATUS_ERROR:
            logger.error(
                "apps_standards_reader: error read_id=%s error=%s",
                result.read_id,
                result.error,
            )
            return
        if result.status == APPS_STANDARDS_STATUS_BLOCKED:
            logger.warning(
                "apps_standards_reader: blocked read_id=%s reasons=%s",
                result.read_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "apps_standards_reader: interpreted read_id=%s systems=%s standards=%s",
            result.read_id,
            len(result.systems_detected),
            len(result.technical_standards),
        )
