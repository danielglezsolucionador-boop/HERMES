"""
fix_3_4.py — Subfase 3.4: Telegram Task Commands
Crea:
  1. app/services/task_service.py  (nuevo)
Modifica:
  2. app/telegram/handler.py       (agrega handle_tasks, handle_task)
  3. app/telegram/polling.py       (registra CommandHandlers)
"""

import os

# ── ARCHIVO 1: task_service.py (NUEVO) ─────────────────────────────────────

service_path = r"C:\Users\admin\knowledge-core\hermes\app\services\task_service.py"
os.makedirs(os.path.dirname(service_path), exist_ok=True)

SERVICE_SRC = '''"""
TaskService — Subfase 3.4
Capa de servicio entre Telegram handlers y TaskRepository.
"""
import logging
from typing import Optional
from uuid import UUID

from app.db.engine import AsyncSessionLocal
from app.repositories.task_repository import TaskRepository

logger = logging.getLogger(__name__)


async def get_tasks(status: Optional[str] = None, limit: int = 10):
    """Retorna lista de tasks. Filtra por status si se indica."""
    async with AsyncSessionLocal() as session:
        repo = TaskRepository(session)
        tasks, total = await repo.list_tasks(limit=limit, offset=0, status=status)
        logger.debug("task_service.get_tasks: status=%s total=%d", status, total)
        return tasks


async def get_task(task_id: str):
    """Retorna una task por UUID string. None si no existe o UUID inválido."""
    try:
        uid = UUID(task_id)
    except (ValueError, AttributeError):
        logger.warning("task_service.get_task: UUID inválido=%s", task_id)
        return None

    async with AsyncSessionLocal() as session:
        repo = TaskRepository(session)
        task = await repo.get_task(uid)
        logger.debug("task_service.get_task: id=%s encontrada=%s", task_id, task is not None)
        return task
'''

if os.path.exists(service_path):
    print("⚠️  task_service.py ya existe — skip")
else:
    with open(service_path, "w", encoding="utf-8") as f:
        f.write(SERVICE_SRC)
    print("✅ app/services/task_service.py — creado")

# ── ARCHIVO 2: handler.py — agregar handlers al final ──────────────────────

handler_path = r"C:\Users\admin\knowledge-core\hermes\app\telegram\handler.py"

with open(handler_path, "r", encoding="utf-8") as f:
    handler_src = f.read()

NEW_HANDLERS = '''

async def handle_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /tasks [status_opcional]."""
    if not is_authorized(update):
        return

    chat_id = update.message.chat_id
    args = context.args  # palabras después del comando
    status_filter = args[0].lower() if args else None

    # Validar status si viene
    valid_statuses = {"pending", "doing", "review", "done", "failed"}
    if status_filter and status_filter not in valid_statuses:
        await send_message(
            f"Status inválido: '{status_filter}'. Usa: pending, doing, review, done, failed",
            chat_id=chat_id,
        )
        return

    from app.services.task_service import get_tasks
    try:
        tasks = await get_tasks(status=status_filter, limit=10)
    except Exception as exc:
        logger.error("handle_tasks error: %s", exc)
        await send_message("Error consultando tasks.", chat_id=chat_id)
        return

    if not tasks:
        label = f"({status_filter})" if status_filter else "(todas)"
        await send_message(f"No hay tasks {label}.", chat_id=chat_id)
        return

    label = f"({status_filter})" if status_filter else "(todas)"
    lines = [f"📋 Tasks {label}"]
    for t in tasks:
        short_id = str(t.id)[:8]
        lines.append(f"• {short_id}... — {t.title} [{t.status}]")
    await send_message("\n".join(lines), chat_id=chat_id)
    logger.info("handle_tasks: chat_id=%s status=%s devueltas=%d", chat_id, status_filter, len(tasks))


async def handle_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para /task <task_id>."""
    if not is_authorized(update):
        return

    chat_id = update.message.chat_id
    args = context.args

    if not args:
        await send_message("Uso: /task <task_id>", chat_id=chat_id)
        return

    task_id = args[0].strip()

    from app.services.task_service import get_task
    try:
        task = await get_task(task_id)
    except Exception as exc:
        logger.error("handle_task error: %s", exc)
        await send_message("Error consultando task.", chat_id=chat_id)
        return

    if task is None:
        await send_message(f"Task no encontrada: {task_id}", chat_id=chat_id)
        return

    created = task.created_at.strftime("%Y-%m-%d %H:%M") if task.created_at else "?"
    msg = (
        f"🧠 Task\\n"
        f"ID: {task.id}\\n"
        f"Title: {task.title}\\n"
        f"Status: {task.status}\\n"
        f"Phase: {task.phase or '-'}\\n"
        f"Created: {created}"
    )
    await send_message(msg, chat_id=chat_id)
    logger.info("handle_task: chat_id=%s task_id=%s", chat_id, task_id)
'''

if "handle_tasks" in handler_src:
    print("⚠️  handle_tasks ya existe en handler.py — skip")
else:
    handler_src = handler_src.rstrip() + NEW_HANDLERS + "\n"
    with open(handler_path, "w", encoding="utf-8") as f:
        f.write(handler_src)
    print("✅ handler.py — handle_tasks y handle_task agregados")

# ── ARCHIVO 3: polling.py — registrar CommandHandlers ──────────────────────

polling_path = r"C:\Users\admin\knowledge-core\hermes\app\telegram\polling.py"

with open(polling_path, "r", encoding="utf-8") as f:
    polling_src = f.read()

# Cambio 3a: agregar imports de los nuevos handlers
OLD_IMPORT = "from app.telegram.handler import handle_message, handle_start, handle_status"
NEW_IMPORT = "from app.telegram.handler import handle_message, handle_start, handle_status, handle_tasks, handle_task"

if "handle_tasks" in polling_src:
    print("⚠️  handle_tasks ya importado en polling.py — skip import")
else:
    assert OLD_IMPORT in polling_src, "ERROR: import handler no encontrado en polling.py"
    polling_src = polling_src.replace(OLD_IMPORT, NEW_IMPORT)
    print("✅ polling.py — imports actualizados")

# Cambio 3b: registrar los CommandHandlers
OLD_HANDLER_REG = '        _ptb_app.add_handler(CommandHandler("status", handle_status))'
NEW_HANDLER_REG = (
    '        _ptb_app.add_handler(CommandHandler("status", handle_status))\n'
    '        _ptb_app.add_handler(CommandHandler("tasks", handle_tasks))\n'
    '        _ptb_app.add_handler(CommandHandler("task", handle_task))'
)

if 'CommandHandler("tasks"' in polling_src:
    print("⚠️  CommandHandler tasks ya registrado en polling.py — skip")
else:
    assert OLD_HANDLER_REG in polling_src, "ERROR: registro handle_status no encontrado en polling.py"
    polling_src = polling_src.replace(OLD_HANDLER_REG, NEW_HANDLER_REG)
    print("✅ polling.py — CommandHandlers tasks y task registrados")

with open(polling_path, "w", encoding="utf-8") as f:
    f.write(polling_src)

print("\n🎯 fix_3_4.py completado — valida con py_compile a continuación")