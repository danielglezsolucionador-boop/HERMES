from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.models.task import Task
from app.runner.task_execution import TaskExecutionRuntime
from app.runner.timeout_control import TimeoutControl


def _claimed_task() -> Task:
    return Task(
        id=uuid4(),
        title="timeout control task",
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
        max_duration_seconds=5,
    )
    prepared = runtime.prepare(_claimed_task())
    started = runtime.start(prepared.context)
    return started.context


def _control(**kwargs) -> TimeoutControl:
    return TimeoutControl(runtime_owner="runner-test:runtime-test", **kwargs)


@pytest.mark.asyncio
async def test_timeout_control_allows_clear_runtime_without_active_execution():
    control = _control()

    result = await control.inspect(
        execution_visibility={
            "active_executions": 0,
            "active_contexts": [],
        }
    )

    assert result.status == "clear"
    assert result.success is True
    assert result.timeout_state == "ready"
    assert result.runtime_protected is True
    assert result.timeout_detected is False
    assert result.active_timeout_checks == 0


def test_timeout_control_tracks_active_execution_duration():
    context = _started_context()
    control = _control(max_execution_duration_seconds=5)

    result = control.evaluate(
        execution_visibility={
            "active_executions": 1,
            "max_duration_seconds": 5,
            "active_contexts": [context.to_dict()],
        }
    )

    assert result.status == "tracking"
    assert result.timeout_state == "tracking"
    assert result.duration_tracking is True
    assert result.execution_id == context.execution_id
    assert result.runtime_owner == "runner-test:runtime-test"
    assert result.timeout_threshold_ms == 5000
    assert result.current_runtime_duration_ms >= 0
    assert result.reasons == ()


def test_timeout_control_detects_timeout_without_recovery(caplog):
    context = replace(
        _started_context(),
        started_at=(datetime.now(timezone.utc) - timedelta(seconds=3)).isoformat(),
        max_duration_seconds=1,
    )
    control = _control(max_execution_duration_seconds=1)

    result = control.evaluate(
        execution_visibility={
            "active_executions": 1,
            "max_duration_seconds": 1,
            "active_contexts": [context.to_dict()],
        }
    )

    assert result.status == "timeout_detected"
    assert result.timeout_state == "detected"
    assert result.timeout_detected is True
    assert result.timeout_registered is True
    assert result.timeout_id is not None
    assert result.detected_at is not None
    assert result.current_runtime_duration_ms >= 3000
    assert "execution_timeout_detected" in result.reasons
    assert "timeout_control: timeout detected" in caplog.text


def test_timeout_control_rejects_orphan_and_mismatched_execution():
    control = _control()

    result = control.evaluate(
        execution_visibility={
            "active_contexts": [
                {
                    "execution_id": "execution-1",
                    "task_id": "task-1",
                    "runtime_id": "foreign-runtime",
                    "runtime_owner": "other:foreign-runtime",
                    "execution_state": "executing",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "max_duration_seconds": 5,
                }
            ]
        }
    )

    assert result.status == "rejected"
    assert result.monitoring_allowed is False
    assert result.ownership_consistent is False
    assert result.linkage_valid is True
    assert "runtime_owner_mismatch" in result.reasons


def test_timeout_control_rejects_invalid_execution_linkage():
    control = _control()

    result = control.evaluate(
        execution_visibility={
            "active_contexts": [
                {
                    "execution_state": "claimed",
                    "started_at": "not-a-date",
                    "max_duration_seconds": 5,
                }
            ]
        }
    )

    assert result.status == "rejected"
    assert result.linkage_valid is False
    assert "missing_execution_id" in result.reasons
    assert "missing_task_id" in result.reasons
    assert "missing_runtime_id" in result.reasons
    assert "missing_runtime_owner" in result.reasons
    assert "invalid_execution_started_at" in result.reasons
    assert "invalid_execution_state" in result.reasons


def test_timeout_control_enforces_runtime_limits(monkeypatch):
    context = _started_context()
    control = _control(
        max_concurrent_timeout_checks=1,
        max_runtime_timeout_load=0.5,
    )
    control._active_timeout_checks = 1

    concurrency = control.evaluate(
        execution_visibility={"active_contexts": [context.to_dict()]}
    )

    assert concurrency.status == "rejected"
    assert "max_concurrent_timeout_checks_reached" in concurrency.reasons

    overhead_limited = _control(max_check_duration_ms=1)
    monkeypatch.setattr(overhead_limited, "_duration_ms", lambda started: 2)
    overhead = overhead_limited.evaluate(
        execution_visibility={"active_contexts": [context.to_dict()]}
    )

    assert overhead.status == "rejected"
    assert "timeout_control_overhead_exceeded" in overhead.reasons


def test_timeout_control_contains_internal_errors(monkeypatch):
    control = _control()

    def broken_contexts(visibility, execution_context):
        raise RuntimeError("timeout context failure")

    monkeypatch.setattr(control, "_contexts", broken_contexts)
    result = control.evaluate(execution_visibility={"active_contexts": []})

    assert result.status == "error"
    assert result.timeout_state == "error"
    assert result.runtime_protected is True
    assert result.active_timeout_checks == 0
    assert "timeout_control_error_contained" in result.reasons
