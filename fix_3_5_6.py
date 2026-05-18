"""
fix_3_5_6.py — Subfase 3.5.6: Runtime Observability
Crea:
  1. app/services/runtime_status.py  — estado en memoria
  2. app/api/runtime.py              — GET /runtime/status
Modifica:
  3. app/runner/task_runner.py       — heartbeat + metricas (quirurgico)
  4. app/api/__init__.py             — registrar runtime router
"""

import os
import py_compile

# ── 1. app/services/runtime_status.py (NUEVO) ──────────────────────────────

svc_path = r"C:\Users\admin\knowledge-core\hermes\app\services\runtime_status.py"

RUNTIME_STATUS_SRC = '''"""
runtime_status.py — Subfase 3.5.6
Estado operacional del runner en memoria.
NO persistido en DB — se reinicia con cada restart.
Ref: docs/runtime_architecture.md
"""
from datetime import datetime, timezone
from typing import Optional


class RuntimeStatus:
    """
    Singleton en memoria para estado operacional del runner.
    Actualizado por el runner en cada ciclo.
    """

    def __init__(self):
        self.runner_started_at: Optional[datetime] = None
        self.last_loop_at: Optional[datetime] = None
        self.last_task_started_at: Optional[datetime] = None
        self.last_task_completed_at: Optional[datetime] = None
        self.current_task_id: Optional[str] = None
        self.current_task_title: Optional[str] = None
        self.total_processed: int = 0
        self.total_success: int = 0
        self.total_failed: int = 0
        self.runner_alive: bool = False

    def mark_started(self):
        self.runner_started_at = datetime.now(timezone.utc)
        self.runner_alive = True

    def mark_loop(self):
        self.last_loop_at = datetime.now(timezone.utc)

    def mark_task_started(self, task_id: str, task_title: str):
        self.current_task_id = task_id
        self.current_task_title = task_title
        self.last_task_started_at = datetime.now(timezone.utc)

    def mark_task_done(self):
        self.last_task_completed_at = datetime.now(timezone.utc)
        self.current_task_id = None
        self.current_task_title = None
        self.total_processed += 1
        self.total_success += 1

    def mark_task_failed(self):
        self.last_task_completed_at = datetime.now(timezone.utc)
        self.current_task_id = None
        self.current_task_title = None
        self.total_processed += 1
        self.total_failed += 1

    def health_status(self) -> str:
        if not self.runner_alive:
            return "offline"
        if self.last_loop_at is None:
            return "starting"
        delta = (datetime.now(timezone.utc) - self.last_loop_at).total_seconds()
        if delta > 30:
            return "degraded"
        return "healthy"

    def to_dict(self) -> dict:
        def fmt(dt):
            return dt.isoformat() if dt else None
        return {
            "runner_alive": self.runner_alive,
            "runner_started_at": fmt(self.runner_started_at),
            "last_loop_at": fmt(self.last_loop_at),
            "last_task_started_at": fmt(self.last_task_started_at),
            "last_task_completed_at": fmt(self.last_task_completed_at),
            "current_task_id": self.current_task_id,
            "current_task_title": self.current_task_title,
            "total_processed": self.total_processed,
            "total_success": self.total_success,
            "total_failed": self.total_failed,
            "runtime_status": self.health_status(),
        }


# Instancia global — unica fuente de verdad en memoria
runtime_status = RuntimeStatus()
'''

if not os.path.exists(svc_path):
    with open(svc_path, "w", encoding="utf-8") as f:
        f.write(RUNTIME_STATUS_SRC)
    print("OK app/services/runtime_status.py creado")
else:
    print("SKIP runtime_status.py ya existe")

py_compile.compile(svc_path, doraise=True)
print("OK runtime_status.py — sintaxis correcta")

# ── 2. app/api/runtime.py (NUEVO) ───────────────────────────────────────────

runtime_api_path = r"C:\Users\admin\knowledge-core\hermes\app\api\runtime.py"

RUNTIME_API_SRC = '''"""
runtime.py — Subfase 3.5.6
Endpoint de observabilidad operacional del runner.
"""
import logging
from fastapi import APIRouter
from app.db.engine import AsyncSessionLocal
from app.repositories.task_repository import TaskRepository
from app.services.runtime_status import runtime_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.get("/status", summary="Estado operacional del runner")
async def get_runtime_status():
    """
    Retorna estado real del runner en memoria + conteos reales de PostgreSQL.
    NO metricas inventadas. Solo datos reales.
    """
    data = runtime_status.to_dict()

    # Conteos reales desde PostgreSQL
    try:
        async with AsyncSessionLocal() as session:
            repo = TaskRepository(session)
            _, pending = await repo.list_tasks(limit=1, offset=0, status="pending")
            _, doing = await repo.list_tasks(limit=1, offset=0, status="doing")
            _, failed = await repo.list_tasks(limit=1, offset=0, status="failed")

        data["backlog"] = {
            "pending": pending,
            "doing": doing,
            "failed": failed,
        }

        # Stuck tasks: doing con started_at no null
        # (visibilidad — no recovery automatico)
        stuck_count = doing  # todas las doing son potencialmente stuck al startup
        data["stuck_tasks"] = stuck_count

    except Exception as exc:
        logger.error("runtime/status DB error: %s", exc)
        data["backlog"] = {"error": str(exc)}
        data["stuck_tasks"] = None

    return data
'''

