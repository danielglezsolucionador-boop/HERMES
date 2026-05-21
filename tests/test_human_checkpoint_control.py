from app.runner.human_checkpoint_control import (
    HumanCheckpointControl,
    HumanCheckpointControlRequest,
)
from app.runner.multi_step_execution_control import (
    MultiStepExecutionControl,
    MultiStepExecutionControlRequest,
)
from app.services.runtime_status import RuntimeStatus


def _checkpoint_request(**overrides):
    values = {
        "checkpoint_id": "checkpoint-9-3",
        "workflow_id": "9.3_HUMAN_CHECKPOINT_CONTROL.md",
        "approval_status": "waiting",
        "execution_status": "advanced",
        "governance_status": "waiting_human_authority",
        "continuation_status": "frozen_waiting_human_approval",
        "authority_status": "human_required",
        "runtime_state": {"status": "paused"},
        "approval_conditions": ("human approval required",),
        "metadata": {"phase": "9.3"},
    }
    values.update(overrides)
    return HumanCheckpointControlRequest(**values)


def _multi_step_result():
    control = MultiStepExecutionControl()
    return control.control(
        MultiStepExecutionControlRequest(
            workflow_id="9.3_HUMAN_CHECKPOINT_CONTROL.md",
            workflow_steps=("detect_checkpoint", "pause_execution"),
            completed_steps=("detect_checkpoint",),
            governance_status="approved",
            continuation_status="ready",
            checkpoint_status="not_required",
            runtime_state={"status": "online"},
        )
    )


def test_human_checkpoint_control_waits_and_pauses_execution():
    status = RuntimeStatus()
    control = HumanCheckpointControl(status=status)

    result = control.control(_checkpoint_request())

    assert result.status == "waiting"
    assert result.success is True
    assert result.checkpoint_detected is True
    assert result.execution_paused is True
    assert result.continuation_allowed is False
    assert result.human_authority_preserved is True
    assert "waiting_human_approval" in result.reasons

    metrics = status.human_checkpoint_control_metrics()
    assert metrics["human_checkpoint_control_status"] == "waiting"
    assert metrics["human_checkpoints_waiting"] == 1
    assert metrics["human_checkpoint_control_errors"] == 0


def test_human_checkpoint_control_allows_approved_continuation():
    control = HumanCheckpointControl()

    result = control.control(
        _checkpoint_request(
            approval_status="approved",
            governance_status="human_approved",
            continuation_status="authorized_by_human",
            authority_status="CEO",
            runtime_state={"status": "online"},
        )
    )

    assert result.status == "approved"
    assert result.continuation_allowed is True
    assert result.execution_paused is False
    assert result.approval_legitimate is True
    assert "human_checkpoint_approved" in result.reasons


def test_human_checkpoint_control_uses_multi_step_context():
    control = HumanCheckpointControl()

    result = control.control(
        HumanCheckpointControlRequest(
            checkpoint_id="checkpoint-from-multi-step",
            approval_status="waiting",
            governance_status="waiting_human_authority",
            continuation_status="frozen_waiting_human_approval",
            authority_status="human_required",
            runtime_state={"status": "paused"},
            multi_step_control=_multi_step_result(),
        )
    )

    assert result.status == "waiting"
    assert result.workflow_id == "9.3_HUMAN_CHECKPOINT_CONTROL.md"
    assert result.execution_paused is True


def test_human_checkpoint_control_blocks_rejection_and_overrides():
    control = HumanCheckpointControl()

    result = control.control(
        _checkpoint_request(
            approval_status="rejected",
            governance_status="human_rejected",
            continuation_status="blocked_human_rejected",
            ignore_human_checkpoint_requested=True,
            continue_blocked_workflow_requested=True,
            overwrite_human_approval_requested=True,
            falsify_approval_requested=True,
        )
    )

    assert result.status == "blocked"
    assert result.continuation_allowed is False
    assert "human_rejection_blocks_continuation" in result.reasons
    assert "human_checkpoint_ignore_blocked" in result.reasons
    assert "blocked_workflow_continuation_blocked" in result.reasons
    assert "human_approval_overwrite_blocked" in result.reasons
    assert "approval_falsification_blocked" in result.reasons


def test_human_checkpoint_control_reports_changes_and_escalation():
    control = HumanCheckpointControl()

    changes = control.control(
        _checkpoint_request(
            approval_status="needs_changes",
            governance_status="waiting_human_authority",
        )
    )
    escalated = control.control(
        _checkpoint_request(
            approval_status="escalated",
            governance_status="waiting_human_authority",
        )
    )

    assert changes.status == "changes_requested"
    assert "human_requested_changes" in changes.reasons
    assert escalated.status == "escalated"
    assert "human_escalation_requested" in escalated.reasons


def test_human_checkpoint_control_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    control = HumanCheckpointControl(status=status)

    def broken_context(*args, **kwargs):
        raise RuntimeError("human checkpoint exploded")

    monkeypatch.setattr(control, "_context", broken_context)

    result = control.control(_checkpoint_request())

    assert result.status == "error"
    assert "human_checkpoint_control_error_contained" in result.reasons

    metrics = status.human_checkpoint_control_metrics()
    assert metrics["human_checkpoint_control_status"] == "error"
    assert metrics["human_checkpoint_control_errors"] == 1
