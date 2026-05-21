from app.runner.approval_gate import ApprovalGate, ApprovalGateRequest, HumanDecisionInput
from app.runner.approval_system import ApprovalSystem, ApprovalSystemRequest
from app.runner.audit_response_control import (
    AuditResponseControl,
    AuditResponseInput,
)
from app.runner.audit_request_system import AuditRequestInput, AuditRequestSystem
from app.runner.self_validation import SelfValidation, SelfValidationRequest
from app.services.runtime_status import RuntimeStatus


def _approved_gate_record():
    validation = SelfValidation().validate(
        SelfValidationRequest(
            execution_id="execution-gate-1",
            task_id="task-gate-1",
            outputs=("Gate ready.",),
            modified_files=("app/runner/approval_system.py",),
            runtime_state={"status": "online", "loop_state": "active"},
        )
    )
    audit_request = AuditRequestSystem().request(
        AuditRequestInput(
            validation_result=validation,
            execution_summary="Approval system ready.",
            runtime_state={"status": "online", "loop_state": "active"},
        )
    )
    audit_response = AuditResponseControl().process(
        AuditResponseInput(
            audit_request=audit_request,
            audit_result="approved",
            risk_level="clear",
        )
    )
    pending = ApprovalGate().request(
        ApprovalGateRequest(
            audit_response=audit_response,
            approval_type="continuation",
            execution_summary="Ready for approval.",
        )
    )
    return ApprovalGate().decide(
        HumanDecisionInput(
            approval_request=pending,
            human_decision="approve",
            decided_by="CEO",
        )
    )


def test_approval_system_validates_ceo_critical_approval_and_metrics():
    status = RuntimeStatus()
    approvals = ApprovalSystem(status=status)

    result = approvals.validate(
        ApprovalSystemRequest(
            approval_id="approval-1",
            authority_source="CEO",
            approval_type="ceo",
            approval_status="approved",
            workflow_id="phase-5",
            execution_id="execution-1",
            critical_workflow=True,
            architecture_change=True,
            governance_status="approved",
            security_status="clear",
        )
    )

    assert result.status == "approved"
    assert result.success is True
    assert result.required_approval_type == "ceo"
    assert result.execution_permitted is True
    assert result.human_authority_preserved is True
    assert result.no_self_approval is True
    assert result.governance_compatible is True

    metrics = status.approval_system_metrics()
    assert metrics["approval_system_status"] == "approved"
    assert metrics["approval_system_approved"] == 1
    assert metrics["authority_source"] == "CEO"


def test_approval_system_accepts_conditional_cerebro_approval_with_restrictions():
    approvals = ApprovalSystem()

    result = approvals.validate(
        ApprovalSystemRequest(
            approval_id="approval-2",
            authority_source="CEREBRO",
            approval_type="cerebro",
            approval_status="conditional_approval",
            workflow_id="continuation-1",
            continuation_requested=True,
            governance_status="approved",
            approval_restrictions=("continue only after audit visibility",),
        )
    )

    assert result.status == "conditional_approval"
    assert result.success is True
    assert result.conditional_approval is True
    assert result.execution_permitted is True
    assert result.approval_restrictions == (
        "continue only after audit visibility",
    )


def test_approval_system_escalates_missing_ceo_approval_for_architecture():
    approvals = ApprovalSystem()

    result = approvals.validate(
        ApprovalSystemRequest(
            authority_source="CEREBRO",
            architecture_change=True,
            governance_status="approved",
        )
    )

    assert result.status == "escalation_required"
    assert result.success is False
    assert result.required_approval_type == "ceo"
    assert "approval_missing" in result.reasons
    assert "approval_status_missing" in result.reasons
    assert "approval_authority_insufficient" in result.reasons
    assert result.escalation_required is True


def test_approval_system_blocks_self_and_fake_approval():
    approvals = ApprovalSystem()

    result = approvals.validate(
        ApprovalSystemRequest(
            approval_id="approval-3",
            authority_source="HERMES",
            approval_type="cerebro",
            approval_status="approved",
            self_approval_requested=True,
            create_fake_approval_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "self_approval_blocked" in result.reasons
    assert "approval_integrity_violation" in result.reasons
    assert result.no_self_approval is False
    assert result.human_authority_preserved is False


def test_approval_system_preserves_rejected_approval():
    approvals = ApprovalSystem()

    result = approvals.validate(
        ApprovalSystemRequest(
            approval_id="approval-4",
            authority_source="CEO",
            approval_type="cerebro",
            approval_status="rejected",
            ignore_rejection_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "approval_rejected" in result.reasons
    assert "valid_rejection_preserved" in result.reasons
    assert result.execution_permitted is False


def test_approval_system_validates_audit_and_security_authorities():
    approvals = ApprovalSystem()

    audit = approvals.validate(
        ApprovalSystemRequest(
            approval_id="approval-audit",
            authority_source="SENTINEL",
            approval_type="audit",
            approval_status="approved",
            audit_required=True,
            audit_status="approved",
        )
    )
    security = approvals.validate(
        ApprovalSystemRequest(
            approval_id="approval-security",
            authority_source="CENTINELA",
            approval_type="security",
            approval_status="approved",
            security_sensitive=True,
            security_status="clear",
        )
    )

    assert audit.status == "approved"
    assert audit.audit_permission_valid is True
    assert security.status == "approved"
    assert security.security_permission_valid is True


def test_approval_system_accepts_approved_gate_result_as_record():
    approvals = ApprovalSystem()
    gate_result = _approved_gate_record()

    result = approvals.validate(
        ApprovalSystemRequest(
            approval_record=gate_result,
            approval_type="cerebro",
            governance_status="approved",
            continuation_requested=True,
        )
    )

    assert result.status == "approved"
    assert result.success is True
    assert result.approval_exists is True
    assert result.authority_source == "CEO"
    assert result.execution_id == "execution-gate-1"


def test_approval_system_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    approvals = ApprovalSystem(status=status)

    def broken_registry(*args, **kwargs):
        raise RuntimeError("approval registry exploded")

    monkeypatch.setattr(approvals.registry, "get_system", broken_registry)

    result = approvals.validate(
        ApprovalSystemRequest(
            approval_id="approval-5",
            authority_source="CEO",
            approval_type="ceo",
            approval_status="approved",
        )
    )

    assert result.status == "error"
    assert result.success is False
    assert "approval_system_error_contained" in result.reasons
    metrics = status.approval_system_metrics()
    assert metrics["approval_system_errors"] == 1
