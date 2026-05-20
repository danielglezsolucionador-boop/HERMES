import logging

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.api import ai as ai_api
from app.api.ai import _build_ai_test_prompt
from app.integrations import claude_client
from app.integrations.claude_client import ask, validate_startup
from app.main import app


@pytest.fixture(autouse=True)
def no_claude_key(monkeypatch):
    monkeypatch.setattr(settings, "CLAUDE_API_KEY", "")
    monkeypatch.setattr(settings, "CLAUDE_REAL_REQUESTS_ENABLED", False)


def test_validate_startup_warns_without_key(caplog):
    caplog.set_level(logging.WARNING)

    validate_startup()

    assert "provider_not_configured" in caplog.text
    assert "CLAUDE_API_KEY" in caplog.text


def test_ai_test_prompt_connects_context_isolation_and_builder_shape():
    prompt = _build_ai_test_prompt(
        {
            "summary": "Runner offline",
            "tasks": [
                {
                    "id": "1",
                    "title": "Revisar",
                    "description": "DATABASE_URL=postgresql+asyncpg://user:pass@host/db",
                    "status": "pending",
                    "phase": "3.6.3",
                    "error": None,
                    "retry_count": 0,
                }
            ],
            "incidents": ["Bearer secret-token-123456"],
            "runtime": {"runner_status": "offline"},
            "metadata": {"context_version": "3.6", "unsafe": {"nested": "ignored"}},
        },
        "consulta con sk-ant-abcdefghij1234567890",
    )

    assert "HERMES OPERATIONAL CONTEXT" in prompt
    assert "USER REQUEST" in prompt
    assert "3.6.3" in prompt
    assert "postgresql+asyncpg://user:pass@host/db" not in prompt
    assert "sk-ant-abcdefghij1234567890" not in prompt
    assert '"unsafe"' not in prompt


@pytest.mark.asyncio
async def test_ask_without_key_returns_controlled_schema(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("No real HTTP request is allowed in subphase 3.6.1")

    monkeypatch.setattr(httpx, "AsyncClient", fail_if_called)

    result = await ask("estado operacional")

    assert result == {
        "success": False,
        "content": None,
        "model": None,
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "duration_ms": 0,
        "error": "provider_not_configured",
        "error_type": "provider_not_configured",
    }


@pytest.mark.asyncio
async def test_ai_test_endpoint_uses_orchestrator_without_real_http(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("No real Claude HTTP request is allowed from /ai/test")

    monkeypatch.setattr(claude_client.httpx, "AsyncClient", fail_if_called)

    async def no_operational_route(prompt: str):
        return None

    async def fake_generate(prompt: str, max_tokens: int = 1024):
        return {
            "success": True,
            "response": "Hermes operativo",
            "provider": "openrouter",
            "model": "test-model",
            "duration_ms": 1,
            "provider_ms": 1,
            "usage": {"input_tokens": 1, "output_tokens": 2},
            "tokens_estimated": 3,
            "context_chars": 10,
            "guardrail_blocked": False,
            "guardrail_reason": None,
            "handoff": {"agent": "openrouter", "status": "completed"},
            "error": None,
        }

    monkeypatch.setattr(ai_api, "maybe_handle_operational_query", no_operational_route)
    monkeypatch.setattr(ai_api.orchestrator, "generate", fake_generate)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post("/ai/test", json={"prompt": "consulta libre"})

    data = response.json()
    assert response.status_code == 200
    assert data["success"] is True
    assert data["response"] == "Hermes operativo"
    assert data["provider"] == "openrouter"
    assert data["usage"] == {"input_tokens": 1, "output_tokens": 2}


@pytest.mark.asyncio
async def test_ai_test_endpoint_routes_operational_queries_without_provider(monkeypatch):
    async def fake_operational(prompt: str):
        assert prompt == "Backlog"
        return "Backlog operacional\nTotal backlog: 3 | pending 2 | doing 1"

    async def fail_generate(*args, **kwargs):
        raise AssertionError("Operational queries should not call the AI provider")

    monkeypatch.setattr(ai_api, "maybe_handle_operational_query", fake_operational)
    monkeypatch.setattr(ai_api.orchestrator, "generate", fail_generate)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post("/ai/test", json={"prompt": "Backlog"})

    data = response.json()
    assert response.status_code == 200
    assert data["success"] is True
    assert data["provider"] == "operational_summary"
    assert "Backlog operacional" in data["response"]


@pytest.mark.asyncio
async def test_key_present_still_does_not_make_real_request_when_disabled(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Real Claude requests are disabled in subphase 3.6.1")

    monkeypatch.setattr(settings, "CLAUDE_API_KEY", "sk-ant-test-not-real")
    monkeypatch.setattr(settings, "CLAUDE_REAL_REQUESTS_ENABLED", False)
    monkeypatch.setattr(httpx, "AsyncClient", fail_if_called)

    result = await ask("estado operacional")

    assert result["success"] is False
    assert result["content"] is None
    assert result["model"] is None
    assert result["error"] == "provider_disabled"
    assert result["error_type"] == "provider_disabled"
