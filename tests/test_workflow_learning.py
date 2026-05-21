from app.runner.operational_memory import (
    OperationalMemory,
    OperationalMemoryCaptureRequest,
)
from app.runner.workflow_learning import (
    WorkflowLearning,
    WorkflowLearningRequest,
)
from app.services.runtime_status import RuntimeStatus


def _memory_record(**overrides):
    values = {
        "execution_id": "execution-1",
        "task_id": "task-1",
        "memory_type": "execution",
        "workflow": "5.5.2_WORKFLOW_LEARNING.md",
        "event_type": "workflow_completed",
        "memory_context": {
            "execution_id": "execution-1",
            "summary": "workflow learning source",
        },
        "outputs": {"tests": "passed"},
        "governance_status": "approved",
        "audit_status": "approved",
        "risk_level": "clear",
        "governance_history": ({"approval_status": "approved"},),
        "audit_history": ({"audit_status": "approved"},),
        "workflow_history": ({"workflow": "5.5.2_WORKFLOW_LEARNING.md"},),
        "continuation_history": ({"continuation_status": "safe"},),
    }
    values.update(overrides)
    if "memory_context" not in overrides:
        values["memory_context"] = {
            **values["memory_context"],
            "execution_id": values["execution_id"],
        }
    memory = OperationalMemory()
    result = memory.capture(OperationalMemoryCaptureRequest(**values))
    assert result.status == "captured"
    return result.memory_record


def test_workflow_learning_detects_success_patterns_and_metrics():
    status = RuntimeStatus()
    learning = WorkflowLearning(status=status)
    records = (
        _memory_record(),
        _memory_record(execution_id="execution-2", task_id="task-2"),
    )

    result = learning.analyze(
        WorkflowLearningRequest(
            execution_id="execution-3",
            task_id="task-3",
            workflow="5.5.2_WORKFLOW_LEARNING.md",
            learning_type="success_pattern",
            memory_records=records,
            governance_status="approved",
            audit_status="approved",
            runtime_state={"state": "active"},
        )
    )

    assert result.status == "learned"
    assert result.success is True
    assert result.memory_analyzed is True
    assert result.learning_validated is True
    assert result.reuse_allowed is False
    assert result.optimization_status == "suggested_only"
    assert result.patterns_detected[0]["pattern_type"] == "success_pattern"

    metrics = status.workflow_learning_metrics()
    assert metrics["workflow_learning_status"] == "learned"
    assert metrics["workflow_learning_learned"] == 1
    assert metrics["patterns_detected_count"] == 1
    assert metrics["autonomy_expanded"] is False


def test_workflow_learning_allows_reuse_after_governance_audit_and_runtime_safety():
    learning = WorkflowLearning()

    result = learning.analyze(
        WorkflowLearningRequest(
            learning_type="success_pattern",
            memory_records=(_memory_record(), _memory_record(task_id="task-2")),
            governance_status="approved",
            audit_status="approved_with_warnings",
            runtime_state={"loop_state": "active"},
            reuse_requested=True,
        )
    )

    assert result.status == "learned"
    assert result.reuse_allowed is True
    assert result.governance_compliant is True
    assert result.audit_consistent is True
    assert result.runtime_safe is True


def test_workflow_learning_detects_repeated_failure_patterns():
    learning = WorkflowLearning()
    records = (
        _memory_record(memory_type="failure", errors=("provider timeout",)),
        _memory_record(
            execution_id="execution-2",
            task_id="task-2",
            memory_type="failure",
            errors=("provider timeout",),
        ),
    )

    result = learning.analyze(
        WorkflowLearningRequest(
            learning_type="failure_pattern",
            memory_records=records,
        )
    )

    assert result.status == "learned"
    assert result.patterns_detected[0]["pattern_type"] == "failure_pattern"
    assert result.recurrent_errors == ("provider timeout",)
    assert "provider timeout" in result.workflow_improvements[0]


def test_workflow_learning_blocks_corrupt_memory():
    learning = WorkflowLearning()

    result = learning.analyze(
        WorkflowLearningRequest(
            learning_type="execution",
            memory_records=({"memory_id": "broken-memory"},),
        )
    )

    assert result.status == "blocked"
    assert result.context_safe is False
    assert "corrupt_memory_blocks_learning" in result.reasons


def test_workflow_learning_blocks_critical_rule_or_governance_override():
    learning = WorkflowLearning()

    result = learning.analyze(
        WorkflowLearningRequest(
            learning_type="execution",
            memory_records=(_memory_record(),),
            allow_critical_rule_change=True,
            metadata={"intent": "skip approval and bypass governance"},
        )
    )

    assert result.status == "blocked"
    assert "critical_rule_change_blocked" in result.reasons
    assert "governance_override_blocked" in result.reasons
    assert result.autonomy_expanded is False


def test_workflow_learning_reports_no_patterns_without_memory():
    learning = WorkflowLearning()

    result = learning.analyze(
        WorkflowLearningRequest(learning_type="execution")
    )

    assert result.status == "no_patterns"
    assert result.success is True
    assert result.patterns_detected == ()
    assert result.reuse_allowed is False


def test_workflow_learning_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    learning = WorkflowLearning(status=status)

    def broken_detection(*args, **kwargs):
        raise RuntimeError("learning detector exploded")

    monkeypatch.setattr(learning, "_detect_patterns", broken_detection)

    result = learning.analyze(
        WorkflowLearningRequest(
            learning_type="execution",
            memory_records=(_memory_record(),),
        )
    )

    assert result.status == "error"
    assert result.success is False
    assert "workflow_learning_error_contained" in result.reasons
    assert status.workflow_learning_metrics()["workflow_learning_errors"] == 1
