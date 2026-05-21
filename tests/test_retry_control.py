import logging
from uuid import uuid4

import pytest

from app.models.task import Task
from app.runner.retry_control import RetryControl


def _failed_task(
    retry_count: int = 0,
    max_retries: int = 3,
    error: str = "provider timeout",
) -> Task:
    return Task(
        id=uuid4(),
        title="retry control task",
        status="failed",
        phase="test",
        error=error,
        retry_count=retry_count,
        max_retries=max_retries,
        runner_id="runner-test",
        runtime_id="runtime-test",
    )


def _control(**kwargs) -> RetryControl:
    return RetryControl(runtime_owner="runner-test:runtime-test", **kwargs)


@pytest.mark.asyncio
async def test_retry_control_idle_runtime_ready():
    control = _control()

    result = await control.inspect()

    assert result.status == "idle"
    assert result.success is True
    assert result.retry_state == "ready"
    assert result.retry_allowed is True
    assert result.runtime_protected is True
    assert result.active_retries == 0


def test_retry_control_registers_eligible_failed_task_without_requeue(caplog):
    caplog.set_level(logging.INFO)
    control = _control()
    task = _failed_task(retry_count=1, max_retries=3)

    result = control.evaluate(task=task, retry_reason="temporary_failure")

    assert result.status == "registered"
    assert result.retry_state == "registered"
    assert result.retry_registered is True
    assert result.retry_started is True
    assert result.retry_id is not None
    assert result.retry_attempt == 2
    assert result.retry_threshold == 3
    assert result.retry_reason == "temporary_failure"
    assert result.task_id == str(task.id)
    assert result.runtime_owner == "runner-test:runtime-test"
    assert result.active_retries == 1
    assert "retry_control: registered" in caplog.text

    completed = control.complete(result)
    assert completed.status == "completed"
    assert completed.retry_completed is True
    assert completed.active_retries == 0


def test_retry_control_rejects_retry_threshold():
    control = _control()
    task = _failed_task(retry_count=3, max_retries=3)

    result = control.evaluate(task=task, retry_reason="threshold_check")

    assert result.status == "rejected"
    assert result.retry_allowed is False
    assert result.threshold_valid is True
    assert result.retry_attempt == 4
    assert result.retry_threshold == 3
    assert "max_retry_attempts_reached" in result.reasons
    assert result.active_retries == 0


def test_retry_control_rejects_provider_unavailable_and_orphan_retry():
    control = _control()
    unavailable = control.evaluate(
        task=_failed_task(),
        provider_available=False,
        retry_reason="provider_unavailable",
    )

    assert unavailable.status == "rejected"
    assert unavailable.provider_available is False
    assert "provider_unavailable" in unavailable.reasons

    orphan = control.evaluate(retry_reason="manual_retry")

    assert orphan.status == "rejected"
    assert orphan.linkage_valid is False
    assert "missing_task_id" in orphan.reasons
    assert "missing_failed_execution_signal" in orphan.reasons


def test_retry_control_flow_start_complete_and_fail():
    control = _control()

    registered = control.evaluate(
        task=_failed_task(),
        retry_reason="transient_provider_error",
    )
    executing = control.start(registered)
    completed = control.complete(executing)

    assert executing.status == "executing"
    assert executing.retry_state == "executing"
    assert completed.status == "completed"
    assert completed.retry_completed is True
    assert completed.active_retries == 0

    registered_again = control.evaluate(
        task=_failed_task(),
        retry_reason="transient_provider_error",
    )
    executing_again = control.start(registered_again)
    failed = control.fail(executing_again, "provider still unavailable")

    assert failed.status == "failed"
    assert failed.success is False
    assert failed.retry_failed is True
    assert failed.active_retries == 0
    assert "retry_execution_failed" in failed.reasons
    assert failed.error == "provider still unavailable"


def test_retry_control_enforces_runtime_limits(monkeypatch):
    control = _control(
        max_concurrent_retries=1,
        max_runtime_retry_load=0.5,
    )
    control._active_retries = 1

    concurrency = control.evaluate(
        task=_failed_task(),
        retry_reason="limit_check",
    )

    assert concurrency.status == "rejected"
    assert "max_concurrent_retries_reached" in concurrency.reasons
    assert "max_runtime_retry_load_reached" in concurrency.reasons

    overhead_limited = _control(max_retry_overhead_ms=1)
    monkeypatch.setattr(overhead_limited, "_duration_ms", lambda started: 2)
    overhead = overhead_limited.evaluate(
        task=_failed_task(),
        retry_reason="overhead_check",
    )

    assert overhead.status == "rejected"
    assert "retry_control_overhead_exceeded" in overhead.reasons


def test_retry_control_contains_internal_errors(monkeypatch):
    control = _control()

    def broken_context(*args, **kwargs):
        raise RuntimeError("retry context failure")

    monkeypatch.setattr(control, "_retry_context", broken_context)
    result = control.evaluate(task=_failed_task(), retry_reason="boom")

    assert result.status == "error"
    assert result.retry_state == "error"
    assert result.runtime_protected is True
    assert result.active_retries == 0
    assert "retry_control_error_contained" in result.reasons
