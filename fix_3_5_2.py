"""
fix_3_5_2.py — Subfase 3.5.2: Execution Engine
Modifica SOLO: app/runner/executors.py
- Agrega duration_ms
- Agrega campo executor: "default"
- Agrega timeout con asyncio.wait_for()
- Agrega manejo controlado de errores y timeout
- Usa payload de la task para simular fail/timeout en validacion
"""

executors_path = r"C:\Users\admin\knowledge-core\hermes\app\runner\executors.py"

NEW_EXECUTORS = '''"""
executors.py — Subfase 3.5.2
Executor desacoplado del runner.
Arquitectura: Task -> Runner -> Executor -> Resultado
Ref: docs/runtime_architecture.md
"""
import asyncio
import logging
import time

from app.models.task import Task

logger = logging.getLogger(__name__)

EXECUTOR_TIMEOUT = 30  # segundos — timeout simple, sin retry frameworks


async def _run(task: Task) -> dict:
    """
    Logica interna de ejecucion.
    Separada para que wait_for() pueda aplicar timeout limpio.
    Usa payload para simular escenarios en validacion:
      payload={"simulate": "fail"}    -> lanza excepcion
      payload={"simulate": "timeout"} -> duerme 60s (provoca timeout)
    """
    start_ms = time.monotonic()

    simulate = None
    if task.payload and isinstance(task.payload, dict):
        simulate = task.payload.get("simulate")

    if simulate == "fail":
        logger.warning("executor: simulando fallo task_id=%s", task.id)
        raise ValueError("Fallo simulado via payload.simulate=fail")

    if simulate == "timeout":
        logger.warning("executor: simulando timeout task_id=%s", task.id)
        await asyncio.sleep(60)  # excede EXECUTOR_TIMEOUT=30

    # Ejecucion normal
    await asyncio.sleep(1)

    duration_ms = int((time.monotonic() - start_ms) * 1000)

    return {
        "executed": True,
        "task_id": str(task.id),
        "executor": "default",
        "duration_ms": duration_ms,
        "message": "Task ejecutada correctamente",
    }


async def execute_task(task: Task) -> dict:
    """
    Punto de entrada del executor.
    Aplica timeout. Maneja errores. Nunca crashea el runner.
    """
    logger.info("executor: iniciando task_id=%s title=%s", task.id, task.title)

    try:
        result = await asyncio.wait_for(_run(task), timeout=EXECUTOR_TIMEOUT)
        logger.info(
            "executor: completado task_id=%s duration_ms=%s",
            task.id,
            result.get("duration_ms"),
        )
        return result

    except asyncio.TimeoutError:
        msg = "Executor timeout despues de {}s".format(EXECUTOR_TIMEOUT)
        logger.error("executor: timeout task_id=%s", task.id)
        raise RuntimeError(msg)

    except Exception as exc:
        logger.error("executor: error task_id=%s error=%s", task.id, exc)
        raise
'''

with open(executors_path, "w", encoding="utf-8") as f:
    f.write(NEW_EXECUTORS)
print("OK app/runner/executors.py reescrito")

import py_compile
try:
    py_compile.compile(executors_path, doraise=True)
    print("OK sintaxis correcta")
except py_compile.PyCompileError as e:
    print("ERROR sintaxis: {}".format(e))