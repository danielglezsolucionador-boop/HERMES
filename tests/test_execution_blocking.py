from app.runner.approval_gate import ApprovalGate, ApprovalGateRequest
from app.runner.approval_system import ApprovalSystem, ApprovalSystemRequest
from app.runner.audit_request_system import AuditRequestInput, AuditRequestSystem
from app.runner.audit_response_control import (
    AuditResponseControl,
    AuditResponseInput,
)
from app.runner.execution_blocking import ExecutionBlockRequest, ExecutionBlocking
from app.runner.governance_foundation import (
    GovernanceFoundation,
    GovernanceFoundationRequest,
)
from app.runner.self_validation import SelfValidation, SelfValidationRequest
from app.services.runtime_status import RuntimeStatus


def _audit_response_result(
    audit_result="approved",
    risk_level="clear",
    detected_risks=(),
    rejection_reasons=(),
    risk_notes=(),
):
    validation = SelfValidation().validate(
        SelfValidationRequest(
            execution_id="execution-1",
            task_id="task-1",
            outputs=("Evaluated execution blocking.",),
            modified_files=("app/runner/execution_blocking.py",),
            runtime_state={"status": "online", "loop_state": "active"},
            risk_notes=risk_notes,
        )
    )
    audit_request = AuditRequestSystem().request(
        AuditRequestInput(
            validation_result=validation,
            execution_summary="Execution blocking implementation complete.",
            runtime_state={"status": "online", "loop_state": "active"},
        )
    )
    return AuditResponseControl().process(
        AuditResponseInput(
            audit_request=audit_request,
            audit_result=audit_result,
            risk_level=risk_level,
            detected_risks=detected_risks,
            rejection_reasons=rejection_reasons,
        )
    )


def test_execution_blocking_activates_audit_block_for_rejection():
    status = RuntimeStatus()
    audit_response = _audit_response_result(
        audit_result="rejected",
        risk_level="critical",
        rejection_reasons=("audit rejected unsafe execution",),
    )
    blocking = ExecutionBlocking(status=status)

    result = blocking.activate(
        ExecutionBlockRequest(
            audit_response=audit_response,
            runtime_logs=({"event": "audit_rejected"},),
            execution_context={"phase": "5.3.5"},
        )
    )

    assert result.status == "active"
    assert result.success is True
    assert result.block_type == "audit"
    assert result.block_classification == "critical_block"
    assert result.continuation_status == "blocked_critical"
    assert result.execution_frozen is True
    assert result.continuation_blocked is True
    assert result.human_authority_required is True
    assert result.context_preserved is True
    assert "audit_blocking_active" in result.reasons

    metrics = status.execution_blocking_metrics()
    assert metrics["execution_blocking_status"] == "active"
    assert metrics["execution_blocks_active"] == 1
    assert metrics["block_type"] == "audit"


def test_execution_blocking_escalates_security_block_to_centinela():
    audit_response = _audit_response_result(
        audit_result="rejected",
        risk_level="critical",
        detected_risks=("credential leak",),
        rejection_reasons=("security credential leak detected",),
        risk_notes=("security credential exposure",),
    )
    blocking = ExecutionBlocking()

    result = blocking.activate(ExecutionBlockRequest(audit_response=audit_response))

    assert result.status == "active"
    assert result.block_type == "security"
    assert result.block_classification == "security_block"
    assert result.escalation_status == "escalated_to_centinela"
    assert result.continuation_status == "blocked_security_authority"
    assert result.security_authority_required is True
    assert result.human_authority_required is True


def test_execution_blocking_activates_governance_block_for_pending_approval():
    audit_response = _audit_response_result()
    approval = ApprovalGate().request(
        ApprovalGateRequest(
            audit_response=audit_response,
            execution_summary="Waiting human approval.",
        )
    )
    blocking = ExecutionBlocking()

    result = blocking.activate(ExecutionBlockRequest(approval_gate=approval))

    assert result.status == "active"
    assert result.block_type == "governance"
    assert result.block_classification == "governance_block"
    assert result.escalation_status == "waiting_human_approval"
    assert result.continuation_status == "blocked_governance_authority"
    assert result.human_authority_required is True


