from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.ai.providers.base import AIProvider
from app.models.task import Task
from app.runner.prompt_execution import (
    PromptExecutionRequest,
    PromptExecutionRuntime,
)
from app.runner.provider_bridge import ProviderBridge
from app.runner.task_execution import TaskExecutionRuntime
from app.services.runtime_status import RuntimeStatus


class FakeProvider(AIProvider):
    def __init__(self, response: dict | None = None, health: dict | None = None):
        self.response = response or {
            "success": True,
            "content": "provider output",
            "model": "fake-model",
            "usage": {"input_tokens": 4, "output_tokens": 5},
            "duration_ms": 8,
            "error": None,
            "error_type": None,
        }
        self.health = health or {
            "available": True,
            "configured": True,
            "last_error": None,
            "timeout_support": True,
        }
        self.calls = 0
        self.last_prompt: str | None = None
        self.last_system_prompt: str | None = None

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
        self.last_prompt = prompt
        self.last_system_prompt = system_prompt
        return self.response

    async def healthcheck(self) -> dict:
        return self.health


def _execution_context():
    task = Task(
        id=uuid4(),
        title="prompt execution task",
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


def _request():
    return PromptExecutionRequest(
        execution=_execution_context(),
        objective="Generate an operational summary",
        prompt_type="reporting",
        context_data={"phase": "5.2.2", "task": "provider prompt"},
        execution_limits=("NO tocar runtime core", "NO cambiar arquitectura"),
        expected_output="Short operational response",
        validation_rules=("Preserve execution context",),
        audit_requirements=("Report risks",),
        max_tokens=64,
    )


def _runtime(provider: FakeProvider, status: RuntimeStatus | None = None):
    bridge = ProviderBridge(provider_resolver=lambda name: provider)
    return PromptExecutionRuntime(provider_bridge=bridge, status=status)


@pytest.mark.asyncio
async def test_prompt_execution_builds_prompt_and_preserves_context():
    provider = FakeProvider()
    status = RuntimeStatus()
    runtime = _runtime(provider, status=status)

    result = await runtime.execute(_request())

    assert result.status == "completed"
    assert result.success is True
    assert result.provider_name == "fake"
    assert result.provider_session_id
    assert result.output == "provider output"
    assert provider.calls == 1
    assert provider.last_prompt is not None
    assert "EXECUTION OBJECTIVE" in provider.last_prompt
    assert "Generate an operational summary" in provider.last_prompt
    assert "NO tocar runtime core" in provider.last_prompt
    assert "VALIDATION RULES" in provider.last_prompt
    assert result.provider_result is not None
    assert result.provider_result.context.provider_session_id == result.provider_session_id
    assert [entry["state"] for entry in result.lifecycle] == [
        "building",
        "ready",
        "sending",
        "waiting_response",
        "completed",
    ]

    metrics = status.prompt_execution_metrics()
    assert metrics["prompt_execution_status"] == "completed"
    assert metrics["prompt_status"] == "completed"
    assert metrics["provider_session_id"] == result.provider_session_id
    assert metrics["output_available"] is True
    assert result.to_dict()["output_available"] is True
    assert "output" not in result.to_dict()


@pytest.mark.asyncio
async def test_prompt_execution_rejects_incomplete_prompt_without_provider_call():
    provider = FakeProvider()
    runtime = _runtime(provider)
    request = PromptExecutionRequest(
        execution=_execution_context(),
        objective="",
        context_data={},
        execution_limits=(),
        expected_output="",
        validation_rules=(),
        audit_requirements=(),
    )

    result = await runtime.execute(request)

    assert result.status == "rejected"
    assert result.success is False
    assert "missing_execution_objective" in result.reasons
    assert "missing_context_data" in result.reasons
    assert "missing_execution_limits" in result.reasons
    assert "missing_expected_output" in result.reasons
    assert "missing_validation_rules" in result.reasons
    assert "missing_audit_requirements" in result.reasons
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_prompt_execution_preserves_provider_failure_context():
    provider = FakeProvider(
        health={
            "available": False,
            "configured": False,
            "last_error": "missing api key",
        }
    )
    runtime = _runtime(provider)

    result = await runtime.execute(_request())

    assert result.status == "rejected"
    assert result.success is False
    assert result.prompt_status == "failed"
    assert "provider_not_configured" in result.reasons
    assert result.provider_session_id
    assert result.provider_result is not None
    assert result.provider_result.connection_status == "failed"
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_prompt_execution_blocks_malformed_prompt_objective():
    provider = FakeProvider()
    runtime = _runtime(provider)
    request = PromptExecutionRequest(
        execution=_execution_context(),
        objective="bad\x00objective",
        context_data={"phase": "5.2.2"},
        execution_limits=("NO tocar runtime core",),
        expected_output="summary",
        validation_rules=("Preserve context",),
        audit_requirements=("Report risks",),
    )

    result = await runtime.execute(request)

    assert result.status == "rejected"
    assert "malformed_prompt_objective" in result.reasons
    assert provider.calls == 0
