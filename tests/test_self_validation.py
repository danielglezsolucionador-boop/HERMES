from app.runner.provider_response_handling import ProviderResponseHandlingResult
from app.runner.self_validation import SelfValidation, SelfValidationRequest
from app.services.runtime_status import RuntimeStatus


def test_self_validation_marks_coherent_execution_valid_and_prepares_audit():
    status = RuntimeStatus()
    validator = SelfValidation(status=status)

    result = validator.validate(
        SelfValidationRequest(
            execution_id="execution-1",
            task_id="task-1",
            outputs=("Implemented provider safety.",),
            modified_files=("app/runner/provider_failure_control.py",),
            execution_logs=({"event": "tests_passed"},),
            provider_responses=(
                {
                    "status": "handled",
                    "success": True,
                    "response_status": "stored",
                    "audit_status": "audit_pending",
                },
            ),
            runtime_state={"status": "online", "loop_state": "active"},
            lifecycle_state={
                "state_transition_allowed": True,
                "lifecycle_transition_allowed": True,
            },
            metadata={"phase": "5.3.1"},
        )
    )

    assert result.status == "valid"
    assert result.success is True
    assert result.validation_status == "valid"
    assert result.risk_status == "clear"
    assert result.audit_required is True
    assert result.self_approved is False
    assert result.continuation_blocked is False
    assert result.audit_package["validation_id"] == result.validation_id
    assert result.audit_package["self_approved"] is False

    metrics = status.self_validation_metrics()
    assert metrics["self_validation_status"] == "valid"
    assert metrics["self_validations_valid"] == 1
    assert metrics["audit_required"] is True


def test_self_validation_invalid_when_execution_outputs_are_missing():
    validator = SelfValidation()

    result = validator.validate(SelfValidationRequest())

    assert result.status == "invalid"
    assert result.success is False
    assert result.continuation_blocked is True
    assert result.risk_status == "critical"
    assert "missing_execution_id" in result.reasons
    assert "missing_execution_outputs" in result.reasons


def test_self_validation_blocks_dangerous_runtime_file_change():
    validator = SelfValidation()

    result = validator.validate(
        SelfValidationRequest(
            execution_id="execution-1",
            outputs=("Changed runtime loop.",),
            modified_files=("app/runner/runtime_loop.py",),
            runtime_state={"status": "online", "loop_state": "active"},
        )
    )

    assert result.status == "invalid"
    assert result.continuation_blocked is True
    assert "runtime_core_file_modified" in result.detected_risks
    assert "dangerous_file_change_detected" in result.inconsistencies


def test_self_validation_invalidates_rejected_provider_response():
    validator = SelfValidation()
    rejected_response = ProviderResponseHandlingResult(
        status="rejected",
        success=False,
        handling_id="handling-1",
        response_status="rejected",
        response_type="failure",
        audit_status="blocked",
        reasons=("empty_response_content",),
    )

    result = validator.validate(
        SelfValidationRequest(
            execution_id="execution-1",
            outputs=("Provider rejected.",),
            modified_files=("app/runner/provider_response_handling.py",),
            provider_responses=(rejected_response,),
        )
    )

    assert result.status == "invalid"
    assert "provider_response_invalid" in result.reasons
    assert "provider_response_rejected" in result.reasons
    assert "response_audit_blocked" in result.reasons


def test_self_validation_warns_when_files_are_not_declared():
    validator = SelfValidation()

    result = validator.validate(
        SelfValidationRequest(
            execution_id="execution-1",
            outputs=("Generated output.",),
            runtime_state={"status": "online", "loop_state": "active"},
        )
    )

    assert result.status == "warning"
    assert result.success is True
    assert result.risk_status == "elevated"
    assert result.continuation_blocked is False
    assert "no_modified_files_declared" in result.reasons


def test_self_validation_contains_internal_errors(monkeypatch):
    validator = SelfValidation()

    def broken_execution(*args, **kwargs):
        raise RuntimeError("validation context exploded")

    monkeypatch.setattr(validator, "_execution_reasons", broken_execution)

    result = validator.validate(SelfValidationRequest(execution_id="execution-1"))

    assert result.status == "error"
    assert result.success is False
    assert result.continuation_blocked is True
    assert result.risk_status == "critical"
    assert "self_validation_error_contained" in result.reasons
