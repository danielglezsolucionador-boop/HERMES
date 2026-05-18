"""
fix_3_5_4.py — Subfase 3.5.4: Runtime Consistency & Recovery
Cambios quirurgicos:
  1. app/models/task.py        — agregar started_at, completed_at
  2. app/runner/task_runner.py — persistir timestamps
  3. app/main.py               — recovery scan al startup
  4. genera migracion alembic
NO reescribe archivos completos.
"""

import os
import py_compile

# ── ARCHIVO 1: models/task.py — agregar started_at, completed_at ───────────

model_path = r"C:\Users\admin\knowledge-core\hermes\app\models\task.py"

with open(model_path, "r", encoding="utf-8") as f:
    src = f.read()

# Agregar import de datetime si no existe
OLD_IMPORTS = "from sqlalchemy import String, Text, JSON"
NEW_IMPORTS  = "from datetime import datetime, timezone\nfrom sqlalchemy import String, Text, JSON, DateTime"

if "from datetime import" not in src:
    assert OLD_IMPORTS in src, "ERROR: imports sqlalchemy no encontrados"
    src = src.replace(OLD_IMPORTS, NEW_IMPORTS, 1)
    print("OK modelo — imports datetime agregados")

# Agregar columnas antes del cierre de la clase
OLD_ERROR_COL = "    error: Mapped[str | None] = mapped_column(Text, nullable=True)"
NEW_ERROR_COL = (
    "    error: Mapped[str | None] = mapped_column(Text, nullable=True)\n"
    "    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)\n"
    "    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)"
)

if "started_at" not in src:
    assert OLD_ERROR_COL in src, "ERROR: columna error no encontrada en modelo"
    src = src.replace(OLD_ERROR_COL, NEW_ERROR_COL, 1)
    print("OK modelo — started_at, completed_at agregados")
else:
    print("SKIP modelo — started_at ya existe")

with open(model_path, "w", encoding="utf-8") as f:
    f.write(src)

py_compile.compile(model_path, doraise=True)
print("OK models/task.py — sintaxis correcta")

# ── ARCHIVO 2: task_runner.py — persistir timestamps ───────────────────────

runner_path = r"C:\Users\admin\knowledge-core\hermes\app\runner\task_runner.py"

