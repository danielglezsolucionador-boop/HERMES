import logging

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
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
async def test_ai_test_endpoint_without_key_is_controlled(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("No real HTTP request is allowed in subphase 3.6.1")

    monkeypatch.setattr(claude_client.httpx, "AsyncClient", fail_if_called)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post("/ai/test", json={"prompt": "estado operacional"})

    data = response.json()
    assert response.status_code == 200
    assert data["success"] is False
    assert data["content"] is None
    assert data["model"] is None
    assert data["error"] == "provider_not_configured"
    assert data["usage"] == {"input_tokens": 0, "output_tokens": 0}


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
