import asyncio

import pytest

from app.runner.runtime_loop import RuntimeLoop
from app.services.runtime_status import RuntimeStatus


async def no_pending_tasks() -> int:
    return 0


@pytest.mark.asyncio
async def test_runtime_loop_heartbeat_pause_resume_and_stop():
    status = RuntimeStatus()
    loop = RuntimeLoop(
        status=status,
        interval_seconds=0.01,
        min_interval_seconds=0.01,
        heartbeat_log_every=1000,
        pending_task_counter=no_pending_tasks,
    )

    task = asyncio.create_task(loop.run())
    await asyncio.sleep(0.04)

    running = status.runtime_loop_metrics()
    safety = status.safety_metrics()
    assert running["alive"] is True
    assert running["status"] == "healthy"
    assert running["state"] == "active"
    assert running["iteration"] > 0
    assert running["last_heartbeat_at"] is not None
    assert safety["runtime_safe"] is True
    assert safety["consecutive_errors"] == 0
    assert safety["degraded_state"] is False

    loop.pause()
    await asyncio.sleep(0.02)
    assert status.runtime_loop_metrics()["state"] == "paused"

    loop.resume()
    await asyncio.sleep(0.02)
    assert status.runtime_loop_metrics()["state"] == "active"

    loop.request_stop("test_stop")
    await asyncio.wait_for(task, timeout=1)

    stopped = status.runtime_loop_metrics()
    assert stopped["alive"] is False
    assert stopped["state"] == "stopped"
    assert stopped["stop_requested"] is True
    assert stopped["stop_reason"] == "test_stop"


@pytest.mark.asyncio
async def test_runtime_loop_survives_cycle_error_without_busy_loop():
    class FailingOnceLoop(RuntimeLoop):
        def __init__(self, status: RuntimeStatus) -> None:
            super().__init__(
                status=status,
                interval_seconds=0.01,
                min_interval_seconds=0.01,
                heartbeat_log_every=1000,
                pending_task_counter=no_pending_tasks,
            )
            self.calls = 0

        async def _cycle(self) -> str:
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("simulated runtime cycle failure")
            return await super()._cycle()

    status = RuntimeStatus()
    loop = FailingOnceLoop(status=status)
    task = asyncio.create_task(loop.run())
    await asyncio.sleep(0.04)
    loop.request_stop("test_stop")
    await asyncio.wait_for(task, timeout=1)

    metrics = status.runtime_loop_metrics()
    assert loop.calls > 1
    assert metrics["iteration"] > 1
    assert metrics["interval_seconds"] == 0.01
    assert metrics["stop_reason"] == "test_stop"


@pytest.mark.asyncio
async def test_runtime_loop_polling_detects_pending_tasks():
    async def three_pending_tasks() -> int:
        return 3

    status = RuntimeStatus()
    loop = RuntimeLoop(
        status=status,
        interval_seconds=0.01,
        min_interval_seconds=0.01,
        heartbeat_log_every=1000,
        pending_task_counter=three_pending_tasks,
    )

    task = asyncio.create_task(loop.run())
    await asyncio.sleep(0.03)
    loop.request_stop("test_stop")
    await asyncio.wait_for(task, timeout=1)

    polling = status.polling_metrics()
    assert polling["last_poll_time"] is not None
    assert polling["polling_iteration"] > 0
    assert polling["tasks_detected"] == 3
    assert polling["polling_status"] == "stopped"
    assert polling["polling_errors"] == 0


@pytest.mark.asyncio
async def test_runtime_loop_polling_handles_empty_queue():
    status = RuntimeStatus()
    loop = RuntimeLoop(
        status=status,
        interval_seconds=0.01,
        min_interval_seconds=0.01,
        heartbeat_log_every=1000,
        pending_task_counter=no_pending_tasks,
    )

    task = asyncio.create_task(loop.run())
    await asyncio.sleep(0.03)
    polling_during_run = status.polling_metrics()
    loop.request_stop("test_stop")
    await asyncio.wait_for(task, timeout=1)

    assert polling_during_run["tasks_detected"] == 0
    assert polling_during_run["polling_status"] == "idle"
    assert polling_during_run["polling_errors"] == 0


@pytest.mark.asyncio
async def test_runtime_loop_polling_error_is_contained():
    calls = 0

    async def fails_once_then_empty() -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("simulated polling failure")
        return 0

    status = RuntimeStatus()
    loop = RuntimeLoop(
        status=status,
        interval_seconds=0.01,
        min_interval_seconds=0.01,
        heartbeat_log_every=1000,
        pending_task_counter=fails_once_then_empty,
    )

    task = asyncio.create_task(loop.run())
    await asyncio.sleep(0.04)
    loop.request_stop("test_stop")
    await asyncio.wait_for(task, timeout=1)

    polling = status.polling_metrics()
    assert calls > 1
    assert polling["polling_iteration"] > 1
    assert polling["tasks_detected"] == 0
    assert polling["polling_errors"] == 1


@pytest.mark.asyncio
async def test_runtime_loop_safety_stops_after_consecutive_errors():
    async def always_fails() -> int:
        raise RuntimeError("persistent polling failure")

    status = RuntimeStatus()
    loop = RuntimeLoop(
        status=status,
        interval_seconds=0.01,
        min_interval_seconds=0.01,
        heartbeat_log_every=1000,
        pending_task_counter=always_fails,
        degraded_error_threshold=2,
        max_consecutive_errors=3,
        safety_event_limit=5,
    )

    task = asyncio.create_task(loop.run())
    await asyncio.wait_for(task, timeout=1)

    safety = status.safety_metrics()
    runtime = status.runtime_loop_metrics()
    assert safety["runtime_safe"] is False
    assert safety["consecutive_errors"] == 3
    assert safety["degraded_state"] is True
    assert safety["stop_reason"] == "max_consecutive_errors"
    assert runtime["state"] == "stopped"
    assert runtime["status"] == "stopped"
    assert any(event["event"] == "runtime_degraded" for event in safety["safety_events"])
    assert any(event["event"] == "runtime_safety_stop" for event in safety["safety_events"])


@pytest.mark.asyncio
async def test_runtime_loop_enforces_minimum_sleep_interval():
    status = RuntimeStatus()
    loop = RuntimeLoop(
        status=status,
        interval_seconds=0,
        min_interval_seconds=0.02,
        heartbeat_log_every=1000,
        pending_task_counter=no_pending_tasks,
    )

    task = asyncio.create_task(loop.run())
    await asyncio.sleep(0.055)
    loop.request_stop("test_stop")
    await asyncio.wait_for(task, timeout=1)

    metrics = status.runtime_loop_metrics()
    assert metrics["interval_seconds"] == 0.02
    assert metrics["iteration"] <= 5
