import asyncio
from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.ai.providers.base import AIProvider
from app.models.task import Task
from app.runner.provider_bridge import ProviderBridge, ProviderBridgeRequest
from app.runner.task_execution import TaskExecutionRuntime


class FakeProvider(AIProvider):
    def __init__(
        self,
        response: dict | None = None,
        health: dict | None = None,
        delay_seconds: float = 0.0,
    ) -> None:
        self.response = response or {
            "success": True,
            "content": "provider response",
            "model": "fake-model",
            "usage": {"input_tokens": 3, "output_tokens": 2},
            "duration_ms": 7,
            "error": None,
            "error_type": None,
        }
        self.health = health or {
            "available": True,
            "configured": True,
            "last_error": None,
            "timeout_support": True,
        }
        self.delay_seconds = delay_seconds
        self.calls = 0

    @property
    def provider_name(self) -> str:
        return "fake"

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 1024,
    ) -> dict:
        self.calls += 1
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        return self.response

    async def healthcheck(self) -> dict:
        return self.health


def _execution_context():
    task = Task(
        id=uuid4(),
        title="provider bridge task",
        status="claimed",
        phase="test",
        runner_id="runner-test",
        runtime_id="runtime-test",
        claim_state="claimed",
        claimed_at=datetime.now(timezone.utc),
        claim_attempts=1,
    )
    runtime = TaskExecutionRuntime(
        runner_id="runner-test",
        runtime_id="runtime-test",
        memory_usage_provider=lambda: 64,
    )
    prepared = runtime.prepare(task)
    started = runtime.start(prepared.context)
    return started.context


def _bridge(provider: FakeProvider, **kwargs) -> ProviderBridge:
    return ProviderBridge(provider_resolver=lambda name: provider, **kwargs)


@pytest.mark.asyncio
async def test_provider_bridge_sends_valid_request_and_ingests_response():
    provider = FakeProvider()
    bridge = _bridge(provider)
    request = ProviderBridgeRequest(
        execution=_execution_context(),
        prompt="Summarize this task",
        system_prompt="Operational answer only",
        max_tokens=32,
    )

    result = await bridge.send(request)

    assert result.status == "completed"
    assert result.success is True
    assert result.provider_name == "fake"
    assert result.model == "fake-model"
    assert result.content == "provider response"
    assert result.context.request_id
    assert result.context.execution_id == request.execution.execution_id
    assert result.usage["input_tokens"] == 3
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_provider_bridge_rejects_inactive_execution_and_empty_prompt():
    provider = FakeProvider()
    bridge = _bridge(provider)
    context = _execution_context()
    inactive_context = replace(context, execution_state="completed")

    result = await bridge.send(
        ProviderBridgeRequest(execution=inactive_context, prompt=""),
    )

    assert result.status == "rejected"
    assert result.success is False
    assert "execution_not_active" in result.reasons
    assert "empty_provider_prompt" in result.reasons
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_provider_bridge_rejects_unconfigured_provider():
    provider = FakeProvider(
        health={
            "available": False,
            "configured": False,
            "last_error": "missing api key",
        }
    )
    bridge = _bridge(provider)

    result = await bridge.send(
        ProviderBridgeRequest(execution=_execution_context(), prompt="hello"),
    )

    assert result.status == "rejected"
    assert "provider_not_configured" in result.reasons
    assert "provider_unavailable" in result.reasons
    assert result.error == "missing api key"
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_provider_bridge_rejects_missing_provider_resolution():
    def missing_provider(name):
        raise RuntimeError("no provider active")

    bridge = ProviderBridge(provider_resolver=missing_provider)

    result = await bridge.send(
        ProviderBridgeRequest(
            execution=_execution_context(),
            prompt="hello",
            provider_name="missing",
        ),
    )

    assert result.status == "rejected"
    assert "provider_not_configured" in result.reasons
    assert "provider_unavailable" in result.reasons
    assert result.error == "no provider active"


@pytest.mark.asyncio
async def test_provider_bridge_enforces_request_size_and_rate_limits():
    provider = FakeProvider()
    size_limited = _bridge(provider, max_request_bytes=4)

    too_large = await size_limited.send(
        ProviderBridgeRequest(execution=_execution_context(), prompt="too large"),
    )

    assert too_large.status == "rejected"
    assert "max_request_size_exceeded" in too_large.reasons

    rate_limited = _bridge(provider, max_requests_per_minute=1)
    first = await rate_limited.send(
        ProviderBridgeRequest(execution=_execution_context(), prompt="hello"),
    )
    second = await rate_limited.send(
        ProviderBridgeRequest(execution=_execution_context(), prompt="hello again"),
    )

    assert first.status == "completed"
    assert second.status == "rejected"
    assert "max_provider_requests_reached" in second.reasons


@pytest.mark.asyncio
async def test_provider_bridge_enforces_concurrent_call_limit():
    provider = FakeProvider()
    bridge = _bridge(provider, max_concurrent_calls=1)
    bridge._active_calls = 1

    result = await bridge.send(
        ProviderBridgeRequest(execution=_execution_context(), prompt="hello"),
    )

    assert result.status == "rejected"
    assert "max_concurrent_provider_calls_reached" in result.reasons


@pytest.mark.asyncio
async def test_provider_bridge_contains_provider_failure():
    provider = FakeProvider(
        response={
            "success": False,
            "content": "",
            "model": "fake-model",
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "duration_ms": 4,
            "error": "provider unavailable",
            "error_type": "provider_error",
        }
    )
    bridge = _bridge(provider)

    result = await bridge.send(
        ProviderBridgeRequest(execution=_execution_context(), prompt="hello"),
    )

    assert result.status == "provider_error"
    assert result.success is False
    assert "provider_error" in result.reasons
    assert result.error == "provider unavailable"


@pytest.mark.asyncio
async def test_provider_bridge_rejects_invalid_response():
    provider = FakeProvider(response={"success": True, "content": "", "model": "m"})
    bridge = _bridge(provider)

    result = await bridge.send(
        ProviderBridgeRequest(execution=_execution_context(), prompt="hello"),
    )

    assert result.status == "invalid_response"
    assert "empty_provider_response" in result.reasons


@pytest.mark.asyncio
async def test_provider_bridge_contains_timeout():
    provider = FakeProvider(delay_seconds=0.2)
    bridge = _bridge(provider, timeout_seconds=0.01)

    result = await bridge.send(
        ProviderBridgeRequest(execution=_execution_context(), prompt="hello"),
    )

    assert result.status == "timeout"
    assert result.success is False
    assert "provider_timeout" in result.reasons
    assert bridge.visibility()["active_provider_calls"] == 0
