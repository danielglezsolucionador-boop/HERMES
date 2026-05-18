path = r"app\telegram\handler.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

new_handler = '''

async def handle_ask(update, context):
    """Handler para /ask <consulta operacional>."""
    if not is_authorized(update):
        return

    chat_id = update.message.chat_id
    args = context.args

    if not args:
        await send_message("Uso: /ask <consulta>\\nEjemplo: /ask que tareas fallaron hoy", chat_id=chat_id)
        return

    query = " ".join(args).strip()
    logger.info("handle_ask: chat_id=%s query_chars=%d", chat_id, len(query))

    from app.ai.telegram_bridge import telegram_ai_bridge

    if _main_loop is None:
        await send_message("AI provider unavailable", chat_id=chat_id)
        return

    import asyncio
    future = asyncio.run_coroutine_threadsafe(
        telegram_ai_bridge.handle_query(query), _main_loop
    )
    try:
        response = future.result(timeout=30)
    except Exception as exc:
        logger.error("handle_ask: error=%s", exc)
        response = "AI provider unavailable"

    await send_message(response, chat_id=chat_id)
    logger.info("handle_ask: completado chat_id=%s", chat_id)
'''

assert "async def handle_task" in content, "ERROR: handle_task no encontrado"
assert "handle_ask" not in content, "ERROR: handle_ask ya existe"

content = content + new_handler

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK — handle_ask agregado a handler.py")