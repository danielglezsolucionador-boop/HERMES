import logging
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.task import Task
from app.runner.orchestration_foundation import OrchestrationRuntime
from app.runner.task_execution import TaskExecutionRuntime


def _claimed_task() -> Task:
    return Task(
        id=uuid4(),
        title="coordination task",
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
    state: str = "completed",
    order: int = 1,
    dependency_id: str = "dependency-1",
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


@pytest.mark.asyncio
async def test_coordination_flow_releases_valid_execution(caplog):
    caplog.set_level(logging.INFO)
    runtime = _runtime()
    context = _claimed_context()

    result = await runtime.coordinate(
        execution_context=context,
        dependencies=[_dependency(order=1)],
        execution_order=2,
    )

    assert result.status == "released"
    assert result.success is True
    assert result.coordination_id is not None
    assert result.coordination_state == "released"
    assert result.dependency_status == "satisfied"
    assert result.execution_sequence == 2
    assert result.coordination_completed is True
    assert result.execution_released is True
    assert result.active_orchestrations == 0
    assert "orchestration coordination: started" in caplog.text
    assert "orchestration coordination: completed" in caplog.text


def test_coordination_rejects_invalid_dependency_sequence():
    runtime = _runtime()
    context = _claimed_context()

    result = runtime.evaluate(
        execution_context=context,
        dependencies=[_dependency(order=2)],
        execution_order=2,
    )

    assert result.status == "rejected"
    assert result.coordination_allowed is False
    assert result.sequencing_valid is False
    assert result.conflict_detected is True
    assert "invalid_execution_sequence" in result.reasons


def test_coordination_rejects_duplicate_and_self_dependency():
    runtime = _runtime()
    context = _claimed_context()
    self_dependency = _dependency(order=1)
    self_dependency["execution_id"] = context.execution_id
    duplicate_dependency = _dependency(order=1)

    result = runtime.evaluate(
        execution_context=context,
        dependencies=[self_dependency, duplicate_dependency],
        execution_order=3,
    )

    assert result.status == "rejected"
    assert result.dependency_valid is False
    assert result.sequencing_valid is False
    assert "dependency_self_reference" in result.reasons
    assert "duplicate_dependency" in result.reasons


def test_coordination_enforces_dependency_chain_limit():
    runtime = _runtime(max_dependency_chain=2)
    context = _claimed_context()
    dependency = _dependency(order=1)
    dependency["dependency_chain"] = ["root", "middle", "leaf"]

    result = runtime.evaluate(
        execution_context=context,
        dependencies=[dependency],
        execution_order=4,
    )

    assert result.status == "rejected"
    assert result.dependency_valid is False
    assert result.max_dependency_chain == 2
    assert "max_dependency_chain_reached" in result.reasons


@pytest.mark.asyncio
async def test_coordination_contains_lifecycle_error(monkeypatch):
    runtime = _runtime()

    def broken_start(result):
        raise RuntimeError("coordination lifecycle failure")

    monkeypatch.setattr(runtime, "start", broken_start)
    result = await runtime.coordinate(
        execution_context=_claimed_context(),
        dependencies=[_dependency(order=1)],
        execution_order=2,
    )

    assert result.status == "error"
    assert result.runtime_protected is True
    assert result.active_orchestrations == 0
    assert "coordination_error_contained" in result.reasons
