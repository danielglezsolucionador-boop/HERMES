content = '''"""
Telegram Handler — Subfase 2.2 + 2.3 + 2.5
Recepcion, validacion, normalizacion y persistencia de mensajes.
Solo acepta mensajes del TELEGRAM_CHAT_ID autorizado.
"""
import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.core.config import settings
from app.telegram.client import send_message
from app.repositories.message_repository import MessageRepository

logger = logging.getLogger(__name__)

# Loop principal de uvicorn — se registra en startup
_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Registra el loop principal de uvicorn para persistencia."""
    global _main_loop
    _main_loop = loop
    logger.info("Telegram handler → loop principal registrado")


def is_authorized(update: Update) -> bool:
    """Valida que el mensaje viene del chat autorizado."""
    if update.message is None:
        return False
    chat_id = update.message.chat_id
    authorized = chat_id == settings.TELEGRAM_CHAT_ID
    if not authorized:
        logger.warning(
            "Telegram acceso bloqueado chat_id=%s (no autorizado)", chat_id
        )
    return authorized


def parse_message(update: Update) -> str | None:
    """Extrae y normaliza el texto del mensaje."""
    if update.message is None:
        return None
    text = update.message.text
    if not text:
        return None
    return text.strip()


async def _persist(role: str, content: str, chat_id: int) -> None:
    """Coroutine de persistencia — corre en el loop principal."""
    from app.db.engine import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as session:
            repo = MessageRepository(session)
            await repo.save_message(role=role, content=content, chat_id=chat_id)
            logger.info("Message persistido: role=%s chat_id=%s", role, chat_id)
    except Exception as exc:
        logger.error("Error persistiendo message role=%s: %s", role, exc)


def persist_in_main_loop(role: str, content: str, chat_id: int) -> None:
    """Envia la coroutine de persistencia al loop principal desde el thread de Telegram."""
    if _main_loop is None:
        logger.error("Loop principal no registrado, no se puede persistir")
        return
    future = asyncio.run_coroutine_threadsafe(
        _persist(role, content, chat_id), _main_loop
    )
    try:
        future.result(timeout=10)
    except Exception as exc:
        logger.error("Error en persistencia threadsafe: %s", exc)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler principal de mensajes entrantes.
    1. Valida autorizacion
    2. Parsea mensaje
    3. Persiste mensaje user en loop principal
    4. Responde
    5. Persiste respuesta hermes en loop principal
    """
    if not is_authorized(update):
        return

    text = parse_message(update)
    if not text:
        logger.debug("Telegram mensaje vacio ignorado")
        return

    chat_id = update.message.chat_id
    logger.info("Telegram mensaje recibido chat_id=%s texto=%s", chat_id, text)

    persist_in_main_loop(role="user", content=text, chat_id=chat_id)
    logger.info("Telegram mensaje user persistido")

    response = f"Hermes recibio: {text}"
    await send_message(response, chat_id=chat_id)

    persist_in_main_loop(role="hermes", content=response, chat_id=chat_id)
    logger.info("Telegram respuesta hermes persistida")


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /start."""
    if not is_authorized(update):
        return
    await send_message(
        "Hermes operacional. Listo para recibir instrucciones.",
        chat_id=update.message.chat_id,
    )


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /status."""
    if not is_authorized(update):
        return
    await send_message(
        "Hermes activo | Telegram conectado | DB operacional",
        chat_id=update.message.chat_id,
    )
'''

open('app/telegram/handler.py', 'w', encoding='utf-8').write(content)
print('OK - handler.py actualizado con threadsafe persistence')