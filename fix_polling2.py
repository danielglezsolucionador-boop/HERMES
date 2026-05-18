content = '''"""
Telegram Polling — Subfase 2.1
Thread separado con loop propio.
Arquitectura: FastAPI loop | Telegram loop (independiente)
"""

import asyncio
import logging
import threading
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from app.core.config import settings
from app.telegram.handler import handle_message, handle_start, handle_status
from app.telegram.client import validate_connection

logger = logging.getLogger(__name__)

_thread: threading.Thread | None = None
_ptb_app: Application | None = None
_loop: asyncio.AbstractEventLoop | None = None


def _run_polling_loop() -> None:
    """
    Corre en thread separado con su propio event loop.
    Completamente aislado del loop de uvicorn.
    """
    global _ptb_app, _loop

    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)

    async def _start():
        global _ptb_app
        _ptb_app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        _ptb_app.add_handler(CommandHandler("start", handle_start))
        _ptb_app.add_handler(CommandHandler("status", handle_status))
        _ptb_app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )
        await _ptb_app.initialize()
        await _ptb_app.start()
        await _ptb_app.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram polling → activo en thread separado ✅")
        # Mantener loop vivo
        await asyncio.Event().wait()

    try:
        _loop.run_until_complete(_start())
    except Exception as e:
        logger.error("Telegram polling → error en thread: %s", e)
    finally:
        _loop.close()


async def start_polling() -> None:
    """Lanza el thread de polling. Llamado desde lifespan FastAPI."""
    global _thread
    logger.info("Telegram polling → lanzando thread separado...")

    ok = await validate_connection()
    if not ok:
        logger.error("Telegram polling → conexión fallida, abortando")
        return

    _thread = threading.Thread(target=_run_polling_loop, daemon=True, name="telegram-polling")
    _thread.start()
    logger.info("Telegram polling → thread iniciado ✅")


async def stop_polling() -> None:
    """Detiene el polling limpiamente desde el loop principal."""
    global _ptb_app, _loop, _thread
    if _ptb_app is None or _loop is None:
        return
    try:
        async def _stop():
            await _ptb_app.updater.stop()
            await _ptb_app.stop()
            await _ptb_app.shutdown()

        future = asyncio.run_coroutine_threadsafe(_stop(), _loop)
        future.result(timeout=10)
        logger.info("Telegram polling → detenido limpiamente ✅")
    except Exception as e:
        logger.error("Telegram polling → error al detener: %s", e)
'''

open('app/telegram/polling.py', 'w', encoding='utf-8').write(content)
print('OK - polling.py reescrito con thread separado')