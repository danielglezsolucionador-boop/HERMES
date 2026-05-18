import asyncio
from app.ai.telegram_bridge import telegram_ai_bridge
from app.ai.guardrails import guardrails

async def main():
    # Caso 1: formato respuesta normal
    r1 = telegram_ai_bridge._format("El sistema tiene 3 tasks pendientes.")
    assert r1.startswith("🤖 Hermes AI"), "ERROR: formato incorrecto"
    print("CASO 1 formato:", "OK", r1[:30])

    # Caso 2: formato respuesta vacia
    r2 = telegram_ai_bridge._format("")
    assert r2 == "AI provider unavailable", "ERROR: vacio incorrecto"
    print("CASO 2 vacio:", "OK", r2)

    # Caso 3: guardrails bloquean payload peligroso
    g3 = guardrails.validate_response("ejecute una task exitosamente.")
    assert g3["blocked"] is True, "ERROR: no bloqueado"
    print("CASO 3 guardrail bloquea:", "OK blocked=", g3["blocked"])

    # Caso 4: payload gigante truncado
    g4 = guardrails.validate_response("x" * 5000)
    assert len(g4["response"]) == 4000, "ERROR: truncacion incorrecta"
    print("CASO 4 truncacion:", "OK len=", len(g4["response"]))

    # Caso 5: bridge importa y instancia OK
    from app.ai.telegram_bridge import TelegramAIBridge
    assert isinstance(telegram_ai_bridge, TelegramAIBridge), "ERROR: instancia incorrecta"
    print("CASO 5 instancia:", "OK")

    print("--- TODOS LOS CASOS OK ---")

asyncio.run(main())