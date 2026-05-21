from pathlib import Path

from app.runner.apps_standards_reader import (
    AppsStandardsReader,
    AppsStandardsReaderRequest,
)
from app.services.runtime_status import RuntimeStatus


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _standards_root(tmp_path: Path) -> Path:
    root = tmp_path / "knowledge-core"
    _write(
        root / "ecosystem" / "ECOSYSTEM_REGISTRY.md",
        "# Ecosystem Registry\nHermes application system agent responsibilities owner authority CEREBRO.",
    )
    _write(
        root / "rules" / "OPERATIONAL_RULES.md",
        "# Operational Standards\ntechnical standard rule protocol validation architecture runtime compatibility.",
    )
    _write(
        root / "agents" / "AGENT_REGISTRY.md",
        "# Agent Roles\nVULCAN SENTINEL CENTINELA CEO authority responsibility system.",
    )
    _write(
        root / "governance" / "VALIDATION_SYSTEM.md",
        "# Governance\napproval authority governance validation system.",
    )
    return root


def test_apps_standards_reader_interprets_systems_and_metrics(tmp_path):
    root = _standards_root(tmp_path)
    status = RuntimeStatus()
    reader = AppsStandardsReader(status=status)

    result = reader.read(
        AppsStandardsReaderRequest(
            standards_sources=(str(root),),
            source_authorizations={str(root.resolve()): True},
        )
    )

    assert result.status == "interpreted"
    assert result.success is True
    assert result.systems_detected
    assert "CEREBRO" in result.organizational_roles
    assert result.technical_standards
    assert result.architecture_rules
    assert result.operational_responsibilities
    assert result.governance_alignment_valid is True
    assert result.execution_permissions_valid is True
    assert result.architecture_integrity_preserved is True

    metrics = status.apps_standards_reader_metrics()
    assert metrics["apps_standards_reader_status"] == "interpreted"
    assert metrics["apps_standards_reader_interpreted"] == 1
    assert metrics["apps_standards_reader_errors"] == 0


def test_apps_standards_reader_uses_knowledge_core_sources(tmp_path):
    root = _standards_root(tmp_path)
    reader = AppsStandardsReader()

    result = reader.interpret(
        AppsStandardsReaderRequest(
            knowledge_core={
                "source_roots": [str(root)],
                "governance_context": {"authority": "CEREBRO"},
            }
        )
    )

    assert result.status == "interpreted"
    assert result.execution_compatibility["compatible"] is True
    assert result.governance_context["authority"] == "CEREBRO"


def test_apps_standards_reader_blocks_unauthorized_sources(tmp_path):
    root = _standards_root(tmp_path)
    reader = AppsStandardsReader()

    result = reader.read(
        AppsStandardsReaderRequest(
            standards_sources=(str(root),),
            source_authorizations={str(root.resolve()): False},
        )
    )

    assert result.status == "blocked"
    assert f"standards_source_unauthorized:{root.resolve()}" in result.reasons
    assert "standards_documents_not_found" in result.reasons
    assert "ecosystem_applications_not_found" in result.reasons


def test_apps_standards_reader_blocks_standards_override_requests(tmp_path):
    root = _standards_root(tmp_path)
    reader = AppsStandardsReader()

    result = reader.read(
        AppsStandardsReaderRequest(
            standards_sources=(str(root),),
            redefine_standards_requested=True,
            alter_responsibilities_requested=True,
            invent_architecture_rules_requested=True,
            modify_governance_structures_requested=True,
            overwrite_ecosystem_consistency_requested=True,
            invent_execution_permissions_requested=True,
            ignore_authority_boundaries_requested=True,
            minimize_governance_conflicts_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "standards_override_blocked" in result.reasons
    assert "responsibilities_alteration_blocked" in result.reasons
    assert "architecture_rule_invention_blocked" in result.reasons
    assert "governance_structure_modification_blocked" in result.reasons
    assert "ecosystem_consistency_overwrite_blocked" in result.reasons
    assert "execution_permission_invention_blocked" in result.reasons
    assert "authority_boundary_ignore_blocked" in result.reasons
    assert "governance_conflict_minimization_blocked" in result.reasons


def test_apps_standards_reader_contains_internal_errors(monkeypatch, tmp_path):
    root = _standards_root(tmp_path)
    status = RuntimeStatus()
    reader = AppsStandardsReader(status=status)

    def broken_read(*args, **kwargs):
        raise RuntimeError("standards read exploded")

    monkeypatch.setattr(reader, "_read_documents", broken_read)

    result = reader.read(AppsStandardsReaderRequest(standards_sources=(str(root),)))

    assert result.status == "error"
    assert "apps_standards_reader_error_contained" in result.reasons

    metrics = status.apps_standards_reader_metrics()
    assert metrics["apps_standards_reader_status"] == "error"
    assert metrics["apps_standards_reader_errors"] == 1
