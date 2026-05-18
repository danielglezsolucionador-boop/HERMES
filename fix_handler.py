content = '''"""
Telegram Handler — Subfase 2.2 + 2.3 + 2.5
Recepción, validación, normalización y persistencia de mensajes.
Solo acepta mensajes del TELEGRAM_CHAT_ID autorizado.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.core.config import settings
from app.telegram.client import send_message
from app.db.engine import AsyncSessionLocal
from app.repositories.message_repository import MessageRepository

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


async def persist_message(role: str, content: str, chat_id: int) -> None:
    """Persiste un mensaje en PostgreSQL."""
    try:
        async with AsyncSessionLocal() as session:
            repo = MessageRepository(session)
            await repo.save_message(role=role, content=content, chat_id=chat_id)
    except Exception as exc:
        logger.error("Error persistiendo message role=%s: %s", role, exc)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler principal de mensajes entrantes.
    1. Valida autorización
    2. Parsea mensaje
    3. Persiste mensaje user
    4. Responde
    5. Persiste respuesta hermes
    """
    if not is_authorized(update):
        return

    text = parse_message(update)
    if not text:
        logger.debug("Telegram → mensaje vacío ignorado")
        return

    chat_id = update.message.chat_id
    logger.info("Telegram → mensaje recibido chat_id=%s texto='%s'", chat_id, text)

    # Persistir mensaje del usuario
    await persist_message(role="user", content=text, chat_id=chat_id)
    logger.info("Telegram → mensaje user persistido")

    # Respuesta básica
    response = f"Hermes recibió: {text}"
    await send_message(response, chat_id=chat_id)

    # Persistir respuesta de Hermes
    await persist_message(role="hermes", content=response, chat_id=chat_id)
    logger.info("Telegram → respuesta hermes persistida")


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
'''

open('app/telegram/handler.py', 'w', encoding='utf-8').write(content)
print('OK - handler.py actualizado con persistencia')