if not os.path.exists(runtime_api_path):
    with open(runtime_api_path, "w", encoding="utf-8") as f:
        f.write(RUNTIME_API_SRC)
    print("OK app/api/runtime.py creado")
else:
    print("SKIP runtime.py ya existe")

py_compile.compile(runtime_api_path, doraise=True)
print("OK runtime.py — sintaxis correcta")

# ── 3. task_runner.py — heartbeat + metricas (quirurgico) ───────────────────

runner_path = r"C:\Users\admin\knowledge-core\hermes\app\runner\task_runner.py"

with open(runner_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Agregar import runtime_status
has_runtime = any("runtime_status" in l for l in lines)
if not has_runtime:
    for i, l in enumerate(lines):
        if "from app.runner.executors import execute_task" in l:
            lines.insert(i+1, "from app.services.runtime_status import runtime_status\n")
            print("OK runner — import runtime_status agregado")
            break

with open(runner_path, "w", encoding="utf-8") as f:
    f.writelines(lines)
with open(runner_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Agregar runtime_status.mark_started() al inicio de runner_loop
for i, l in enumerate(lines):
    if 'logger.info("runner: loop iniciado' in l:
        if "mark_started" not in "".join(lines[i-2:i+2]):
            lines.insert(i, "    runtime_status.mark_started()\n")
            print("OK runner — mark_started agregado")
        break

with open(runner_path, "w", encoding="utf-8") as f:
    f.writelines(lines)
with open(runner_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Agregar mark_loop() al inicio del while True
for i, l in enumerate(lines):
    if "while True:" in l:
        # Insertar mark_loop despues del try:
        for j in range(i, min(i+5, len(lines))):
            if "try:" in lines[j]:
                if "mark_loop" not in "".join(lines[j:j+3]):
                    lines.insert(j+1, "            runtime_status.mark_loop()\n")
                    print("OK runner — mark_loop agregado en loop")
                break
        break

with open(runner_path, "w", encoding="utf-8") as f:
    f.writelines(lines)
with open(runner_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Agregar mark_task_started despues de logger procesando
for i, l in enumerate(lines):
    if 'logger.info("runner: procesando task_id=%s title=%s"' in l:
        if "mark_task_started" not in "".join(lines[i:i+3]):
            lines.insert(i+1, "            runtime_status.mark_task_started(str(task_id), task.title)\n")
            print("OK runner — mark_task_started agregado")
        break

with open(runner_path, "w", encoding="utf-8") as f:
    f.writelines(lines)
with open(runner_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Agregar mark_task_done despues de _persist_result
for i, l in enumerate(lines):
    if "await _persist_result(task_id, result)" in l:
        if "mark_task_done" not in "".join(lines[i:i+3]):
            lines.insert(i+1, "                runtime_status.mark_task_done()\n")
            print("OK runner — mark_task_done agregado")
        break

with open(runner_path, "w", encoding="utf-8") as f:
    f.writelines(lines)
with open(runner_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Agregar mark_task_failed despues de _persist_error en except exec
for i, l in enumerate(lines):
    if "await _persist_error(task_id, error_msg)" in l:
        if "mark_task_failed" not in "".join(lines[i:i+3]):
            lines.insert(i+1, "                runtime_status.mark_task_failed()\n")
            print("OK runner — mark_task_failed agregado")
        break

with open(runner_path, "w", encoding="utf-8") as f:
    f.writelines(lines)

py_compile.compile(runner_path, doraise=True)
print("OK task_runner.py — sintaxis correcta")

# ── 4. app/api/__init__.py — registrar runtime router ───────────────────────

init_path = r"C:\Users\admin\knowledge-core\hermes\app\api\__init__.py"

with open(init_path, "r", encoding="utf-8") as f:
    src = f.read()

if "runtime" not in src:
    OLD = "from app.routers.tasks import router as tasks_router"
    NEW = "from app.routers.tasks import router as tasks_router\nfrom app.api.runtime import router as runtime_router"
    assert OLD in src, "ERROR: tasks_router import no encontrado"
    src = src.replace(OLD, NEW, 1)

    OLD_INCLUDE = "api_router.include_router(tasks_router)"
    NEW_INCLUDE = "api_router.include_router(tasks_router)\napi_router.include_router(runtime_router)"
    assert OLD_INCLUDE in src, "ERROR: include tasks_router no encontrado"
    src = src.replace(OLD_INCLUDE, NEW_INCLUDE, 1)

    with open(init_path, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK app/api/__init__.py — runtime_router registrado")
else:
    print("SKIP __init__.py — runtime ya registrado")

py_compile.compile(init_path, doraise=True)
print("OK __init__.py — sintaxis correcta")

print("\nfix_3_5_6.py completado")