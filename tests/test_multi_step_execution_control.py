from app.runner.multi_step_execution_control import (
    MultiStepExecutionControl,
    MultiStepExecutionControlRequest,
)
from app.runner.workflow_execution_engine import (
    WorkflowExecutionEngine,
    WorkflowExecutionEngineRequest,
)
from app.services.runtime_status import RuntimeStatus


WORKFLOW_STEPS = (
    "workflow_initialization",
    "step_execution",
    "step_validation",
)


def _workflow_execution():
    engine = WorkflowExecutionEngine()
    return engine.execute(
        WorkflowExecutionEngineRequest(
            workflow_id="9.2_MULTI_STEP_EXECUTION_CONTROL.md",
            execution_steps=WORKFLOW_STEPS,
            official_workflows=("9.2_MULTI_STEP_EXECUTION_CONTROL.md",),
            runtime_state={"status": "online"},
        )
    )


def _control_request(**overrides):
    values = {
        "workflow_id": "9.2_MULTI_STEP_EXECUTION_CONTROL.md",
        "workflow_steps": WORKFLOW_STEPS,
        "completed_steps": ("workflow_initialization",),
        "step_statuses": {"workflow_initialization": "completed"},
        "continuation_status": "ready",
        "governance_status": "approved",
        "checkpoint_status": "not_required",
        "runtime_state": {"status": "online", "loop_state": "active"},
        "metadata": {"phase": "9.2"},
    }
    values.update(overrides)
    return MultiStepExecutionControlRequest(**values)


def test_multi_step_execution_control_authorizes_next_step_and_metrics():
    status = RuntimeStatus()
    control = MultiStepExecutionControl(status=status)

    result = control.control(_control_request())

    assert result.status == "advanced"
    assert result.success is True
    assert result.expected_next_step == "step_execution"
    assert result.next_step == "step_execution"
    assert result.execution_sequencing_valid is True
    assert result.step_transition_valid is True
    assert result.workflow_progression == "next_step_authorized:step_execution"

    metrics = status.multi_step_execution_control_metrics()
    assert metrics["multi_step_execution_control_status"] == "advanced"
    assert metrics["multi_step_controls_advanced"] == 1
    assert metrics["multi_step_execution_control_errors"] == 0


def test_multi_step_execution_control_uses_workflow_execution_result():
    control = MultiStepExecutionControl()

    result = control.control(
        MultiStepExecutionControlRequest(
            workflow_execution=_workflow_execution(),
            completed_steps=("workflow_initialization",),
            step_statuses={"workflow_initialization": "completed"},
            runtime_state={"status": "online"},
        )
    )

    assert result.status == "advanced"
    assert result.workflow_id == "9.2_MULTI_STEP_EXECUTION_CONTROL.md"
    assert result.expected_next_step == "step_execution"


def test_multi_step_execution_control_blocks_step_skipping():
    control = MultiStepExecutionControl()

    result = control.control(
        _control_request(
            next_step="step_validation",
            skip_step_requested=True,
            alter_execution_order_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "step_transition_invalid" in result.reasons
    assert "workflow_step_skipping_detected" in result.reasons
    assert "workflow_step_skip_blocked" in result.reasons
    assert "execution_order_alteration_blocked" in result.reasons


def test_multi_step_execution_control_blocks_invalid_status_and_runtime():
    control = MultiStepExecutionControl()

    result = control.control(
        _control_request(
            step_statuses={"workflow_initialization": "failed"},
            governance_status="pending",
            continuation_status="broken",
            checkpoint_status="pending",
            runtime_state={"status": "degraded"},
            blocking_conditions=("checkpoint missing",),
            ignore_critical_validations_requested=True,
            minimize_blocking_conditions_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "execution_sequencing_required" in result.reasons
    assert "invalid_step_status:workflow_initialization" in result.reasons
    assert "runtime_integrity_required" in result.reasons
    assert "governance_alignment_required" in result.reasons
    assert "execution_continuity_required" in result.reasons
    assert "operational_stability_required" in result.reasons
    assert "critical_validation_ignore_blocked" in result.reasons
    assert "blocking_condition_minimization_blocked" in result.reasons


def test_multi_step_execution_control_marks_completed_workflow():
    control = MultiStepExecutionControl()

    result = control.control(
        _control_request(
            completed_steps=WORKFLOW_STEPS,
            step_statuses={step: "completed" for step in WORKFLOW_STEPS},
        )
    )

    assert result.status == "completed"
    assert result.workflow_progression == "workflow_completed"
    assert result.pending_steps == ()


def test_multi_step_execution_control_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    control = MultiStepExecutionControl(status=status)

    def broken_order(*args, **kwargs):
        raise RuntimeError("multi-step control exploded")

    monkeypatch.setattr(control, "_execution_order", broken_order)

    result = control.control(_control_request())

    assert result.status == "error"
    assert "multi_step_execution_control_error_contained" in result.reasons

    metrics = status.multi_step_execution_control_metrics()
    assert metrics["multi_step_execution_control_status"] == "error"
    assert metrics["multi_step_execution_control_errors"] == 1
