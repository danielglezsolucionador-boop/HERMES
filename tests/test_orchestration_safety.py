import logging
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.task import Task
from app.runner.orchestration_foundation import OrchestrationRuntime
from app.runner.orchestration_safety import OrchestrationSafety
from app.runner.task_execution import TaskExecutionRuntime


def _claimed_task() -> Task:
    return Task(
        id=uuid4(),
        title="orchestration safety task",
        status="claimed",
        phase="test",
        runner_id="runner-test",
        runtime_id="runtime-test",
        claim_state="claimed",
        claimed_at=datetime.now(timezone.utc),
        claim_attempts=1,
    )


def _claimed_context():
    runtime = TaskExecutionRuntime(
        runner_id="runner-test",
        runtime_id="runtime-test",
    )
    return runtime.prepare(_claimed_task()).context


def _dependency(
    dependency_id: str = "dependency-1",
    state: str = "completed",
    order: int = 1,
) -> dict:
    return {
        "dependency_id": dependency_id,
        "execution_id": f"execution-{dependency_id}",
        "task_id": f"task-{dependency_id}",
        "state": state,
        "execution_order": order,
    }


def _runtime(**kwargs) -> OrchestrationRuntime:
    return OrchestrationRuntime(
        runtime_owner="runner-test:runtime-test",
        **kwargs,
    )


def test_orchestration_safety_allows_idle_runtime():
    runtime = _runtime()
    safety = OrchestrationSafety()
    result = runtime.evaluate()

    safety_result = safety.evaluate(
        orchestration_result=result,
        orchestration_visibility=runtime.visibility(),
    )

    assert safety_result.status == "safe"
    assert safety_result.allows_orchestration is True
    assert safety_result.runtime_protected is True
    assert safety_result.active_orchestrations == 0
    assert safety_result.reasons == ()


def test_orchestration_safety_detects_conflict_corruption_and_sequence(caplog):
    caplog.set_level(logging.WARNING)
    runtime = _runtime()
    context = _claimed_context()
    self_dependency = _dependency(order=2)
    self_dependency["execution_id"] = context.execution_id
    duplicate_dependency = _dependency(order=1)

    orchestration_result = runtime.evaluate(
        execution_context=context,
        dependencies=[self_dependency, duplicate_dependency],
        execution_order=2,
    )
    safety_result = OrchestrationSafety().evaluate(
        orchestration_result=orchestration_result,
        orchestration_visibility=runtime.visibility(),
    )

    assert safety_result.status == "blocked"
    assert safety_result.allows_orchestration is False
    assert safety_result.conflict_detected is True
    assert safety_result.dependency_corruption_detected is True
    assert safety_result.sequencing_violation_detected is True
    assert "dependency_self_reference" in safety_result.reasons
    assert "duplicate_dependency" in safety_result.reasons
    assert "invalid_execution_sequence" in safety_result.reasons
    assert "orchestration_safety: blocked" in caplog.text


def test_orchestration_safety_detects_runaway_visibility():
    safety = OrchestrationSafety()
    result = {
        "status": "registered",
        "success": True,
        "dependency_count": 12,
        "max_execution_dependencies": 10,
        "active_orchestrations": 3,
        "max_active_orchestrations": 1,
        "runtime_orchestration_load": 2.0,
        "max_orchestration_load": 1.0,
    }

    safety_result = safety.evaluate(
        orchestration_result=result,
        orchestration_visibility={
            "active_orchestrations": 3,
            "max_active_orchestrations": 1,
            "runtime_orchestration_load": 2.0,
            "max_orchestration_load": 1.0,
            "max_execution_dependencies": 10,
        },
    )

    assert safety_result.status == "blocked"
    assert safety_result.runaway_detected is True
    assert "orchestration_saturation_detected" in safety_result.reasons
    assert "orchestration_load_degraded" in safety_result.reasons
    assert "dependency_runaway_detected" in safety_result.reasons


def test_orchestration_safety_detects_timeout_and_retry_limit():
    safety = OrchestrationSafety(max_retries=1)
    result = {
        "status": "coordinating",
        "coordination_duration_ms": 2000,
        "max_orchestration_duration_ms": 1000,
        "coordination_overhead_ms": 500,
        "max_coordination_overhead_ms": 250,
        "metadata": {"orchestration_retry_attempts": 1},
    }

    safety_result = safety.evaluate(orchestration_result=result)

    assert safety_result.status == "blocked"
    assert safety_result.timeout_detected is True
    assert safety_result.retry_allowed is False
    assert safety_result.retry_attempts == 1
    assert "orchestration_timeout_detected" in safety_result.reasons
    assert "coordination_overhead_exceeded" in safety_result.reasons
    assert "max_orchestration_safety_retries_reached" in safety_result.reasons


def test_orchestration_safety_contains_internal_errors(monkeypatch):
    safety = OrchestrationSafety()

    def broken_dependencies(result):
        raise RuntimeError("orchestration safety failure")

    monkeypatch.setattr(safety, "_dependencies", broken_dependencies)
    result = safety.evaluate(orchestration_result={"status": "registered"})

    assert result.status == "error"
    assert result.runtime_protected is True
    assert result.allows_orchestration is False
    assert "orchestration_safety_error_contained" in result.reasons
