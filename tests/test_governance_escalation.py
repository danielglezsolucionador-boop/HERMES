from app.runner.approval_system import ApprovalSystem, ApprovalSystemRequest
from app.runner.execution_blocking import ExecutionBlockRequest, ExecutionBlocking
from app.runner.governance_escalation import (
    GovernanceEscalation,
    GovernanceEscalationRequest,
)
from app.runner.governance_foundation import (
    GovernanceFoundation,
    GovernanceFoundationRequest,
)
from app.services.runtime_status import RuntimeStatus


def test_governance_escalation_reports_security_block_to_centinela():
    status = RuntimeStatus()
    block = ExecutionBlocking().activate(
        ExecutionBlockRequest(
            execution_id="execution-security",
            security_status="critical",
            runtime_state={"status": "online"},
        )
    )
    escalation = GovernanceEscalation(status=status)

    result = escalation.escalate(
        GovernanceEscalationRequest(execution_block=block)
    )

    assert result.status == "escalated"
    assert result.success is True
    assert result.escalation_type == "security"
    assert result.reporting_authority == "CENTINELA"
    assert result.security_escalation_detected is True
    assert result.blocking_preserved is True
    assert result.no_self_resolution is True
    assert result.honest_reporting_preserved is True

    metrics = status.governance_escalation_metrics()
    assert metrics["governance_escalation_status"] == "escalated"
    assert metrics["governance_escalations_active"] == 1
    assert metrics["escalation_type"] == "security"


def test_governance_escalation_reports_missing_approval_to_ceo():
    approval = ApprovalSystem().validate(
        ApprovalSystemRequest(
            authority_source="CEREBRO",
            execution_id="execution-approval-escalation",
            architecture_change=True,
            governance_status="approved",
        )
    )
    escalation = GovernanceEscalation()

    result = escalation.escalate(
        GovernanceEscalationRequest(approval_system=approval)
    )

    assert result.status == "escalated"
    assert result.escalation_type == "approval"
    assert result.reporting_authority == "CEO"
    assert result.approval_failure_detected is True
    assert result.risk_level == "elevated"
    assert result.execution_id == "execution-approval-escalation"


def test_governance_escalation_preserves_governance_conflict_context():
    governance = GovernanceFoundation().validate(
        GovernanceFoundationRequest(
            authority_source="HERMES",
            governance_type="approval",
            execution_context={"execution_id": "execution-governance-escalation"},
            approval_required=True,
            approval_status="pending",
        )
    )
    escalation = GovernanceEscalation()

    result = escalation.escalate(
        GovernanceEscalationRequest(governance_foundation=governance)
    )

    assert result.status == "escalated"
    assert result.escalation_type == "governance"
    assert result.reporting_authority == "CEO"
    assert result.governance_conflict_detected is True
    assert result.context_preserved is True
    assert result.traceability_preserved is True


def test_governance_escalation_blocks_invalid_or_unsafe_escalation_request():
    escalation = GovernanceEscalation()

    result = escalation.escalate(
        GovernanceEscalationRequest(
            escalation_type="unknown",
            self_resolution_requested=True,
            ignore_escalation_requested=True,
            invalidate_blocking_requested=True,
        )
    )

    assert result.status == "blocked"
    assert result.success is False
    assert "unsupported_escalation_type" in result.reasons
    assert "missing_execution_id" in result.reasons
    assert "self_resolution_blocked" in result.reasons
    assert "critical_blocking_preserved" in result.reasons
    assert "dishonest_escalation_reporting_blocked" in result.reasons
    assert result.no_self_resolution is False
    assert result.blocking_preserved is False


def test_governance_escalation_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    escalation = GovernanceEscalation(status=status)

    def broken_reason(*args, **kwargs):
        raise RuntimeError("escalation reason exploded")

    monkeypatch.setattr(escalation, "_escalation_reason", broken_reason)

    result = escalation.escalate(
        GovernanceEscalationRequest(
            escalation_type="governance",
            execution_id="execution-error",
        )
    )

    assert result.status == "error"
    assert result.success is False
    assert "governance_escalation_error_contained" in result.reasons
    metrics = status.governance_escalation_metrics()
    assert metrics["governance_escalation_errors"] == 1
