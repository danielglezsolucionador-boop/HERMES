content = open('app/telegram/polling.py', 'r', encoding='utf-8').read()

new_content = '''"""
Telegram Polling — Subfase 2.1
Runner de polling para recibir mensajes en tiempo real.
"""

import asyncio
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from app.core.config import settings
from app.telegram.handler import handle_message, handle_start, handle_status
from app.telegram.client import validate_connection

logger = logging.getLogger(__name__)

_app: Application | None = None


async def start_polling() -> None:
    """
    Inicia el polling de Telegram en background.
    Compatible con python-telegram-bot v21.
    """
    global _app
    logger.info("Telegram polling → iniciando...")

    ok = await validate_connection()
    if not ok:
        logger.error("Telegram polling → conexión fallida, abortando")
        return

    _app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    _app.add_handler(CommandHandler("start", handle_start))
    _app.add_handler(CommandHandler("status", handle_status))
    _app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Telegram polling → handlers registrados")

    await _app.initialize()
    await _app.start()
    await _app.updater.start_polling(drop_pending_updates=True)

    logger.info("Telegram polling → activo ✅")


async def stop_polling() -> None:
    """Detiene el polling limpiamente."""
    global _app
    if _app is None:
        return
    try:
        await _app.updater.stop()
        await _app.stop()
        await _app.shutdown()
        logger.info("Telegram polling → detenido")
    except Exception as e:
        logger.error("Telegram polling → error al detener: %s", e)
'''

open('app/telegram/polling.py', 'w', encoding='utf-8').write(new_content)
print('OK - polling.py actualizado para v21')