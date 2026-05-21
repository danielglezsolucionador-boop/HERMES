from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.models.task import Task
from app.runner.execution_safety import ExecutionSafety
from app.runner.provider_bridge import ProviderBridgeResult
from app.runner.task_execution import TaskExecutionRuntime


def _claimed_task() -> Task:
    return Task(
        id=uuid4(),
        title="execution safety task",
        status="claimed",
        phase="test",
        runner_id="runner-test",
        runtime_id="runtime-test",
        claim_state="claimed",
        claimed_at=datetime.now(timezone.utc),
        claim_attempts=1,
    )


def _started_context():
    runtime = TaskExecutionRuntime(
        runner_id="runner-test",
        runtime_id="runtime-test",
        memory_usage_provider=lambda: 64,
    )
    prepared = runtime.prepare(_claimed_task())
    started = runtime.start(prepared.context)
    return started.context


@pytest.mark.asyncio
async def test_execution_safety_allows_empty_stable_runtime():
    safety = ExecutionSafety()

    result = await safety.inspect()

    assert result.status == "safe"
    assert result.allows_execution is True
    assert result.runtime_protected is True
    assert result.reasons == ()


def test_execution_safety_detects_double_execution_conflict():
    context = _started_context()
    duplicated_context = replace(context, execution_id="execution-2")
    safety = ExecutionSafety(max_concurrent_executions=1)

    result = safety.evaluate(
        execution_visibility={
            "active_executions": 2,
            "max_concurrent_executions": 1,
            "active_contexts": [
                context.to_dict(),
                duplicated_context.to_dict(),
            ],
        }
    )

    assert result.status == "blocked"
    assert result.allows_execution is False
    assert result.conflict_detected is True
    assert "execution_overlap_detected" in result.reasons
    assert "duplicate_task_execution_detected" in result.reasons


def test_execution_safety_detects_timeout_without_recovery():
    context = replace(
        _started_context(),
        started_at=(datetime.now(timezone.utc) - timedelta(seconds=3)).isoformat(),
        max_duration_seconds=1,
    )
    safety = ExecutionSafety(max_duration_seconds=1)

    result = safety.evaluate(
        execution_visibility={
            "active_executions": 1,
            "max_concurrent_executions": 1,
            "max_duration_seconds": 1,
            "active_contexts": [context.to_dict()],
        }
    )

    assert result.status == "blocked"
    assert result.timeout_detected is True
    assert "stale_execution_detected" in result.reasons


def test_execution_safety_detects_runtime_degradation():
    safety = ExecutionSafety(max_runtime_load=0.5, max_memory_mb=32)

    result = safety.evaluate(
        execution_visibility={
            "runtime_load": 0.9,
            "max_runtime_load": 0.5,
            "memory_usage_mb": 64,
            "max_memory_mb": 32,
        }
    )

    assert result.status == "blocked"
    assert "runtime_load_degraded" in result.reasons
    assert "runtime_memory_degraded" in result.reasons


def test_execution_safety_detects_provider_failure_and_saturation():
    safety = ExecutionSafety(max_concurrent_provider_calls=1)
    provider_result = ProviderBridgeResult(
        status="provider_error",
        success=False,
        provider_name="fake",
        reasons=("provider_error",),
        error="provider unavailable",
        active_provider_calls=2,
        max_concurrent_provider_calls=1,
    )

    result = safety.evaluate(
        provider_result=provider_result,
        provider_visibility={
            "active_provider_calls": 2,
            "max_concurrent_provider_calls": 1,
        },
    )

    assert result.status == "blocked"
    assert result.provider_failure_detected is True
    assert "provider_error_detected" in result.reasons
    assert "provider_saturation_detected" in result.reasons


def test_execution_safety_limits_retry_without_autonomous_retry():
    safety = ExecutionSafety(max_retries=2)

    result = safety.evaluate(retry_attempts=2)

    assert result.status == "blocked"
    assert result.retry_allowed is False
    assert "max_execution_retries_reached" in result.reasons


def test_execution_safety_contains_internal_errors(monkeypatch):
    safety = ExecutionSafety()

    def broken_contexts(visibility):
        raise RuntimeError("simulated safety failure")

    monkeypatch.setattr(safety, "_contexts", broken_contexts)
    result = safety.evaluate(execution_visibility={"active_contexts": []})

    assert result.status == "error"
    assert result.allows_execution is False
    assert result.runtime_protected is True
    assert "execution_safety_error_contained" in result.reasons
