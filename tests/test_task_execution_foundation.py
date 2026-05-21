from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.models.task import Task
from app.runner.task_execution import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_EXECUTING,
    TaskExecutionRuntime,
)


def _claimed_task(
    runner_id: str = "runner-test",
    runtime_id: str = "runtime-test",
    status: str = "claimed",
    claim_state: str | None = "claimed",
) -> Task:
    return Task(
        id=uuid4(),
        title="execution foundation task",
        status=status,
        phase="test",
        runner_id=runner_id,
        runtime_id=runtime_id,
        claim_state=claim_state,
        claimed_at=datetime.now(timezone.utc),
        claim_attempts=1,
    )


def _runtime(**kwargs) -> TaskExecutionRuntime:
    return TaskExecutionRuntime(
        runner_id="runner-test",
        runtime_id="runtime-test",
        memory_usage_provider=lambda: 64,
        **kwargs,
    )


def test_task_execution_prepares_eligible_claimed_task_context():
    runtime = _runtime()

    result = runtime.prepare(_claimed_task())

    assert result.status == "prepared"
    assert result.eligible is True
    assert result.context is not None
    assert result.context.execution_id
    assert result.context.execution_state == "claimed"
    assert result.context.runtime_owner == "runner-test:runtime-test"


def test_task_execution_rejects_invalid_ownership_and_claim_state():
    runtime = _runtime()

    result = runtime.prepare(
        _claimed_task(
            runner_id="other-runner",
            runtime_id="other-runtime",
            claim_state=None,
        )
    )

    assert result.status == "rejected"
    assert result.eligible is False
    assert "invalid_runner_owner" in result.reasons
    assert "invalid_runtime_owner" in result.reasons
    assert "invalid_claim_state" in result.reasons


def test_task_execution_rejects_unclaimed_or_inactive_runtime():
    runtime = _runtime()

    result = runtime.prepare(_claimed_task(status="pending"), runtime_active=False)

    assert result.status == "rejected"
    assert "runtime_inactive" in result.reasons
    assert "task_not_claimed" in result.reasons


def test_task_execution_lifecycle_claimed_to_executing_to_completed():
    runtime = _runtime()

    prepared = runtime.prepare(_claimed_task())
    started = runtime.start(prepared.context)
    completed = runtime.complete(started.context)

    assert started.status == "started"
    assert started.context.execution_state == EXECUTION_STATE_EXECUTING
    assert started.context.started_at is not None
    assert completed.status == "completed"
    assert completed.context.execution_state == EXECUTION_STATE_COMPLETED
    assert completed.context.finished_at is not None
    assert runtime.visibility()["active_executions"] == 0


def test_task_execution_rejects_invalid_lifecycle_transition():
    runtime = _runtime()
    prepared = runtime.prepare(_claimed_task())

    result = runtime.complete(prepared.context)

    assert result.status == "rejected"
    assert "complete_requires_executing_state" in result.reasons


def test_task_execution_limits_concurrent_execution():
    runtime = _runtime(max_concurrent_executions=1)
    first = runtime.prepare(_claimed_task())
    runtime.start(first.context)

    second = runtime.prepare(_claimed_task())

    assert second.status == "rejected"
    assert "max_concurrent_executions_reached" in second.reasons


def test_task_execution_limits_duration_without_recovery():
    runtime = _runtime(max_duration_seconds=1)
    prepared = runtime.prepare(_claimed_task())
    started = runtime.start(prepared.context)
    old_context = replace(
        started.context,
        started_at=(datetime.now(timezone.utc) - timedelta(seconds=2)).isoformat(),
    )

    result = runtime.check_duration(old_context)

    assert result.status == "rejected"
    assert "max_execution_duration_exceeded" in result.reasons


def test_task_execution_limits_runtime_load_and_memory():
    high_load = TaskExecutionRuntime(
        runner_id="runner-test",
        runtime_id="runtime-test",
        max_runtime_load=0.5,
        max_memory_mb=32,
        runtime_load_provider=lambda: 0.9,
        memory_usage_provider=lambda: 64,
    )

    result = high_load.prepare(_claimed_task())

    assert result.status == "rejected"
    assert "max_runtime_load_reached" in result.reasons
    assert "max_execution_memory_reached" in result.reasons


def test_task_execution_contains_execution_errors():
    runtime = _runtime()
    prepared = runtime.prepare(_claimed_task())
    started = runtime.start(prepared.context)

    result = runtime.fail(started.context, "provider bridge unavailable")

    assert result.status == "error"
    assert result.error == "provider bridge unavailable"
    assert "execution_error_contained" in result.reasons
    assert runtime.visibility()["active_executions"] == 0
