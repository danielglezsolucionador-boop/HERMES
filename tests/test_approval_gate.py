from app.runner.approval_gate import (
    ApprovalGate,
    ApprovalGateRequest,
    HumanDecisionInput,
)
from app.runner.audit_request_system import AuditRequestInput, AuditRequestSystem
from app.runner.audit_response_control import (
    AuditResponseControl,
    AuditResponseInput,
)
from app.runner.self_validation import SelfValidation, SelfValidationRequest
from app.services.runtime_status import RuntimeStatus


def _audit_response_result(
    audit_result="approved",
    risk_level="clear",
    modified_files=("app/runner/approval_gate.py",),
    warnings=(),
    detected_risks=(),
    rejection_reasons=(),
):
    validation = SelfValidation().validate(
        SelfValidationRequest(
            execution_id="execution-1",
            task_id="task-1",
            outputs=("Implemented approval gate.",),
            modified_files=modified_files,
            runtime_state={"status": "online", "loop_state": "active"},
        )
    )
    audit_request = AuditRequestSystem().request(
        AuditRequestInput(
            validation_result=validation,
            execution_summary="Approval gate implementation complete.",
            runtime_state={"status": "online", "loop_state": "active"},
        )
    )
    return AuditResponseControl().process(
        AuditResponseInput(
            audit_request=audit_request,
            audit_result=audit_result,
            risk_level=risk_level,
            warnings=warnings,
            detected_risks=detected_risks,
            rejection_reasons=rejection_reasons,
        )
    )


def test_approval_gate_creates_pending_human_request():
    status = RuntimeStatus()
    audit_response = _audit_response_result(warnings=("minor warning",))
    gate = ApprovalGate(status=status)

    result = gate.request(
        ApprovalGateRequest(
            audit_response=audit_response,
            execution_summary="Approval gate complete.",
            continuation_recommendation="continue after human approval",
            execution_context={"phase": "5.3.4"},
        )
    )

    assert result.status == "pending"
    assert result.success is True
    assert result.approval_status == "pending"
    assert result.audit_status == "approved"
    assert result.continuation_status == "frozen_waiting_human_approval"
    assert result.governance_status == "waiting_human_authority"
    assert result.autonomy_blocked is True
    assert result.human_authority_preserved is True
    assert result.human_report["execution_summary"] == "Approval gate complete."
    assert result.human_report["warnings"] == ["minor warning"]

    metrics = status.approval_gate_metrics()
    assert metrics["approval_gate_status"] == "pending"
    assert metrics["approval_requests_pending"] == 1
    assert metrics["autonomy_blocked"] is True


def test_approval_gate_blocks_unapproved_audit_response():
    audit_response = _audit_response_result(
        audit_result="rejected",
        risk_level="elevated",
        rejection_reasons=("audit rejected",),
    )
    gate = ApprovalGate()

    result = gate.request(ApprovalGateRequest(audit_response=audit_response))

    assert result.status == "blocked"
    assert result.success is False
    assert result.continuation_status == "blocked_approval_request_invalid"
    assert result.autonomy_blocked is True
    assert "audit_not_approved_for_approval_gate" in result.reasons


def test_approval_gate_records_human_approval_without_auto_continue():
    gate = ApprovalGate()
    pending = gate.request(
        ApprovalGateRequest(
            audit_response=_audit_response_result(),
            execution_summary="Ready for approval.",
        )
    )

    result = gate.decide(
        HumanDecisionInput(
            approval_request=pending,
            human_decision="approve",
            decided_by="CEO",
            decision_reason="Approved for next subphase.",
        )
    )

    assert result.status == "approved"
    assert result.success is True
    assert result.human_decision == "approve"
    assert result.continuation_status == "authorized_by_human"
    assert result.governance_status == "human_approved"
    assert result.autonomy_blocked is False
    assert "human_authorization_recorded_no_auto_continue" in result.reasons


def test_approval_gate_records_human_rejection_as_blocking():
    gate = ApprovalGate()
    pending = gate.request(ApprovalGateRequest(audit_response=_audit_response_result()))

    result = gate.decide(
        HumanDecisionInput(
            approval_request=pending,
            human_decision="reject",
            decided_by="CEO",
            decision_reason="Stop continuation.",
        )
    )

    assert result.status == "rejected"
    assert result.success is False
    assert result.continuation_status == "blocked_human_rejected"
    assert result.autonomy_blocked is True
    assert "human_rejection_blocks_continuation" in result.reasons


def test_approval_gate_records_needs_changes_and_escalation():
    gate = ApprovalGate()
    pending_changes = gate.request(
        ApprovalGateRequest(audit_response=_audit_response_result())
    )
    pending_escalation = gate.request(
        ApprovalGateRequest(audit_response=_audit_response_result())
    )

    changes = gate.decide(
        HumanDecisionInput(
            approval_request=pending_changes,
            human_decision="needs_changes",
            decided_by="CEO",
        )
    )
    escalation = gate.decide(
        HumanDecisionInput(
            approval_request=pending_escalation,
            human_decision="escalate",
            decided_by="CEO",
        )
    )

    assert changes.status == "needs_changes"
    assert changes.continuation_status == "blocked_needs_changes"
    assert changes.autonomy_blocked is True
    assert escalation.status == "escalated"
    assert escalation.continuation_status == "blocked_escalated"
    assert escalation.autonomy_blocked is True


def test_approval_gate_blocks_invalid_human_decision():
    gate = ApprovalGate()
    pending = gate.request(ApprovalGateRequest(audit_response=_audit_response_result()))

    result = gate.decide(
        HumanDecisionInput(
            approval_request=pending,
            human_decision="approve",
        )
    )

    assert result.status == "blocked"
    assert result.success is False
    assert result.continuation_status == "blocked_human_decision_invalid"
    assert "missing_human_decision_authority" in result.reasons


def test_approval_gate_contains_internal_errors(monkeypatch):
    gate = ApprovalGate()

    def broken_report(*args, **kwargs):
        raise RuntimeError("approval report exploded")

    monkeypatch.setattr(gate, "_human_report", broken_report)

    result = gate.request(
        ApprovalGateRequest(
            execution_id="execution-1",
            audit_status="approved",
            risk_status="clear",
        )
    )

    assert result.status == "error"
    assert result.success is False
    assert result.continuation_status == "blocked_approval_gate_error"
    assert result.autonomy_blocked is True
    assert "approval_gate_error_contained" in result.reasons
