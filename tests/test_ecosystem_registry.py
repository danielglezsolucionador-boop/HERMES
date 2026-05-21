from app.runner.ecosystem_registry import (
    EcosystemRegistry,
    EcosystemRegistryRequest,
    EcosystemSystem,
)
from app.services.runtime_status import RuntimeStatus


def test_ecosystem_registry_lists_official_systems_and_metrics():
    status = RuntimeStatus()
    registry = EcosystemRegistry(status=status)

    result = registry.snapshot()

    system_ids = {system["system_id"] for system in result.official_systems}
    assert result.status == "registered"
    assert result.success is True
    assert {"CEO", "CEREBRO", "HERMES", "FORJA", "VULCAN", "SENTINEL", "CENTINELA"} <= system_ids
    assert result.hierarchy_preserved is True
    assert result.governance_preserved is True

    metrics = status.ecosystem_registry_metrics()
    assert metrics["ecosystem_registry_status"] == "registered"
    assert metrics["ecosystem_registry_validated"] == 1
    assert metrics["official_systems_count"] == 7


def test_ecosystem_registry_validates_known_system_authority_scope():
    registry = EcosystemRegistry()

    result = registry.validate(
        EcosystemRegistryRequest(
            system_id="HERMES",
            action="technical_orchestration",
            responsibility_scope="technical_orchestration",
            requested_authority_level="technical_runtime",
        )
    )

    assert result.status == "validated"
    assert result.success is True
    assert result.system_id == "HERMES"
    assert result.authority_respected is True


def test_ecosystem_registry_blocks_authority_override_and_hierarchy_changes():
    registry = EcosystemRegistry()

    result = registry.validate(
        EcosystemRegistryRequest(
            system_id="HERMES",
            action="redefine_strategy",
            responsibility_scope="strategic_vision",
            requested_authority_level="strategic_final",
            authority_override_requested=True,
            alter_hierarchy_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "authority_override_blocked" in result.reasons
    assert "hierarchy_alteration_blocked" in result.reasons
    assert "authority_conflict_detected" in result.reasons
    assert result.authority_conflict_detected is True


def test_ecosystem_registry_respects_centinela_security_authority():
    registry = EcosystemRegistry()

    blocked = registry.validate(
        EcosystemRegistryRequest(system_id="HERMES", action="quarantine")
    )
    allowed = registry.validate(
        EcosystemRegistryRequest(system_id="CENTINELA", action="quarantine")
    )

    assert blocked.status == "blocked"
    assert "security_authority_required" in blocked.reasons
    assert allowed.status == "validated"
    assert allowed.security_escalation_respected is True


def test_ecosystem_registry_blocks_unregistered_system_creation_without_governance():
    registry = EcosystemRegistry()

    result = registry.validate(
        EcosystemRegistryRequest(
            action="register_future_system",
            create_unregistered_system=True,
            future_system={
                "system_id": "ATLAS",
                "system_type": "future_system",
            },
        )
    )

    assert result.status == "blocked"
    assert "unregistered_system_creation_blocked" in result.reasons
    assert "future_system_not_authorized" in result.reasons
    assert result.future_expansion_safe is False


def test_ecosystem_registry_allows_governed_future_system_proposal():
    registry = EcosystemRegistry()

    result = registry.register_future_system(
        EcosystemSystem(
            system_id="ATLAS",
            system_type="future_system",
            authority_level="operational_support",
            responsibility_scope=("support",),
        ),
        governance_status="approved",
    )

    assert result.status == "validated"
    assert result.success is True
    assert result.future_expansion_safe is True


def test_ecosystem_registry_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    registry = EcosystemRegistry(status=status)

    def broken_systems(*args, **kwargs):
        raise RuntimeError("registry lookup exploded")

    monkeypatch.setattr(registry, "get_system", broken_systems)

    result = registry.validate(EcosystemRegistryRequest(system_id="HERMES"))

    assert result.status == "error"
    assert result.success is False
    assert "ecosystem_registry_error_contained" in result.reasons
    assert status.ecosystem_registry_metrics()["ecosystem_registry_errors"] == 1
