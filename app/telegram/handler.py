"""
Telegram Handler — Subfase 2.2 + 2.3
Recepción, validación y normalización de mensajes.
Solo acepta mensajes del TELEGRAM_CHAT_ID autorizado.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.core.config import settings
from app.telegram.client import send_message

logger = logging.getLogger(__name__)


def is_authorized(update: Update) -> bool:
    """Valida que el mensaje viene del chat autorizado."""
    if update.message is None:
        return False
    chat_id = update.message.chat_id
    authorized = chat_id == settings.TELEGRAM_CHAT_ID
    if not authorized:
        logger.warning(
            "Telegram → acceso bloqueado chat_id=%s (no autorizado)", chat_id
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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler principal de mensajes entrantes.
    1. Valida autorización
    2. Parsea mensaje
    3. Loguea
    4. Responde echo básico
    """
    if not is_authorized(update):
        return

    text = parse_message(update)
    if not text:
        logger.debug("Telegram → mensaje vacío ignorado")
        return

    chat_id = update.message.chat_id
    logger.info("Telegram → mensaje recibido chat_id=%s texto='%s'", chat_id, text)

    # Echo básico — Subfase 2.4 lo reemplazará con lógica real
    response = f"Hermes recibió: {text}"
    await send_message(response, chat_id=chat_id)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /start."""
    if not is_authorized(update):
        return
    await send_message(
        "🟢 Hermes operacional. Listo para recibir instrucciones.",
        chat_id=update.message.chat_id,
    )


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /status."""
    if not is_authorized(update):
        return
    await send_message(
        "✅ Hermes activo\n📡 Telegram conectado\n🗄️ DB operacional",
        chat_id=update.message.chat_id,
    )