with open(runner_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Agregar import datetime si no existe
has_datetime = any("from datetime import" in l for l in lines)
if not has_datetime:
    for i, l in enumerate(lines):
        if "import traceback" in l:
            lines.insert(i+1, "from datetime import datetime, timezone\n")
            print("OK runner — import datetime agregado")
            break

# Guardar y releer
with open(runner_path, "w", encoding="utf-8") as f:
    f.writelines(lines)
with open(runner_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Patch: persistir started_at cuando se marca doing
# Buscar linea: await repo.update_task_status(task_id, "doing")
for i, l in enumerate(lines):
    if 'await repo.update_task_status(task_id, "doing")' in l and "started_at" not in "".join(lines[i:i+3]):
        lines[i] = (
            '                await repo.update_task(\n'
            '                    task_id,\n'
            '                    {"status": "doing", "started_at": datetime.now(timezone.utc)},\n'
            '                )\n'
        )
        print("OK runner — started_at persistido al marcar doing")
        break

with open(runner_path, "w", encoding="utf-8") as f:
    f.writelines(lines)
with open(runner_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Patch: persistir completed_at en _persist_result
for i, l in enumerate(lines):
    if 'await repo.update_task(task_id, {"status": "done", "result": result})' in l:
        lines[i] = (
            '        await repo.update_task(\n'
            '            task_id,\n'
            '            {\n'
            '                "status": "done",\n'
            '                "result": result,\n'
            '                "completed_at": datetime.now(timezone.utc),\n'
            '            },\n'
            '        )\n'
        )
        print("OK runner — completed_at persistido en _persist_result")
        break

with open(runner_path, "w", encoding="utf-8") as f:
    f.writelines(lines)
with open(runner_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Patch: persistir completed_at en _persist_error
for i, l in enumerate(lines):
    if 'await repo.update_task(task_id, {"status": "failed", "error": error})' in l:
        lines[i] = (
            '            await repo.update_task(\n'
            '                task_id,\n'
            '                {\n'
            '                    "status": "failed",\n'
            '                    "error": error,\n'
            '                    "completed_at": datetime.now(timezone.utc),\n'
            '                },\n'
            '            )\n'
        )
        print("OK runner — completed_at persistido en _persist_error")
        break

with open(runner_path, "w", encoding="utf-8") as f:
    f.writelines(lines)

py_compile.compile(runner_path, doraise=True)
print("OK task_runner.py — sintaxis correcta")

# ── ARCHIVO 3: main.py — recovery scan al startup ──────────────────────────

main_path = r"C:\Users\admin\knowledge-core\hermes\app\main.py"

with open(main_path, "r", encoding="utf-8") as f:
    src = f.read()

# Agregar import recovery_scan
OLD_RUNNER_IMPORT = "from app.runner.task_runner import runner_loop"
NEW_RUNNER_IMPORT = "from app.runner.task_runner import runner_loop, recovery_scan"

if "recovery_scan" not in src:
    assert OLD_RUNNER_IMPORT in src, "ERROR: import runner_loop no encontrado"
    src = src.replace(OLD_RUNNER_IMPORT, NEW_RUNNER_IMPORT, 1)
    print("OK main.py — import recovery_scan agregado")

# Agregar llamada recovery_scan antes de arrancar el runner
OLD_RUNNER_START = "    asyncio.ensure_future(runner_loop())"
NEW_RUNNER_START = "    await recovery_scan()\n    asyncio.ensure_future(runner_loop())"

if "await recovery_scan()" not in src:
    assert OLD_RUNNER_START in src, "ERROR: ensure_future runner_loop no encontrado"
    src = src.replace(OLD_RUNNER_START, NEW_RUNNER_START, 1)
    print("OK main.py — recovery_scan agregado al startup")

with open(main_path, "w", encoding="utf-8") as f:
    f.write(src)

py_compile.compile(main_path, doraise=True)
print("OK main.py — sintaxis correcta")

# ── ARCHIVO 4: task_runner.py — agregar funcion recovery_scan ──────────────

with open(runner_path, "r", encoding="utf-8") as f:
    src = f.read()

RECOVERY_SCAN = '''

async def recovery_scan() -> None:
    """
    Scan de recovery al startup.
    Detecta tasks zombie (doing sin completed_at).
    NO las re-ejecuta — solo visibilidad.
    Ref: docs/runtime_architecture.md
    """
    from datetime import timezone
    logger.info("runner: recovery_scan iniciado")
    try:
        async with AsyncSessionLocal() as session:
            repo = TaskRepository(session)
            tasks, total = await repo.list_tasks(limit=100, offset=0, status="doing")
            zombies = [t for t in tasks if t.completed_at is None]
            if zombies:
                logger.warning(
                    "runner: recovery_scan — %d task(s) zombie detectada(s):",
                    len(zombies),
                )
                for t in zombies:
                    age = ""
                    if t.started_at:
                        delta = datetime.now(timezone.utc) - t.started_at
                        age = "antiguedad={}s".format(int(delta.total_seconds()))
                    logger.warning(
                        "runner: zombie task_id=%s title=%s %s",
                        t.id, t.title, age,
                    )
            else:
                logger.info("runner: recovery_scan — sin tasks zombie")
    except Exception as exc:
        logger.error("runner: recovery_scan fallo: %s", exc)
'''

if "recovery_scan" not in src:
    # Insertar antes de runner_loop
    idx = src.find("async def runner_loop()")
    assert idx != -1, "ERROR: runner_loop no encontrado"
    src = src[:idx] + RECOVERY_SCAN + "\n" + src[idx:]
    with open(runner_path, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK task_runner.py — recovery_scan agregado")
else:
    print("SKIP task_runner.py — recovery_scan ya existe")

py_compile.compile(runner_path, doraise=True)
print("OK task_runner.py — sintaxis correcta (final)")

print("\nfix_3_5_4.py completado — genera migracion alembic a continuacion")