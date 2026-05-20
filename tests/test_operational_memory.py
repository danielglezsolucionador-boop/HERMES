from app.services import operational_memory
import pytest


def _row(role: str, message: str):
    return {
        "role": role,
        "message": message,
        "created_at": "2026-05-20T15:00:00+00:00",
        "metadata": {"source": "telegram"},
    }


def test_memory_followup_detection():
    assert operational_memory.is_memory_followup("y eso ya se resolvio?")
    assert operational_memory.is_memory_followup("que paso despues")
    assert not operational_memory.is_memory_followup("que tareas fallaron")


@pytest.mark.asyncio
async def test_memory_extracts_last_operational_route(monkeypatch):
    rows = [
        _row("user", "que tareas fallaron"),
        _row("hermes", "Hermes operacional\n\nTasks fallidas\nTotal failed en PostgreSQL: 2"),
        _row("user", "y eso ya se resolvio?"),
    ]

    async def fake_recent(limit: int):
        return rows

    monkeypatch.setattr(operational_memory, "_get_recent_conversation", fake_recent)

    memory = await operational_memory.load_operational_memory(
        current_query="y eso ya se resolvio?"
    )

    assert memory["last_route"] == "failed"
    assert memory["last_user_message"] == "que tareas fallaron"


@pytest.mark.asyncio
async def test_memory_augmented_prompt_includes_recent_messages(monkeypatch):
    rows = [
        _row("user", "que riesgos tenemos"),
        _row(
            "hermes",
            "Hermes operacional\n\nPrioridades:\n- Revisar 1 task(s) fallidas.\n"
            "Decision: se mantiene revision manual.",
        ),
    ]

    async def fake_recent(limit: int):
        return rows

    monkeypatch.setattr(operational_memory, "_get_recent_conversation", fake_recent)

    prompt = await operational_memory.build_memory_augmented_prompt("explica eso")

    assert "telegram_conversations" in prompt
    assert "que riesgos tenemos" in prompt
    assert "Revisar 1 task(s) fallidas." in prompt
    assert "se mantiene revision manual" in prompt
    assert "USER REQUEST" in prompt


def test_resolution_line_uses_real_counts():
    snapshot = {
        "counts": {"failed": 3, "doing": 1, "pending": 0},
        "runner": {"runner_status": "offline"},
    }

    result = operational_memory._resolution_line("failed", snapshot)

    assert "No esta resuelto" in result
    assert "3 task(s) failed" in result
