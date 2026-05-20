"""
Telegram Handler — Subfase 2.2 + 2.3
Recepción, validación y normalización de mensajes.
Solo acepta mensajes del TELEGRAM_CHAT_ID autorizado.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.ai.telegram_bridge import telegram_ai_bridge
from app.core.config import settings
from app.services.runtime_status import runtime_status
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


async def _save_conversation_message(role: str, message: str) -> None:
    try:
        from app.db.engine import AsyncSessionLocal
        from app.repositories.conversation_repository import save_message

        async with AsyncSessionLocal() as session:
            await save_message(session, role=role, message=message)
    except Exception as exc:
        logger.warning("Telegram conversation persistence skipped: %s", exc)


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
    await _save_conversation_message("user", text)

    try:
        response = await telegram_ai_bridge.handle_query(text)
    except Exception as exc:
        logger.error("Telegram AI bridge error: %s", exc)
        response = "AI provider unavailable"

    sent = await send_message(response, chat_id=chat_id)
    runtime_status.mark_telegram_message_processed()
    if sent:
        await _save_conversation_message("hermes", response)


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


def _format_task_line(task) -> str:
    short_id = str(task.id)[:8]
    title = task.title or "(sin titulo)"
    return f"- {short_id}... - {title} [{task.status}]"


async def _send_tasks(update: Update, status_filter: str | None) -> None:
    chat_id = update.message.chat_id
    from app.services.task_service import VALID_TASK_STATUSES, get_tasks

    if status_filter and status_filter not in VALID_TASK_STATUSES:
        valid = ", ".join(sorted(VALID_TASK_STATUSES))
        await send_message(
            f"Status invalido: '{status_filter}'. Usa: {valid}",
            chat_id=chat_id,
        )
        return

    try:
        tasks = await get_tasks(status=status_filter, limit=10)
    except Exception as exc:
        logger.error("Telegram tasks command error: %s", exc)
        await send_message("Error consultando tasks.", chat_id=chat_id)
        return

    label = status_filter or "todas"
    if not tasks:
        await send_message(f"No hay tasks ({label}).", chat_id=chat_id)
        return

    lines = [f"Tasks ({label})"]
    lines.extend(_format_task_line(task) for task in tasks)
    await send_message("\n".join(lines), chat_id=chat_id)
    logger.info(
        "Telegram tasks command chat_id=%s status=%s count=%d",
        chat_id,
        status_filter,
        len(tasks),
    )


async def handle_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /tasks [status]."""
    if not is_authorized(update):
        return

    args = context.args or []
    status_filter = args[0].lower() if args else None
    await _send_tasks(update, status_filter)


async def handle_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /pending."""
    if not is_authorized(update):
        return

    await _send_tasks(update, "pending")


async def handle_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /task <task_id>."""
    if not is_authorized(update):
        return

    chat_id = update.message.chat_id
    args = context.args or []
    if not args:
        await send_message("Uso: /task <task_id>", chat_id=chat_id)
        return

    task_id = args[0].strip()
    from app.services.task_service import get_task

    try:
        task = await get_task(task_id)
    except Exception as exc:
        logger.error("Telegram task command error: %s", exc)
        await send_message("Error consultando task.", chat_id=chat_id)
        return

    if task is None:
        await send_message(f"Task no encontrada: {task_id}", chat_id=chat_id)
        return

    created = task.created_at.strftime("%Y-%m-%d %H:%M") if task.created_at else "-"
    message = "\n".join(
        [
            "Task",
            f"ID: {task.id}",
            f"Title: {task.title}",
            f"Status: {task.status}",
            f"Phase: {task.phase or '-'}",
            f"Created: {created}",
        ]
    )
    await send_message(message, chat_id=chat_id)
    logger.info("Telegram task command chat_id=%s task_id=%s", chat_id, task_id)
