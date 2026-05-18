"""
Telegram Polling — Subfase 2.1
Runner de polling para recibir mensajes en tiempo real.
"""

import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from app.core.config import settings
from app.telegram.handler import handle_message, handle_start, handle_status
from app.telegram.client import validate_connection

logger = logging.getLogger(__name__)


async def start_polling() -> None:
    """
    Inicia el polling de Telegram.
    Valida conexión antes de arrancar.
    """
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

    # Registrar handlers
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("status", handle_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Telegram polling → handlers registrados")
    logger.info("Telegram polling → escuchando mensajes...")

    # Iniciar polling
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    logger.info("Telegram polling → activo ✅")

_app = None

async def stop_polling() -> None:
    """Detiene el polling de Telegram."""
    global _app
    if _app:
        try:
            await _app.updater.stop()
            await _app.stop()
            await _app.shutdown()
            logger.info("Telegram polling → detenido")
        except Exception as e:
            logger.warning("Telegram polling → error al detener: %s", e)