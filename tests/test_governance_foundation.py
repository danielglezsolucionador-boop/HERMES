from app.runner.governance_foundation import (
    GovernanceFoundation,
    GovernanceFoundationRequest,
)
from app.services.runtime_status import RuntimeStatus


def test_governance_foundation_validates_ceo_execution_and_metrics():
    status = RuntimeStatus()
    governance = GovernanceFoundation(status=status)

    result = governance.validate(
        GovernanceFoundationRequest(
            authority_source="CEO",
            governance_type="execution",
            execution_context={"task_id": "task-1"},
            governance_status="approved",
            approval_required=True,
            approval_status="human_approved",
            security_status="clear",
        )
    )

    assert result.status == "validated"
    assert result.success is True
    assert result.authority_identified is True
    assert result.authority_legitimate is True
    assert result.human_authority_preserved is True
    assert result.approval_satisfied is True
    assert result.execution_permitted is True
    assert result.reporting_target == "CEO"

    metrics = status.governance_foundation_metrics()
    assert metrics["governance_foundation_status"] == "validated"
    assert metrics["governance_foundation_validated"] == 1
    assert metrics["authority_source"] == "CEO"
    assert "human_authority_is_final" in metrics["governance_rules"]


def test_governance_foundation_allows_hermes_technical_execution_scope():
    governance = GovernanceFoundation()

    result = governance.assess(
        GovernanceFoundationRequest(
            authority_source="HERMES",
            governance_type="continuation",
            execution_context={"workflow": "phase_5"},
            governance_status="approved",
            operational_status="active",
        )
    )

    assert result.status == "validated"
    assert result.success is True
    assert result.reporting_target == "CEREBRO"
    assert result.execution_limits_preserved is True


def test_governance_foundation_blocks_authority_override_and_autonomy():
    governance = GovernanceFoundation()

    result = governance.validate(
        GovernanceFoundationRequest(
            authority_source="HERMES",
            governance_type="approval",
            authority_override_requested=True,
            alter_authorities_requested=True,
            autonomy_expansion_requested=True,
        )
    )

    assert result.status == "blocked"
    assert result.success is False
    assert "authority_scope_not_allowed" in result.reasons
    assert "authority_override_blocked" in result.reasons
    assert "autonomy_expansion_blocked" in result.reasons
    assert result.human_authority_preserved is False
    assert result.execution_limits_preserved is False


def test_governance_foundation_blocks_missing_required_approval():
    governance = GovernanceFoundation()

    result = governance.validate(
        GovernanceFoundationRequest(
            authority_source="CEREBRO",
            governance_type="execution",
            approval_required=True,
            approval_status="pending",
        )
    )

    assert result.status == "blocked"
    assert "approval_required" in result.reasons
    assert result.approval_required is True
    assert result.approval_satisfied is False
    assert result.execution_permitted is False


def test_governance_foundation_preserves_security_blocking():
    governance = GovernanceFoundation()

    result = governance.validate(
        GovernanceFoundationRequest(
            authority_source="CENTINELA",
            governance_type="security",
            security_status="quarantine",
            blocking_status="critical_blocked",
            critical_blocking_active=True,
            risks=("critical execution blocked",),
        )
    )

    assert result.status == "blocked"
    assert "security_escalation_required" in result.reasons
    assert "blocking_condition_active" in result.reasons
    assert result.security_escalation_required is True
    assert result.blocking_active is True
    assert result.reporting_target == "CENTINELA"
    assert result.runtime_protected is True


def test_governance_foundation_blocks_dishonest_governance():
    governance = GovernanceFoundation()

    result = governance.validate(
        GovernanceFoundationRequest(
            authority_source="CEO",
            governance_type="ecosystem",
            conceal_conflicts_requested=True,
            minimize_risks_requested=True,
            falsify_approval_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "approval_integrity_violation" in result.reasons
    assert "dishonest_governance_blocked" in result.reasons
    assert result.governance_transparency_preserved is False
    assert result.human_authority_preserved is False


def test_governance_foundation_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    governance = GovernanceFoundation(status=status)

    def broken_registry(*args, **kwargs):
        raise RuntimeError("governance registry exploded")

    monkeypatch.setattr(governance.registry, "get_system", broken_registry)

    result = governance.validate(
        GovernanceFoundationRequest(authority_source="CEO")
    )

    assert result.status == "error"
    assert result.success is False
    assert "governance_foundation_error_contained" in result.reasons
    metrics = status.governance_foundation_metrics()
    assert metrics["governance_foundation_errors"] == 1