def test_execution_blocking_activates_approval_block_from_approval_system():
    status = RuntimeStatus()
    approval = ApprovalSystem().validate(
        ApprovalSystemRequest(
            authority_source="CEREBRO",
            execution_id="execution-approval",
            architecture_change=True,
            governance_status="approved",
        )
    )
    blocking = ExecutionBlocking(status=status)

    result = blocking.activate(ExecutionBlockRequest(approval_system=approval))

    assert result.status == "active"
    assert result.block_type == "approval"
    assert result.block_classification == "governance_block"
    assert result.escalation_status == "approval_escalation_required"
    assert result.continuation_status == "blocked_approval_authority"
    assert result.approval_missing_detected is True
    assert result.block_preserved is True

    metrics = status.execution_blocking_metrics()
    assert metrics["block_type"] == "approval"
    assert metrics["approval_missing_detected"] is True
    assert metrics["block_preserved"] is True


def test_execution_blocking_activates_governance_block_from_foundation():
    governance = GovernanceFoundation().validate(
        GovernanceFoundationRequest(
            authority_source="HERMES",
            governance_type="approval",
            execution_context={"execution_id": "execution-governance"},
            approval_required=True,
            approval_status="pending",
        )
    )
    blocking = ExecutionBlocking()

    result = blocking.activate(
        ExecutionBlockRequest(governance_foundation=governance)
    )

    assert result.status == "active"
    assert result.block_type == "governance"
    assert result.block_classification == "governance_block"
    assert result.governance_conflict_detected is True
    assert result.context_preserved is True


def test_execution_blocking_blocks_unsafe_continuation_and_preserves_block():
    blocking = ExecutionBlocking()

    result = blocking.activate(
        ExecutionBlockRequest(
            execution_id="execution-continuation",
            continuation_status="unsafe",
            override_block_requested=True,
            minimize_risk_requested=True,
        )
    )

    assert result.status == "active"
    assert result.block_type == "continuation"
    assert result.continuation_status == "blocked_unsafe_continuation"
    assert result.continuation_unsafe_detected is True
    assert result.block_preserved is False


def test_execution_blocking_activates_temporary_provider_block():
    blocking = ExecutionBlocking()

    result = blocking.activate(
        ExecutionBlockRequest(
            execution_id="execution-1",
            provider_context={"status": "failed", "error": "timeout"},
        )
    )

    assert result.status == "active"
    assert result.block_type == "provider"
    assert result.block_classification == "temporary_block"
    assert result.risk_level == "elevated"
    assert result.continuation_status == "blocked_temporary"
    assert result.human_authority_required is False


def test_execution_blocking_blocks_invalid_activation():
    blocking = ExecutionBlocking()

    result = blocking.activate(ExecutionBlockRequest(block_type="audit"))

    assert result.status == "blocked"
    assert result.success is False
    assert result.continuation_status == "blocked_invalid_execution_block"
    assert "missing_execution_id" in result.reasons
    assert "missing_risk_level" in result.reasons


def test_execution_blocking_contains_internal_errors(monkeypatch):
    blocking = ExecutionBlocking()

    def broken_reason(*args, **kwargs):
        raise RuntimeError("blocking reason exploded")

    monkeypatch.setattr(blocking, "_block_reason", broken_reason)

    result = blocking.activate(
        ExecutionBlockRequest(
            execution_id="execution-1",
            block_type="human",
            risk_level="critical",
        )
    )

    assert result.status == "error"
    assert result.success is False
    assert result.continuation_status == "blocked_execution_blocking_error"
    assert result.continuation_blocked is True
    assert "execution_blocking_error_contained" in result.reasons
