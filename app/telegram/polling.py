"""
Telegram Polling — Subfase 2.1
Runner de polling para recibir mensajes en tiempo real.
"""

import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from app.core.config import settings
from app.telegram.handler import (
    handle_message,
    handle_pending,
    handle_start,
    handle_status,
    handle_task,
    handle_tasks,
)
from app.telegram.client import validate_connection

logger = logging.getLogger(__name__)

_telegram_app: Application | None = None


async def start_polling() -> None:
    """
    Inicia el polling de Telegram.
    Valida conexión antes de arrancar.
    """
    global _telegram_app
    if _telegram_app is not None:
        logger.info("Telegram polling already active")
        return

    logger.info("Telegram polling → iniciando...")

    # Validar conexión
    ok = await validate_connection()
    if not ok:
        logger.error("Telegram polling → conexión fallida, abortando")
        return

    # Construir aplicación
    app = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .build()
    )
    _telegram_app = app

    # Registrar handlers
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("status", handle_status))
    app.add_handler(CommandHandler("tasks", handle_tasks))
    app.add_handler(CommandHandler("task", handle_task))
    app.add_handler(CommandHandler("pending", handle_pending))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Telegram polling → handlers registrados")
    logger.info("Telegram polling → escuchando mensajes...")

    # Iniciar polling
    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
    except Exception:
        _telegram_app = None
        raise

    logger.info("Telegram polling → activo ✅")


async def stop_polling() -> None:
    """Detiene el polling de Telegram si esta activo."""
    global _telegram_app
    app = _telegram_app
    if app is None:
        logger.info("Telegram polling stop requested but no app is active")
        return

    _telegram_app = None
    try:
        if app.updater:
            await app.updater.stop()
        await app.stop()
        await app.shutdown()
        logger.info("Telegram polling stopped")
    except Exception as exc:
        logger.warning("Telegram polling stop error: %s", exc)


if __name__ == '__main__':
    import asyncio
    asyncio.run(start_polling())
