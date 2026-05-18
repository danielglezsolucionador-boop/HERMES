"""
fix_3_4c.py — Reescribe handle_tasks y handle_task con run_coroutine_threadsafe
Approach: reemplazar desde la firma hasta el final de cada función por líneas clave.
"""

handler_path = r"C:\Users\admin\knowledge-core\hermes\app\telegram\handler.py"

with open(handler_path, "r", encoding="utf-8") as f:
    src = f.read()

# Encontrar donde empieza handle_tasks
idx_tasks = src.find("async def handle_tasks(")
idx_task  = src.find("async def handle_task(")

if idx_tasks == -1:
    print("❌ handle_tasks no encontrado")
    exit(1)
if idx_task == -1:
    print("❌ handle_task no encontrado")
    exit(1)

print(f"handle_tasks encontrado en offset: {idx_tasks}")
print(f"handle_task  encontrado en offset: {idx_task}")

# Conservar todo lo que hay ANTES de handle_tasks
parte_anterior = src[:idx_tasks]

# Nuevas implementaciones limpias
HANDLE_TASKS_NEW = '''async def handle_tasks(update, context):
    """Handler para /tasks [status_opcional]."""
    if not is_authorized(update):
        return

    chat_id = update.message.chat_id
    args = context.args
    status_filter = args[0].lower() if args else None

    valid_statuses = {"pending", "doing", "review", "done", "failed"}
    if status_filter and status_filter not in valid_statuses:
        await send_message(
            "Status invalido: '{}'. Usa: pending, doing, review, done, failed".format(status_filter),
            chat_id=chat_id,
        )
        return

    from app.services.task_service import get_tasks
    try:
        if _main_loop is None:
            raise RuntimeError("Loop principal no registrado")
        future = asyncio.run_coroutine_threadsafe(
            get_tasks(status=status_filter, limit=10), _main_loop
        )
        tasks = future.result(timeout=10)
    except Exception as exc:
        logger.error("handle_tasks error: %s", exc)
        await send_message("Error consultando tasks.", chat_id=chat_id)
        return

    if not tasks:
        label = "({})".format(status_filter) if status_filter else "(todas)"
        await send_message("No hay tasks {}.".format(label), chat_id=chat_id)
        return

    label = "({})".format(status_filter) if status_filter else "(todas)"
    lines = ["Tasks {}".format(label)]
    for t in tasks:
        short_id = str(t.id)[:8]
        lines.append("* {}... - {} [{}]".format(short_id, t.title, t.status))
    await send_message("\\n".join(lines), chat_id=chat_id)
    logger.info("handle_tasks: chat_id=%s status=%s devueltas=%d", chat_id, status_filter, len(tasks))


'''

HANDLE_TASK_NEW = '''async def handle_task(update, context):
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
        if _main_loop is None:
            raise RuntimeError("Loop principal no registrado")
        future = asyncio.run_coroutine_threadsafe(
            get_task(task_id), _main_loop
        )
        task = future.result(timeout=10)
    except Exception as exc:
        logger.error("handle_task error: %s", exc)
        await send_message("Error consultando task.", chat_id=chat_id)
        return

    if task is None:
        await send_message("Task no encontrada: {}".format(task_id), chat_id=chat_id)
        return

    created = task.created_at.strftime("%Y-%m-%d %H:%M") if task.created_at else "?"
    msg = "Task\\nID: {}\\nTitle: {}\\nStatus: {}\\nPhase: {}\\nCreated: {}".format(
        task.id, task.title, task.status, task.phase or "-", created
    )
    await send_message(msg, chat_id=chat_id)
    logger.info("handle_task: chat_id=%s task_id=%s", chat_id, task_id)
'''

# Construir archivo final: parte_anterior + handle_tasks + handle_task
nuevo_src = parte_anterior.rstrip() + "\n\n" + HANDLE_TASKS_NEW + HANDLE_TASK_NEW + "\n"

with open(handler_path, "w", encoding="utf-8") as f:
    f.write(nuevo_src)

print("Archivo escrito.")

import py_compile
try:
    py_compile.compile(handler_path, doraise=True)
    print("OK handler.py sintaxis correcta")
except py_compile.PyCompileError as e:
    print("ERROR sintaxis: {}".format(e))