from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.ai import telegram_bridge
from app.services import operational_summary


def _task(title: str, status: str, error: str | None = None):
    return SimpleNamespace(
        id="11111111-2222-3333-4444-555555555555",
        title=title,
        status=status,
        error=error,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _snapshot():
    failed_task = _task("Validar OpenRouter", "failed", "provider timeout real")
    doing_task = _task("Procesar cola local", "doing")
    pending_task = _task("Revisar backlog", "pending")
    return {
        "generated_at": datetime.now(timezone.utc),
        "counts": {"pending": 1, "doing": 1, "review": 0, "done": 2, "failed": 1},
        "today_status_counts": {
            "pending": 0,
            "doing": 1,
            "review": 0,
            "done": 1,
            "failed": 1,
        },
        "created_today": 1,
        "completed_today": 1,
        "recent_today_tasks": [failed_task, doing_task],
        "failed_tasks": [failed_task],
        "doing_tasks": [doing_task],
        "pending_tasks": [pending_task],
        "runner": {
            "runner_status": "offline",
            "runner_alive": False,
            "last_loop_at": None,
            "total_ai_requests": 3,
            "ai_success_requests": 2,
            "ai_failed_requests": 1,
            "avg_ai_duration_ms": 1200,
            "last_ai_provider": "openrouter",
            "last_ai_model": "test-model",
            "telegram_messages_processed": 4,
        },
        "priorities": ["Revisar 1 task(s) fallidas."],
        "risks": ["Runner offline con tasks en doing puede indicar ejecucion detenida."],
        "incidents": ["11111111 Validar OpenRouter - provider timeout real"],
    }


def test_classify_operational_queries():
    assert operational_summary.classify_operational_query("que paso hoy") == "summary"
    assert operational_summary.classify_operational_query("que tareas fallaron") == "failed"
    assert operational_summary.classify_operational_query("que esta atrasado") == "delayed"
    assert operational_summary.classify_operational_query("que riesgos tenemos") == "risks"
    assert operational_summary.classify_operational_query("hola hermes") is None


@pytest.mark.asyncio
async def test_failed_summary_uses_operational_snapshot(monkeypatch):
    async def fake_snapshot():
        return _snapshot()

    monkeypatch.setattr(operational_summary, "_load_snapshot", fake_snapshot)

    response = await operational_summary.maybe_handle_operational_query(
        "que tareas fallaron"
    )

    assert "Tasks fallidas" in response
    assert "Total failed en PostgreSQL: 1" in response
    assert "Validar OpenRouter" in response
    assert "provider timeout real" in response


@pytest.mark.asyncio
async def test_telegram_bridge_bypasses_ai_for_operational_query(monkeypatch):
    async def fake_operational(query: str) -> str:
        return "Resumen real desde PostgreSQL"

    async def fail_generate(*args, **kwargs):
        raise AssertionError("AI provider should not be used for routed operational query")

    monkeypatch.setattr(telegram_bridge, "maybe_handle_operational_query", fake_operational)
    monkeypatch.setattr(telegram_bridge.orchestrator, "generate", fail_generate)

    response = await telegram_bridge.TelegramAIBridge().handle_query("que paso hoy")

    assert response == "Hermes operacional\n\nResumen real desde PostgreSQL"
