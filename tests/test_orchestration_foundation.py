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
        title="orchestration task",
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
    prepared = runtime.prepare(_claimed_task())
    return prepared.context


def _dependency(state: str = "completed") -> dict:
    return {
        "dependency_id": "dependency-1",
        "execution_id": "execution-previous",
        "task_id": "task-previous",
        "state": state,
        "execution_order": 1,
    }


def _runtime(**kwargs) -> OrchestrationRuntime:
    return OrchestrationRuntime(
        runtime_owner="runner-test:runtime-test",
        **kwargs,
    )


@pytest.mark.asyncio
async def test_orchestration_idle_runtime_ready():
    runtime = _runtime()

    result = await runtime.inspect()

    assert result.status == "idle"
    assert result.success is True
    assert result.orchestration_state == "ready"
    assert result.dependency_state == "clear"
    assert result.coordination_allowed is True
    assert result.runtime_protected is True
    assert result.active_orchestrations == 0


def test_orchestration_registers_claimed_execution_with_dependencies(caplog):
    caplog.set_level(logging.INFO)
    runtime = _runtime()
    context = _claimed_context()

    result = runtime.evaluate(
        execution_context=context,
        dependencies=[_dependency()],
        execution_order=2,
        metadata={"source": "test"},
    )

    assert result.status == "registered"
    assert result.orchestration_state == "registered"
    assert result.dependency_state == "satisfied"
    assert result.orchestration_registered is True
    assert result.orchestration_id is not None
    assert result.execution_id == context.execution_id
    assert result.execution_order == 2
    assert result.dependency_count == 1
    assert result.runtime_owner == "runner-test:runtime-test"
    assert result.active_orchestrations == 1
    assert "orchestration coordination: registered" in caplog.text

    started = runtime.start(result)
    released = runtime.release(started)

    assert started.status == "coordinating"
    assert started.coordination_started is True
    assert released.status == "released"
    assert released.execution_released is True
    assert released.coordination_completed is True
    assert released.active_orchestrations == 0


def test_orchestration_rejects_orphan_dependency_and_invalid_execution():
    runtime = _runtime()

    result = runtime.evaluate(
        dependencies=[{"state": "completed"}],
        execution_order=1,
    )

    assert result.status == "rejected"
    assert result.coordination_allowed is False
    assert result.linkage_valid is False
    assert result.dependency_valid is False
    assert "missing_execution_id" in result.reasons
    assert "missing_task_id" in result.reasons
    assert "orphan_dependency" in result.reasons


def test_orchestration_rejects_unsatisfied_dependency_and_owner_mismatch():
    runtime = _runtime()
    context = _claimed_context().to_dict()
    context["runtime_owner"] = "other-runner:other-runtime"

    result = runtime.evaluate(
        execution_context=context,
        dependencies=[_dependency(state="pending")],
        execution_order=1,
    )

    assert result.status == "rejected"
    assert result.conflict_detected is True
    assert result.ownership_consistent is False
    assert result.dependency_valid is False
    assert result.dependency_state == "blocked"
    assert "runtime_owner_mismatch" in result.reasons
    assert "dependency_unsatisfied" in result.reasons


def test_orchestration_enforces_runtime_limits(monkeypatch):
    context = _claimed_context()
    runtime = _runtime(
        max_active_orchestrations=1,
        max_orchestration_load=0.5,
        max_execution_dependencies=1,
    )
    runtime._active_orchestrations = 1

    limited = runtime.evaluate(
        execution_context=context,
        dependencies=[_dependency(), {**_dependency(), "dependency_id": "dependency-2"}],
        execution_order=1,
    )

    assert limited.status == "rejected"
    assert "max_active_orchestrations_reached" in limited.reasons
    assert "max_orchestration_load_reached" in limited.reasons
    assert "max_execution_dependencies_reached" in limited.reasons

    overhead_limited = _runtime(max_coordination_overhead_ms=1)
    monkeypatch.setattr(overhead_limited, "_duration_ms", lambda started: 2)
    overhead = overhead_limited.evaluate(
        execution_context=context,
        dependencies=[_dependency()],
        execution_order=1,
    )

    assert overhead.status == "rejected"
    assert "coordination_overhead_exceeded" in overhead.reasons


def test_orchestration_contains_internal_errors(monkeypatch):
    runtime = _runtime()

    def broken_context(*args, **kwargs):
        raise RuntimeError("orchestration context failure")

    monkeypatch.setattr(runtime, "_orchestration_context", broken_context)
    result = runtime.evaluate(execution_context=_claimed_context())

    assert result.status == "error"
    assert result.orchestration_state == "error"
    assert result.runtime_protected is True
    assert result.active_orchestrations == 0
    assert "orchestration_error_contained" in result.reasons
