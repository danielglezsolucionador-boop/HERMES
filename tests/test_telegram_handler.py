from types import SimpleNamespace

import pytest

from app.telegram import handler


def _update(chat_id: int, text: str):
    return SimpleNamespace(message=SimpleNamespace(chat_id=chat_id, text=text))


@pytest.mark.asyncio
async def test_handle_message_uses_ai_bridge(monkeypatch):
    sent = []
    queries = []
    saved = []
    monkeypatch.setattr(handler.settings, "TELEGRAM_CHAT_ID", 123)

    async def fake_handle_query(query: str) -> str:
        queries.append(query)
        return "Hermes AI operativo"

    async def fake_operational_query(query: str) -> str | None:
        return None

    async def fake_send_message(text: str, chat_id: int | None = None) -> bool:
        sent.append((chat_id, text))
        return True

    async def fake_save(role: str, message: str) -> None:
        saved.append((role, message))

    monkeypatch.setattr(handler.telegram_ai_bridge, "handle_query", fake_handle_query)
    monkeypatch.setattr(handler, "maybe_handle_operational_query", fake_operational_query)
    monkeypatch.setattr(handler, "send_message", fake_send_message)
    monkeypatch.setattr(handler, "_save_conversation_message", fake_save)

    await handler.handle_message(_update(123, "que tareas faltan"), None)

    assert queries == ["que tareas faltan"]
    assert sent == [(123, "Hermes AI operativo")]
    assert saved == [("user", "que tareas faltan"), ("hermes", "Hermes AI operativo")]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "como estamos",
        "hay problemas",
        "runtime estable",
        "qué pasó hoy",
        "qué tareas fallaron",
        "qué está atrasado",
    ],
)
async def test_handle_message_routes_executive_queries_to_operational_summary(
    monkeypatch,
    query,
):
    sent = []
    bridge_calls = []
    monkeypatch.setattr(handler.settings, "TELEGRAM_CHAT_ID", 123)

    async def fake_operational_query(raw_query: str) -> str | None:
        assert raw_query == query
        return "Resumen ejecutivo operacional real\nDB: connected\nRiesgos: 1"

    async def fake_handle_query(raw_query: str) -> str:
        bridge_calls.append(raw_query)
        return "Hermes recibi\u00f3: " + raw_query

    async def fake_send_message(text: str, chat_id: int | None = None) -> bool:
        sent.append((chat_id, text))
        return True

    async def fake_save(role: str, message: str) -> None:
        return None

    monkeypatch.setattr(handler, "maybe_handle_operational_query", fake_operational_query)
    monkeypatch.setattr(handler.telegram_ai_bridge, "handle_query", fake_handle_query)
    monkeypatch.setattr(handler, "send_message", fake_send_message)
    monkeypatch.setattr(handler, "_save_conversation_message", fake_save)

    await handler.handle_message(_update(123, query), None)

    assert bridge_calls == []
    assert len(sent) == 1
    assert sent[0][0] == 123
    assert sent[0][1].startswith("Hermes operacional")
    assert "Resumen ejecutivo operacional real" in sent[0][1]
    assert "Hermes recibi\u00f3:" not in sent[0][1]


@pytest.mark.asyncio
async def test_handle_message_supports_consecutive_messages(monkeypatch):
    sent = []
    saved = []
    monkeypatch.setattr(handler.settings, "TELEGRAM_CHAT_ID", 123)

    async def fake_handle_query(query: str) -> str:
        return f"respuesta: {query}"

    async def fake_operational_query(query: str) -> str | None:
        return None

    async def fake_send_message(text: str, chat_id: int | None = None) -> bool:
        sent.append((chat_id, text))
        return True

    async def fake_save(role: str, message: str) -> None:
        saved.append((role, message))

    monkeypatch.setattr(handler.telegram_ai_bridge, "handle_query", fake_handle_query)
    monkeypatch.setattr(handler, "maybe_handle_operational_query", fake_operational_query)
    monkeypatch.setattr(handler, "send_message", fake_send_message)
    monkeypatch.setattr(handler, "_save_conversation_message", fake_save)

    await handler.handle_message(_update(123, "hola"), None)
    await handler.handle_message(_update(123, "riesgos"), None)

    assert sent == [(123, "respuesta: hola"), (123, "respuesta: riesgos")]
    assert saved == [
        ("user", "hola"),
        ("hermes", "respuesta: hola"),
        ("user", "riesgos"),
        ("hermes", "respuesta: riesgos"),
    ]
