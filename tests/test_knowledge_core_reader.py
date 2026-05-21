from pathlib import Path

from app.runner.knowledge_core_reader import (
    REQUIRED_COMPONENTS,
    KnowledgeCoreReader,
    KnowledgeCoreReaderRequest,
)
from app.services.runtime_status import RuntimeStatus


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _knowledge_root(tmp_path: Path) -> Path:
    root = tmp_path / "knowledge-core"
    _write(root / "phases" / "PHASE_SYSTEM.md", "# Phase\nphase subphase")
    _write(
        root / "phases" / "ROADMAP.md",
        "# Roadmap\nroadmap workflow pipeline",
    )
    _write(
        root / "rules" / "OPERATIONAL_RULES.md",
        "# Technical Standards\nstandard validation protocol",
    )
    _write(
        root / "ecosystem" / "ECOSYSTEM_REGISTRY.md",
        "# Ecosystem\nagent registry ecosystem",
    )
    _write(
        root / "memory" / "OPERATIONAL_MEMORY.md",
        "# Execution History\nmemory execution history",
    )
    _write(
        root / "runtime" / "TASK_RUNNER.md",
        "# Dependency Context\nruntime dependency task runner",
    )
    _write(
        root / "governance" / "VALIDATION_SYSTEM.md",
        "# Governance\napproval authority governance",
    )
    return root


def test_knowledge_core_reader_loads_authorized_sources_and_metrics(tmp_path):
    root = _knowledge_root(tmp_path)
    status = RuntimeStatus()
    reader = KnowledgeCoreReader(status=status)

    result = reader.read(
        KnowledgeCoreReaderRequest(
            source_roots=(str(root),),
            source_authorizations={str(root.resolve()): True},
            current_workflow="8.1_KNOWLEDGE_CORE_READER.md",
        )
    )

    assert result.status == "loaded"
    assert result.success is True
    assert result.documents_read == 7
    assert result.source_legitimacy_valid is True
    assert result.read_only_preserved is True
    for component in REQUIRED_COMPONENTS:
        assert result.components_found[component] is True

    metrics = status.knowledge_core_reader_metrics()
    assert metrics["knowledge_core_reader_status"] == "loaded"
    assert metrics["knowledge_core_reader_loaded"] == 1
    assert metrics["knowledge_core_reader_errors"] == 0
    assert metrics["documents_read"] == 7


def test_knowledge_core_reader_blocks_unauthorized_sources_without_reading(tmp_path):
    root = _knowledge_root(tmp_path)
    reader = KnowledgeCoreReader()

    result = reader.load(
        KnowledgeCoreReaderRequest(
            source_roots=(str(root),),
            source_authorizations={str(root.resolve()): False},
            modify_documentation_requested=True,
            alter_roadmap_requested=True,
            overwrite_governance_context_requested=True,
        )
    )

    assert result.status == "blocked"
    assert result.documents_read == 0
    assert f"knowledge_source_unauthorized:{root.resolve()}" in result.reasons
    assert "knowledge_sources_not_found" in result.reasons
    assert "knowledge_documentation_modification_blocked" in result.reasons
    assert "knowledge_roadmap_alteration_blocked" in result.reasons
    assert "governance_context_overwrite_blocked" in result.reasons


def test_knowledge_core_reader_blocks_missing_required_components(tmp_path):
    root = tmp_path / "knowledge-core"
    _write(root / "phases" / "PHASE_SYSTEM.md", "# Phase\nphase subphase")
    reader = KnowledgeCoreReader()

    result = reader.read(KnowledgeCoreReaderRequest(source_roots=(str(root),)))

    assert result.status == "blocked"
    assert "missing_knowledge_component:roadmap_context" in result.reasons
    assert "missing_knowledge_component:governance_context" in result.reasons


def test_knowledge_core_reader_blocks_context_invention_and_minimization(tmp_path):
    root = _knowledge_root(tmp_path)
    reader = KnowledgeCoreReader()

    result = reader.read(
        KnowledgeCoreReaderRequest(
            source_roots=(str(root),),
            invent_context_requested=True,
            ignore_critical_dependencies_requested=True,
            minimize_governance_conflicts_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "knowledge_context_invention_blocked" in result.reasons
    assert "critical_dependency_ignored_blocked" in result.reasons
    assert "governance_conflict_minimization_blocked" in result.reasons


def test_knowledge_core_reader_contains_internal_errors(monkeypatch, tmp_path):
    root = _knowledge_root(tmp_path)
    status = RuntimeStatus()
    reader = KnowledgeCoreReader(status=status)

    def broken_discovery(*args, **kwargs):
        raise RuntimeError("knowledge discovery exploded")

    monkeypatch.setattr(reader, "_discover_sources", broken_discovery)

    result = reader.read(KnowledgeCoreReaderRequest(source_roots=(str(root),)))

    assert result.status == "error"
    assert "knowledge_core_reader_error_contained" in result.reasons

    metrics = status.knowledge_core_reader_metrics()
    assert metrics["knowledge_core_reader_status"] == "error"
    assert metrics["knowledge_core_reader_errors"] == 1
