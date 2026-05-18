"""
fix_3_5.py — Subfase 3.5.1: Runner Core
Crea:
  1. app/runner/executors.py
  2. app/runner/task_runner.py
Modifica:
  3. app/main.py — arrancar runner en lifespan
"""

import os

# ── ARCHIVO 1: executors.py ─────────────────────────────────────────────────

executors_path = r"C:\Users\admin\knowledge-core\hermes\app\runner\executors.py"

EXECUTORS_SRC = '''"""
executors.py — Subfase 3.5.1
Executor simple. Un solo punto de ejecucion de tasks.
Arquitectura: Task -> Runner -> Executor -> PostgreSQL
"""
import asyncio
import logging
from app.models.task import Task

logger = logging.getLogger(__name__)


async def execute_task(task: Task) -> dict:
    """
    Executor base. Recibe una task, la ejecuta, retorna resultado.
    Subfase 3.5.1: implementacion minima controlada.
    Subfases futuras reemplazaran esto con logica real.
    """
    logger.info("executor: iniciando task_id=%s title=%s", task.id, task.title)

    # Simulacion de trabajo — reemplazar en subfases futuras
    await asyncio.sleep(1)

    result = {
        "executed": True,
        "task_id": str(task.id),
        "message": "Task ejecutada correctamente",
    }

    logger.info("executor: completado task_id=%s", task.id)
    return result
'''

with open(executors_path, "w", encoding="utf-8") as f:
    f.write(EXECUTORS_SRC)
print("OK app/runner/executors.py creado")

# ── ARCHIVO 2: task_runner.py ───────────────────────────────────────────────

runner_path = r"C:\Users\admin\knowledge-core\hermes\app\runner\task_runner.py"

RUNNER_SRC = '''"""
task_runner.py — Subfase 3.5.1
Runner loop principal de Hermes.
Arquitectura: Task -> Runner -> Executor -> PostgreSQL
UN SOLO RUNNER. UN SOLO LOOP. UN SOLO FLUJO.
Ref: docs/runtime_architecture.md
"""
import asyncio
import logging

from app.db.engine import AsyncSessionLocal
from app.repositories.task_repository import TaskRepository
from app.runner.executors import execute_task

logger = logging.getLogger(__name__)

POLL_INTERVAL = 5  # segundos entre ciclos


async def _get_next_pending() -> object | None:
    """Busca la task pending mas antigua. Retorna Task o None."""
    async with AsyncSessionLocal() as session:
        repo = TaskRepository(session)
        tasks, total = await repo.list_tasks(limit=1, offset=0, status="pending")
        if tasks:
            logger.debug("runner: task pending encontrada id=%s", tasks[0].id)
            return tasks[0]
        return None


async def _mark_doing(task_id) -> None:
    """Marca la task como doing."""
    async with AsyncSessionLocal() as session:
        repo = TaskRepository(session)
        await repo.update_task_status(task_id, "done")
        # Reusar update_task para status doing
        from sqlalchemy import update
        from app.models.task import Task
        await session.execute(
            update(Task).where(Task.id == task_id).values(status="doing")
        )
        await session.commit()
    logger.info("runner: task_id=%s -> doing", task_id)


async def _persist_result(task_id, result: dict) -> None:
    """Persiste resultado y marca done."""
    async with AsyncSessionLocal() as session:
        repo = TaskRepository(session)
        await repo.update_task(task_id, {"status": "done", "result": result})
    logger.info("runner: task_id=%s -> done", task_id)


async def _persist_error(task_id, error: str) -> None:
    """Persiste error y marca failed."""
    async with AsyncSessionLocal() as session:
        repo = TaskRepository(session)
        await repo.update_task(task_id, {"status": "failed", "error": error})
    logger.warning("runner: task_id=%s -> failed error=%s", task_id, error)


async def runner_loop() -> None:
    """
    Loop principal del runner.
    while True:
        buscar 1 task pending
        ejecutar
        persistir resultado
        dormir POLL_INTERVAL segundos
    Sobrevive excepciones — nunca crashea el proceso principal.
    """
    logger.info("runner: loop iniciado (poll_interval=%ds)", POLL_INTERVAL)

    while True:
        try:
            task = await _get_next_pending()

            if task is None:
                logger.debug("runner: sin tasks pending, durmiendo %ds", POLL_INTERVAL)
                await asyncio.sleep(POLL_INTERVAL)
                continue

            task_id = task.id
            logger.info("runner: procesando task_id=%s title=%s", task_id, task.title)

            # Marcar doing
            async with AsyncSessionLocal() as session:
                repo = TaskRepository(session)
                await repo.update_task_status(task_id, "doing")
            logger.info("runner: task_id=%s -> doing", task_id)

            # Ejecutar
            try:
                result = await execute_task(task)
                await _persist_result(task_id, result)
            except Exception as exec_exc:
                error_msg = str(exec_exc)
                logger.error("runner: executor fallo task_id=%s error=%s", task_id, error_msg)
                await _persist_error(task_id, error_msg)

        except Exception as loop_exc:
            # El runner sobrevive cualquier excepcion — regla de oro
            logger.error("runner: error en loop (sobreviviendo): %s", loop_exc)

        await asyncio.sleep(POLL_INTERVAL)
'''

with open(runner_path, "w", encoding="utf-8") as f:
    f.write(RUNNER_SRC)
print("OK app/runner/task_runner.py creado")

# ── ARCHIVO 3: main.py — agregar runner al lifespan ────────────────────────

main_path = r"C:\Users\admin\knowledge-core\hermes\app\main.py"

with open(main_path, "r", encoding="utf-8") as f:
    main_src = f.read()

# Cambio 3a: import runner
OLD_IMPORT = "from app.telegram.polling import start_polling, stop_polling"
NEW_IMPORT = "from app.telegram.polling import start_polling, stop_polling\nfrom app.runner.task_runner import runner_loop"

if "runner_loop" in main_src:
    print("WARNING runner_loop ya importado en main.py")
else:
    assert OLD_IMPORT in main_src, "ERROR: import polling no encontrado en main.py"
    main_src = main_src.replace(OLD_IMPORT, NEW_IMPORT)
    print("OK main.py import runner_loop agregado")

# Cambio 3b: arrancar runner en lifespan junto al polling
OLD_POLLING = "asyncio.ensure_future(start_polling())"
NEW_POLLING = "asyncio.ensure_future(start_polling())\n    asyncio.ensure_future(runner_loop())"

if "runner_loop()" in main_src:
    print("WARNING runner_loop() ya en lifespan")
else:
    assert OLD_POLLING in main_src, "ERROR: ensure_future polling no encontrado"
    main_src = main_src.replace(OLD_POLLING, NEW_POLLING)
    print("OK main.py runner_loop agregado al lifespan")

with open(main_path, "w", encoding="utf-8") as f:
    f.write(main_src)

print("\nValidando sintaxis...")
import py_compile
for path in [executors_path, runner_path, main_path]:
    try:
        py_compile.compile(path, doraise=True)
        print("OK {}".format(path.split("\\")[-1]))
    except py_compile.PyCompileError as e:
        print("ERROR {}: {}".format(path.split("\\")[-1], e))

print("\nfix_3_5.py completado")