from pathlib import Path

from app.runner.phases_roadmap_reader import (
    PhasesRoadmapReader,
    PhasesRoadmapReaderRequest,
)
from app.services.runtime_status import RuntimeStatus


def _write(path: Path, content: str = "# Phase\nroadmap phase") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _roadmap_root(tmp_path: Path) -> Path:
    root = tmp_path / "knowledge-core" / "phases"
    _write(root / "8.1_KNOWLEDGE_CORE_READER.md")
    _write(root / "8.2_PHASES_AND_ROADMAP_READER.md")
    _write(root / "8.3_APPS_AND_STANDARDS_READER.md")
    _write(root / "10.1_STRESS_TESTS.md")
    _write(root / "HERMES_PHASES.md", "# Hermes Phases\nphase roadmap")
    return root


def test_phases_roadmap_reader_interprets_order_and_metrics(tmp_path):
    root = _roadmap_root(tmp_path)
    status = RuntimeStatus()
    reader = PhasesRoadmapReader(status=status)

    result = reader.read(
        PhasesRoadmapReaderRequest(
            roadmap_sources=(str(root),),
            source_authorizations={str(root.resolve()): True},
            current_subphase="8.1_KNOWLEDGE_CORE_READER.md",
            completed_subphases=("8.1_KNOWLEDGE_CORE_READER.md",),
            governance_context={"authority": "CEREBRO"},
        )
    )

    assert result.status == "interpreted"
    assert result.success is True
    assert result.execution_order[:4] == (
        "8.1_KNOWLEDGE_CORE_READER.md",
        "8.2_PHASES_AND_ROADMAP_READER.md",
        "8.3_APPS_AND_STANDARDS_READER.md",
        "10.1_STRESS_TESTS.md",
    )
    assert result.priority_context["next_subphase"] == (
        "8.2_PHASES_AND_ROADMAP_READER.md"
    )
    assert result.continuation_status == "ready"
    assert result.roadmap_coherence_preserved is True
    assert result.dependency_integrity_valid is True

    metrics = status.phases_roadmap_reader_metrics()
    assert metrics["phases_roadmap_reader_status"] == "interpreted"
    assert metrics["phases_roadmap_reader_interpreted"] == 1
    assert metrics["phases_roadmap_reader_errors"] == 0


def test_phases_roadmap_reader_uses_knowledge_core_sources(tmp_path):
    root = _roadmap_root(tmp_path)
    reader = PhasesRoadmapReader()

    result = reader.interpret(
        PhasesRoadmapReaderRequest(
            knowledge_core={
                "source_roots": [str(root)],
                "governance_context": {"governance_loaded": True},
            },
            current_subphase="10.1_STRESS_TESTS.md",
        )
    )

    assert result.status == "interpreted"
    assert result.priority_context["next_subphase"] == "HERMES_PHASES.md"
    assert result.governance_alignment_valid is True


def test_phases_roadmap_reader_blocks_unauthorized_sources(tmp_path):
    root = _roadmap_root(tmp_path)
    reader = PhasesRoadmapReader()

    result = reader.read(
        PhasesRoadmapReaderRequest(
            roadmap_sources=(str(root),),
            source_authorizations={str(root.resolve()): False},
            governance_context={"authority": "CEREBRO"},
        )
    )

    assert result.status == "blocked"
    assert f"roadmap_source_unauthorized:{root.resolve()}" in result.reasons
    assert "phase_documentation_not_found" in result.reasons
    assert result.execution_order == ()


def test_phases_roadmap_reader_blocks_roadmap_override_requests(tmp_path):
    root = _roadmap_root(tmp_path)
    reader = PhasesRoadmapReader()

    result = reader.read(
        PhasesRoadmapReaderRequest(
            roadmap_sources=(str(root),),
            governance_context={"authority": "CEREBRO"},
            modify_roadmap_requested=True,
            invent_subphase_requested=True,
            alter_priorities_requested=True,
            ignore_dependencies_requested=True,
            overwrite_governance_planning_requested=True,
            hide_blocking_conditions_requested=True,
            minimize_governance_conflicts_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "roadmap_modification_blocked" in result.reasons
    assert "subphase_invention_blocked" in result.reasons
    assert "execution_priority_alteration_blocked" in result.reasons
    assert "roadmap_dependency_ignore_blocked" in result.reasons
    assert "governance_planning_overwrite_blocked" in result.reasons
    assert "roadmap_blocking_conditions_concealment_blocked" in result.reasons
    assert "roadmap_governance_conflict_minimization_blocked" in result.reasons


def test_phases_roadmap_reader_contains_internal_errors(monkeypatch, tmp_path):
    root = _roadmap_root(tmp_path)
    status = RuntimeStatus()
    reader = PhasesRoadmapReader(status=status)

    def broken_discovery(*args, **kwargs):
        raise RuntimeError("roadmap discovery exploded")

    monkeypatch.setattr(reader, "_discover_phase_files", broken_discovery)

    result = reader.read(
        PhasesRoadmapReaderRequest(
            roadmap_sources=(str(root),),
            governance_context={"authority": "CEREBRO"},
        )
    )

    assert result.status == "error"
    assert "phases_roadmap_reader_error_contained" in result.reasons

    metrics = status.phases_roadmap_reader_metrics()
    assert metrics["phases_roadmap_reader_status"] == "error"
    assert metrics["phases_roadmap_reader_errors"] == 1
