"""
Telegram Client — Subfase 2.1
Conexión real con Telegram API.
Polling + envío de mensajes.
"""

import logging
from telegram import Bot
from telegram.error import TelegramError
from app.core.config import settings

logger = logging.getLogger(__name__)

# Bot global — se inicializa una vez
_bot: Bot | None = None


def get_bot() -> Bot:
    """Retorna instancia global del bot."""
    global _bot
    if _bot is None:
        _bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    return _bot


async def send_message(text: str, chat_id: int | None = None) -> bool:
    """
    Envía mensaje al CEO.
    Usa TELEGRAM_CHAT_ID por defecto si no se especifica.
    Retorna True si ok, False si error.
    """
    target = chat_id or settings.TELEGRAM_CHAT_ID
    try:
        bot = get_bot()
        await bot.send_message(chat_id=target, text=text)
        logger.info("Telegram → mensaje enviado a chat_id=%s", target)
        return True
    except TelegramError as e:
        logger.error("Telegram → error enviando mensaje: %s", e)
        return False


async def validate_connection() -> bool:
    """
    Valida que el bot conecta correctamente con Telegram API.
    Retorna True si ok.
    """
    try:
        bot = get_bot()
        me = await bot.get_me()
        logger.info("Telegram → bot conectado: @%s", me.username)
        return True
    except TelegramError as e:
        logger.error("Telegram → error de conexión: %s", e)
        return False