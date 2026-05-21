from app.runner.audit_request_system import AuditRequestInput, AuditRequestSystem
from app.runner.audit_response_control import (
    AuditResponseControl,
    AuditResponseInput,
)
from app.runner.self_validation import SelfValidation, SelfValidationRequest
from app.services.runtime_status import RuntimeStatus


def _audit_request_result(
    modified_files=("app/runner/audit_response_control.py",),
    risk_notes=(),
):
    validation = SelfValidation().validate(
        SelfValidationRequest(
            execution_id="execution-1",
            task_id="task-1",
            outputs=("Implemented audit response control.",),
            modified_files=modified_files,
            runtime_state={"status": "online", "loop_state": "active"},
            risk_notes=risk_notes,
        )
    )
    return AuditRequestSystem().request(
        AuditRequestInput(
            validation_result=validation,
            execution_summary="Audit response control implementation complete.",
            runtime_state={"status": "online", "loop_state": "active"},
            metadata={"phase": "5.3.3"},
        )
    )


def test_audit_response_approved_moves_to_human_approval_pipeline():
    status = RuntimeStatus()
    request_result = _audit_request_result()
    control = AuditResponseControl(status=status)

    result = control.process(
        AuditResponseInput(
            audit_request=request_result,
            audit_result="approved",
            risk_level="clear",
            execution_context={"phase": "5.3.3"},
            audit_logs=({"event": "sentinel_approved"},),
        )
    )

    assert result.status == "approved"
    assert result.success is True
    assert result.audit_id == request_result.audit_id
    assert result.execution_id == "execution-1"
    assert result.correction_status == "not_required"
    assert result.continuation_status == "ready_for_approval_pipeline"
    assert result.human_approval_status == "pending"
    assert result.audit_integrity_preserved is True
    assert result.context_preserved is True
    assert [entry["state"] for entry in result.audit_lifecycle] == [
        "received",
        "validated",
        "approved",
    ]

    metrics = status.audit_response_metrics()
    assert metrics["audit_response_status"] == "approved"
    assert metrics["audit_responses_approved"] == 1
    assert metrics["continuation_status"] == "ready_for_approval_pipeline"


def test_audit_response_approved_with_warnings_preserves_visibility():
    request_result = _audit_request_result()
    control = AuditResponseControl()

    result = control.process(
        AuditResponseInput(
            audit_request=request_result,
            audit_result="approved_with_warnings",
            risk_level="low",
            warnings=("minor observability note",),
        )
    )

    assert result.status == "approved_with_warnings"
    assert result.success is True
    assert result.continuation_status == "ready_with_warnings"
    assert result.human_approval_status == "pending"
    assert result.warnings == ("minor observability note",)
    assert "approved_with_warnings" in result.reasons


def test_audit_response_needs_fix_blocks_continuation():
    request_result = _audit_request_result()
    control = AuditResponseControl()

    result = control.process(
        AuditResponseInput(
            audit_request=request_result,
            audit_result="needs_fix",
            risk_level="elevated",
            correction_requirements=("tighten validation coverage",),
        )
    )

    assert result.status == "needs_fix"
    assert result.success is False
    assert result.continuation_status == "blocked_needs_fix"
    assert result.correction_status == "required"
    assert result.execution_decision == "prepare_correction_workflow"
    assert result.correction_requirements == ("tighten validation coverage",)


def test_audit_response_rejected_security_escalates_to_centinela():
    request_result = _audit_request_result(
        modified_files=("app/runner/provider_bridge.py",),
        risk_notes=("security credential leakage",),
    )
    control = AuditResponseControl()

    result = control.process(
        AuditResponseInput(
            audit_request=request_result,
            audit_result="rejected",
            risk_level="critical",
            detected_risks=("credential leakage",),
            rejection_reasons=("credential leakage detected",),
        )
    )

    assert result.status == "rejected"
    assert result.success is False
    assert result.continuation_status == "blocked_security_escalation"
    assert result.human_approval_status == "escalated"
    assert result.security_escalation_status == "escalated_to_centinela"
    assert result.centinela_escalation is True
    assert result.execution_decision == "escalate_to_centinela"
    assert "critical_security_escalation_required" in result.reasons


def test_audit_response_blocks_integrity_mismatch():
    request_result = _audit_request_result()
    control = AuditResponseControl()

    result = control.process(
        AuditResponseInput(
            audit_request=request_result,
            audit_id=request_result.audit_id,
            execution_id="different-execution",
            audit_result="approved",
            risk_level="clear",
        )
    )

    assert result.status == "blocked"
    assert result.success is False
    assert result.audit_integrity_preserved is False
    assert result.continuation_status == "blocked_audit_response_invalid"
    assert "execution_id_mismatch" in result.reasons


def test_audit_response_contains_internal_errors(monkeypatch):
    control = AuditResponseControl()

    def broken_response(*args, **kwargs):
        raise RuntimeError("audit response exploded")

    monkeypatch.setattr(control, "_audit_response", broken_response)

    result = control.process(AuditResponseInput(audit_id="audit-1"))

    assert result.status == "error"
    assert result.success is False
    assert result.continuation_status == "blocked_audit_response_error"
    assert result.audit_integrity_preserved is False
    assert "audit_response_error_contained" in result.reasons
