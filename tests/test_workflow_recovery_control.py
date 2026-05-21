from app.runner.human_checkpoint_control import (
    HumanCheckpointControl,
    HumanCheckpointControlRequest,
)
from app.runner.workflow_recovery_control import (
    WorkflowRecoveryControl,
    WorkflowRecoveryControlRequest,
)
from app.services.runtime_status import RuntimeStatus


def _recovery_request(**overrides):
    values = {
        "recovery_id": "recovery-9-4",
        "workflow_id": "9.4_WORKFLOW_RECOVERY_CONTROL.md",
        "workflow_state": {
            "workflow_id": "9.4_WORKFLOW_RECOVERY_CONTROL.md",
            "step": "recovery_validation",
        },
        "execution_context": {"execution_id": "execution-9-4"},
        "continuation_status": "recovery_validated",
        "recovery_status": "ready",
        "governance_status": "approved",
        "checkpoint_status": "valid",
        "runtime_state": {"status": "online", "loop_state": "active"},
        "metadata": {"phase": "9.4"},
    }
    values.update(overrides)
    return WorkflowRecoveryControlRequest(**values)


def _human_checkpoint_result():
    control = HumanCheckpointControl()
    return control.control(
        HumanCheckpointControlRequest(
            checkpoint_id="checkpoint-9-4",
            workflow_id="9.4_WORKFLOW_RECOVERY_CONTROL.md",
            approval_status="approved",
            governance_status="human_approved",
            continuation_status="authorized_by_human",
            authority_status="CEO",
            runtime_state={"status": "online"},
        )
    )


def test_workflow_recovery_control_recovers_workflow_and_metrics():
    status = RuntimeStatus()
    control = WorkflowRecoveryControl(status=status)

    result = control.recover(_recovery_request())

    assert result.status == "recovered"
    assert result.success is True
    assert result.continuation_allowed is True
    assert result.state_restored is True
    assert result.workflow_integrity_valid is True
    assert result.runtime_continuity_valid is True
    assert result.governance_alignment_valid is True

    metrics = status.workflow_recovery_control_metrics()
    assert metrics["workflow_recovery_control_status"] == "recovered"
    assert metrics["workflow_recoveries_completed"] == 1
    assert metrics["workflow_recovery_control_errors"] == 0


def test_workflow_recovery_control_uses_checkpoint_and_human_context():
    control = WorkflowRecoveryControl()

    result = control.recover(
        WorkflowRecoveryControlRequest(
            workflow_id="9.4_WORKFLOW_RECOVERY_CONTROL.md",
            checkpoint_recovery={
                "recovery_id": "checkpoint-recovery-1",
                "recovery_status": "recovery_prepared",
                "checkpoint_valid": True,
                "continuation_status": "recovery_validated",
                "restored_state": {
                    "workflow_id": "9.4_WORKFLOW_RECOVERY_CONTROL.md"
                },
            },
            human_checkpoint_control=_human_checkpoint_result(),
            governance_status="approved",
            runtime_state={"status": "online"},
        )
    )

    assert result.status == "recovered"
    assert result.recovery_id == "checkpoint-recovery-1"
    assert result.restored_state["workflow_id"] == (
        "9.4_WORKFLOW_RECOVERY_CONTROL.md"
    )


def test_workflow_recovery_control_blocks_invalid_recovery():
    control = WorkflowRecoveryControl()

    result = control.recover(
        _recovery_request(
            workflow_state={},
            recovery_status="corrupt",
            continuation_status="broken",
            governance_status="pending",
            checkpoint_status="invalid",
            runtime_state={"status": "degraded"},
            blocking_conditions=("runtime corruption",),
            recover_corrupt_workflow_requested=True,
            ignore_runtime_inconsistencies_requested=True,
            overwrite_governance_state_requested=True,
            unsafe_continuation_requested=True,
            hide_recovery_failures_requested=True,
            ignore_blocking_conditions_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "restored_state_required" in result.reasons
    assert "recovery_status_invalid" in result.reasons
    assert "runtime_continuity_required" in result.reasons
    assert "governance_alignment_required" in result.reasons
    assert "execution_consistency_required" in result.reasons
    assert "operational_stability_required" in result.reasons
    assert "corrupt_workflow_recovery_blocked" in result.reasons
    assert "runtime_inconsistency_ignore_blocked" in result.reasons
    assert "governance_state_overwrite_blocked" in result.reasons
    assert "unsafe_continuation_blocked" in result.reasons
    assert "recovery_failure_concealment_blocked" in result.reasons
    assert "blocking_condition_ignore_blocked" in result.reasons


def test_workflow_recovery_control_blocks_history_and_status_falsification():
    control = WorkflowRecoveryControl()

    result = control.recover(
        _recovery_request(
            alter_workflow_history_requested=True,
            minimize_runtime_corruption_requested=True,
            falsify_continuation_status_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "workflow_history_alteration_blocked" in result.reasons
    assert "runtime_corruption_minimization_blocked" in result.reasons
    assert "continuation_status_falsification_blocked" in result.reasons


def test_workflow_recovery_control_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    control = WorkflowRecoveryControl(status=status)

    def broken_state(*args, **kwargs):
        raise RuntimeError("workflow recovery exploded")

    monkeypatch.setattr(control, "_restored_state", broken_state)

    result = control.recover(_recovery_request())

    assert result.status == "error"
    assert "workflow_recovery_control_error_contained" in result.reasons

    metrics = status.workflow_recovery_control_metrics()
    assert metrics["workflow_recovery_control_status"] == "error"
    assert metrics["workflow_recovery_control_errors"] == 1
