from app.runner.workflow_execution_engine import (
    WorkflowExecutionEngine,
    WorkflowExecutionEngineRequest,
)
from app.services.runtime_status import RuntimeStatus


def _workflow_request(**overrides):
    values = {
        "workflow_id": "9.1_WORKFLOW_EXECUTION_ENGINE.md",
        "workflow_objective": "execute controlled workflow",
        "execution_steps": (
            "workflow_initialization",
            "step_execution",
            "execution_validation",
        ),
        "official_workflows": ("9.1_WORKFLOW_EXECUTION_ENGINE.md",),
        "execution_state": "ready",
        "continuation_status": "ready",
        "governance_status": "approved",
        "checkpoint_status": "not_required",
        "runtime_state": {"status": "online", "loop_state": "active"},
        "operational_dependencies": ("knowledge_core_validation",),
        "satisfied_dependencies": ("knowledge_core_validation",),
        "metadata": {"phase": "9.1"},
    }
    values.update(overrides)
    return WorkflowExecutionEngineRequest(**values)


def test_workflow_execution_engine_executes_steps_and_metrics():
    status = RuntimeStatus()
    engine = WorkflowExecutionEngine(status=status)

    result = engine.execute(_workflow_request())

    assert result.status == "completed"
    assert result.success is True
    assert result.workflow_completion_confirmed is True
    assert result.execution_continuity_valid is True
    assert result.runtime_integrity_valid is True
    assert result.governance_alignment_valid is True
    assert result.execution_sequencing_controlled is True
    assert len(result.executed_steps) == 3
    assert result.human_visibility_payload["workflow_status"] == "completed"

    metrics = status.workflow_execution_engine_metrics()
    assert metrics["workflow_execution_engine_status"] == "completed"
    assert metrics["workflow_executions_completed"] == 1
    assert metrics["workflow_execution_engine_errors"] == 0
    assert metrics["workflow_completion_confirmed"] is True


def test_workflow_execution_engine_blocks_arbitrary_workflow_and_sequence_change():
    engine = WorkflowExecutionEngine()

    result = engine.execute(
        _workflow_request(
            workflow_id="invented-workflow",
            invent_workflow_requested=True,
            alter_execution_sequence_requested=True,
        )
    )

    assert result.status == "blocked"
    assert result.workflow_completion_confirmed is False
    assert "workflow_consistency_required" in result.reasons
    assert "arbitrary_workflow_invention_blocked" in result.reasons
    assert "execution_sequence_alteration_blocked" in result.reasons


def test_workflow_execution_engine_blocks_unsafe_runtime_and_governance():
    engine = WorkflowExecutionEngine()

    result = engine.execute(
        _workflow_request(
            governance_status="pending",
            checkpoint_status="pending",
            continuation_status="broken",
            runtime_state={"status": "degraded"},
            blocking_conditions=("runtime drift",),
            minimize_blocking_conditions_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "runtime_integrity_required" in result.reasons
    assert "governance_alignment_required" in result.reasons
    assert "execution_continuity_required" in result.reasons
    assert "operational_stability_required" in result.reasons
    assert "runtime drift" in result.reasons
    assert "blocking_condition_minimization_blocked" in result.reasons


def test_workflow_execution_engine_blocks_non_prefix_completed_steps():
    engine = WorkflowExecutionEngine()

    result = engine.execute(
        _workflow_request(completed_steps=("execution_validation",))
    )

    assert result.status == "blocked"
    assert "execution_sequencing_required" in result.reasons


def test_workflow_execution_engine_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    engine = WorkflowExecutionEngine(status=status)

    def broken_steps(*args, **kwargs):
        raise RuntimeError("workflow execution exploded")

    monkeypatch.setattr(engine, "_executed_steps", broken_steps)

    result = engine.execute(_workflow_request())

    assert result.status == "error"
    assert "workflow_execution_engine_error_contained" in result.reasons

    metrics = status.workflow_execution_engine_metrics()
    assert metrics["workflow_execution_engine_status"] == "error"
    assert metrics["workflow_execution_engine_errors"] == 1
