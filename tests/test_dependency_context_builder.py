from app.runner.dependency_context_builder import (
    DependencyContextBuilder,
    DependencyContextBuilderRequest,
)
from app.services.runtime_status import RuntimeStatus


def _base_request(**overrides):
    data = {
        "runtime_dependencies": ("postgres", "telegram"),
        "execution_relationships": (
            {"subphase": "8.4_DEPENDENCY_CONTEXT_BUILDER.md", "depends_on": ["8.3_APPS_AND_STANDARDS_READER.md"]},
        ),
        "architecture_context": {"runtime": "hermes"},
        "governance_context": {"authority": "CEREBRO"},
        "operational_relationships": ("dashboard",),
        "continuity_status": "ready",
    }
    data.update(overrides)
    return DependencyContextBuilderRequest(**data)


def test_dependency_context_builder_builds_context_and_metrics():
    status = RuntimeStatus()
    builder = DependencyContextBuilder(status=status)

    result = builder.build(_base_request())

    assert result.status == "built"
    assert result.success is True
    assert result.dependency_integrity_valid is True
    assert result.runtime_compatibility_valid is True
    assert result.governance_alignment_valid is True
    assert result.architecture_consistency_valid is True
    assert result.operational_continuity_valid is True
    assert result.runtime_integrity_preserved is True

    metrics = status.dependency_context_builder_metrics()
    assert metrics["dependency_context_builder_status"] == "built"
    assert metrics["dependency_context_builder_built"] == 1
    assert metrics["dependency_context_builder_errors"] == 0


def test_dependency_context_builder_uses_reader_contexts():
    builder = DependencyContextBuilder()

    result = builder.construct(
        DependencyContextBuilderRequest(
            knowledge_core={
                "dependency_context": {"sources": ["runtime/TASK_RUNNER.md"]},
                "execution_context": {"component": "runtime"},
                "governance_context": {"knowledge": True},
            },
            phases_roadmap={
                "dependency_relationships": [
                    {
                        "subphase": "8.4_DEPENDENCY_CONTEXT_BUILDER.md",
                        "depends_on": ["8.3_APPS_AND_STANDARDS_READER.md"],
                    }
                ],
                "governance_context": {"roadmap": True},
                "continuation_status": "ready",
            },
            apps_standards={
                "systems_detected": [{"name": "Hermes"}],
                "architecture_rules": ["runtime compatibility"],
                "governance_context": {"apps": True},
            },
        )
    )

    assert result.status == "built"
    assert result.runtime_dependencies
    assert result.execution_relationships
    assert result.operational_relationships
    assert result.governance_context["knowledge"] is True
    assert result.governance_context["roadmap"] is True
    assert result.governance_context["apps"] is True


def test_dependency_context_builder_blocks_missing_required_context():
    builder = DependencyContextBuilder()

    result = builder.build(DependencyContextBuilderRequest())

    assert result.status == "blocked"
    assert "runtime_dependencies_required" in result.reasons
    assert "execution_relationships_required" in result.reasons
    assert "architecture_context_required" in result.reasons
    assert "governance_context_required" in result.reasons
    assert "operational_relationships_required" in result.reasons
    assert "runtime_compatibility_required" in result.reasons
    assert "operational_continuity_blocked" in result.reasons


def test_dependency_context_builder_blocks_dependency_override_requests():
    builder = DependencyContextBuilder()

    result = builder.build(
        _base_request(
            alter_dependency_structures_requested=True,
            break_execution_compatibility_requested=True,
            ignore_critical_dependencies_requested=True,
            overwrite_architecture_relationships_requested=True,
            modify_governance_dependencies_requested=True,
            minimize_dependency_impact_requested=True,
            hide_runtime_relationships_requested=True,
            ignore_execution_conflicts_requested=True,
            alter_dependency_history_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "dependency_structure_alteration_blocked" in result.reasons
    assert "execution_compatibility_break_blocked" in result.reasons
    assert "critical_dependency_ignore_blocked" in result.reasons
    assert "architecture_dependency_overwrite_blocked" in result.reasons
    assert "governance_dependency_modification_blocked" in result.reasons
    assert "dependency_impact_minimization_blocked" in result.reasons
    assert "runtime_relationship_concealment_blocked" in result.reasons
    assert "execution_conflict_ignore_blocked" in result.reasons
    assert "dependency_history_alteration_blocked" in result.reasons


def test_dependency_context_builder_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    builder = DependencyContextBuilder(status=status)

    def broken_dependencies(*args, **kwargs):
        raise RuntimeError("dependency discovery exploded")

    monkeypatch.setattr(builder, "_runtime_dependencies", broken_dependencies)

    result = builder.build(_base_request())

    assert result.status == "error"
    assert "dependency_context_builder_error_contained" in result.reasons

    metrics = status.dependency_context_builder_metrics()
    assert metrics["dependency_context_builder_status"] == "error"
    assert metrics["dependency_context_builder_errors"] == 1
