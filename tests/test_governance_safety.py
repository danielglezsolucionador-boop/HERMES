from app.runner.execution_blocking import ExecutionBlockRequest, ExecutionBlocking
from app.runner.governance_escalation import (
    GovernanceEscalation,
    GovernanceEscalationRequest,
)
from app.runner.governance_safety import GovernanceSafety, GovernanceSafetyRequest
from app.services.runtime_status import RuntimeStatus


def test_governance_safety_allows_approved_governance_and_metrics():
    status = RuntimeStatus()
    safety = GovernanceSafety(status=status)

    result = safety.validate(
        GovernanceSafetyRequest(
            safety_type="governance",
            execution_id="execution-safe",
            authority_source="CEO",
            execution_context={"execution_id": "execution-safe"},
            authority_status="final",
            governance_status="approved",
            approval_status="approved",
            audit_status="approved",
            security_status="clear",
            runtime_status="online",
            continuation_status="ready",
        )
    )

    assert result.status == "safe"
    assert result.success is True
    assert result.execution_allowed is True
    assert result.human_authority_preserved is True
    assert result.governance_integrity_preserved is True
    assert result.audit_respected is True
    assert result.security_respected is True
    assert result.traceability_preserved is True

    metrics = status.governance_safety_metrics()
    assert metrics["governance_safety_status"] == "safe"
    assert metrics["governance_safety_safe"] == 1
    assert metrics["execution_allowed"] is True


def test_governance_safety_blocks_authority_override_and_autonomy():
    safety = GovernanceSafety()

    result = safety.validate(
        GovernanceSafetyRequest(
            safety_type="human_authority",
            execution_id="execution-authority",
            authority_source="HERMES",
            governance_status="approved",
            runtime_status="online",
            authority_override_requested=True,
            alter_authorities_requested=True,
            autonomy_expansion_requested=True,
            governance_redefinition_requested=True,
            conceal_conflicts_requested=True,
        )
    )

    assert result.status == "blocked"
    assert result.success is False
    assert result.execution_allowed is False
    assert result.human_authority_risk_detected is True
    assert result.governance_risk_detected is True
    assert result.human_authority_preserved is False
    assert result.autonomy_limited is False
    assert "human_authority_preserved" in result.reasons
    assert "governance_integrity_required" in result.reasons
    assert "honest_governance_required" in result.reasons


def test_governance_safety_respects_security_escalation_and_blocking():
    block = ExecutionBlocking().activate(
        ExecutionBlockRequest(
            execution_id="execution-security-safety",
            security_status="critical",
            runtime_state={"status": "online"},
        )
    )
    escalation = GovernanceEscalation().escalate(
        GovernanceEscalationRequest(execution_block=block)
    )
    safety = GovernanceSafety()

    result = safety.validate(
        GovernanceSafetyRequest(
            safety_type="security",
            governance_escalation=escalation,
            execution_blocking=block,
        )
    )

    assert result.status == "blocked"
    assert result.security_risk_detected is True
    assert result.execution_risk_detected is True
    assert result.continuation_risk_detected is True
    assert result.reporting_authority == "CENTINELA"
    assert result.escalation_required is True
    assert "security_authority_required" in result.reasons
    assert "critical_blocking_preserved" in result.reasons


def test_governance_safety_blocks_audit_invalidation_and_continuation_override():
    safety = GovernanceSafety()

    result = safety.validate(
        GovernanceSafetyRequest(
            safety_type="audit",
            execution_id="execution-audit-safety",
            audit_status="rejected",
            runtime_status="online",
            invalidate_audit_requested=True,
            continuation_override_requested=True,
        )
    )

    assert result.status == "blocked"
    assert result.audit_risk_detected is True
    assert result.continuation_risk_detected is True
    assert result.audit_respected is False
    assert "audit_authority_required" in result.reasons
    assert "continuation_safety_required" in result.reasons


def test_governance_safety_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    safety = GovernanceSafety(status=status)

    def broken_statuses(*args, **kwargs):
        raise RuntimeError("governance safety exploded")

    monkeypatch.setattr(safety, "_statuses", broken_statuses)

    result = safety.validate(
        GovernanceSafetyRequest(
            safety_type="governance",
            execution_id="execution-error",
        )
    )

    assert result.status == "error"
    assert result.success is False
    assert "governance_safety_error_contained" in result.reasons
    metrics = status.governance_safety_metrics()
    assert metrics["governance_safety_errors"] == 1
