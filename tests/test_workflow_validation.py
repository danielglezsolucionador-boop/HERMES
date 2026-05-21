from app.runner.workflow_validation import (
    WorkflowValidation,
    WorkflowValidationRequest,
)
from app.services.runtime_status import RuntimeStatus


def _validation_request(**overrides):
    workflow_id = "9.5_WORKFLOW_VALIDATION.md"
    values = {
        "validation_id": "validation-9-5",
        "workflow_id": workflow_id,
        "workflow_execution": {
            "status": "completed",
            "success": True,
            "workflow_id": workflow_id,
        },
        "multi_step_control": {
            "status": "completed",
            "success": True,
            "workflow_id": workflow_id,
        },
        "human_checkpoint_control": {
            "status": "approved",
            "success": True,
            "workflow_id": workflow_id,
            "continuation_allowed": True,
            "governance_status": "human_approved",
            "continuation_status": "authorized_by_human",
        },
        "workflow_recovery_control": {
            "status": "recovered",
            "success": True,
            "workflow_id": workflow_id,
            "continuation_allowed": True,
            "governance_status": "approved",
            "continuation_status": "recovery_validated",
        },
        "workflow_status": "completed",
        "continuation_status": "authorized_by_human",
        "governance_status": "human_approved",
        "runtime_state": {"status": "online", "loop_state": "active"},
        "metadata": {"phase": "9.5"},
    }
    values.update(overrides)
    return WorkflowValidationRequest(**values)


def test_workflow_validation_validates_complete_workflow_and_metrics():
    status = RuntimeStatus()
    validator = WorkflowValidation(status=status)

    result = validator.validate(_validation_request())

    assert result.status == "validated"
    assert result.success is True
    assert result.workflow_safe is True
    assert result.continuation_allowed is True
    assert result.workflow_integrity_preserved is True
    assert result.execution_traceability_preserved is True
    assert result.governance_consistency_preserved is True

    metrics = status.workflow_validation_metrics()
    assert metrics["workflow_validation_status"] == "validated"
    assert metrics["workflow_validations_validated"] == 1
    assert metrics["workflow_validation_errors"] == 0
    assert metrics["workflow_safe"] is True


def test_workflow_validation_blocks_prior_module_inconsistencies():
    validator = WorkflowValidation()

    result = validator.validate(
        _validation_request(
            multi_step_control={
                "status": "blocked",
                "success": False,
                "workflow_id": "9.5_WORKFLOW_VALIDATION.md",
            },
            human_checkpoint_control={
                "status": "waiting",
                "success": True,
                "workflow_id": "9.5_WORKFLOW_VALIDATION.md",
                "continuation_allowed": False,
                "governance_status": "waiting_human_authority",
                "continuation_status": "frozen_waiting_human_approval",
            },
            blocking_conditions=("manual approval pending",),
        )
    )

    assert result.status == "blocked"
    assert result.continuation_allowed is False
    assert "workflow_inconsistencies_detected" in result.reasons
    assert "workflow_blocking_conditions_active" in result.reasons
    assert "multi_step_blocked" in result.detected_inconsistencies
    assert "human_checkpoint_waiting" in result.detected_inconsistencies


def test_workflow_validation_blocks_false_validation_requests():
    validator = WorkflowValidation()

    result = validator.validate(
        _validation_request(
            approve_corrupt_workflow_requested=True,
            ignore_runtime_inconsistencies_requested=True,
            minimize_execution_failures_requested=True,
            falsify_validations_requested=True,
            unsafe_continuation_requested=True,
            hide_execution_failures_requested=True,
            minimize_blocking_conditions_requested=True,
            alter_workflow_history_requested=True,
            ignore_governance_conflicts_requested=True,
            blocking_conditions=("governance conflict",),
        )
    )

    assert result.status == "blocked"
    assert "corrupt_workflow_approval_blocked" in result.reasons
    assert "runtime_inconsistency_ignore_blocked" in result.reasons
    assert "execution_failure_minimization_blocked" in result.reasons
    assert "validation_falsification_blocked" in result.reasons
    assert "unsafe_continuation_blocked" in result.reasons
    assert "execution_failure_concealment_blocked" in result.reasons
    assert "blocking_condition_minimization_blocked" in result.reasons
    assert "workflow_history_alteration_blocked" in result.reasons
    assert "governance_conflict_ignore_blocked" in result.reasons


def test_workflow_validation_blocks_runtime_governance_and_continuity_drift():
    validator = WorkflowValidation()

    result = validator.validate(
        _validation_request(
            runtime_state={"status": "degraded", "loop_state": "stalled"},
            governance_status="pending",
            continuation_status="broken",
        )
    )

    assert result.status == "blocked"
    assert "runtime_validation_required" in result.reasons
    assert "governance_validation_required" in result.reasons
    assert "continuity_validation_required" in result.reasons
    assert "workflow_inconsistencies_detected" in result.reasons


def test_workflow_validation_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    validator = WorkflowValidation(status=status)

    def broken_context(*args, **kwargs):
        raise RuntimeError("workflow validation exploded")

    monkeypatch.setattr(validator, "_context", broken_context)

    result = validator.validate(_validation_request())

    assert result.status == "error"
    assert "workflow_validation_error_contained" in result.reasons

    metrics = status.workflow_validation_metrics()
    assert metrics["workflow_validation_status"] == "error"
    assert metrics["workflow_validation_errors"] == 1
