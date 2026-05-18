"""
fix_3_2.py — Subfase 3.2: Agrega filtro ?status= a GET /tasks
Modifica:
  1. task_repository.py → list_tasks acepta status opcional
  2. tasks.py (router) → GET /tasks acepta Query param status
"""

import re

# ── ARCHIVO 1: task_repository.py ──────────────────────────────────────────

repo_path = r"C:\Users\admin\knowledge-core\hermes\app\repositories\task_repository.py"

with open(repo_path, "r", encoding="utf-8") as f:
    repo_src = f.read()

# Cambio 1a: firma del método list_tasks
OLD_FIRMA = (
    "    async def list_tasks(\n"
    "        self,\n"
    "        limit: int = 20,\n"
    "        offset: int = 0,\n"
    "    ) -> tuple[list[Task], int]:"
)
NEW_FIRMA = (
    "    async def list_tasks(\n"
    "        self,\n"
    "        limit: int = 20,\n"
    "        offset: int = 0,\n"
    "        status: Optional[str] = None,\n"
    "    ) -> tuple[list[Task], int]:"
)

# Cambio 1b: count query — agregar where condicional
OLD_COUNT = (
    "            count_result = await self.session.execute(\n"
    "                select(func.count()).select_from(Task)\n"
    "            )"
)
NEW_COUNT = (
    "            count_q = select(func.count()).select_from(Task)\n"
    "            if status is not None:\n"
    "                count_q = count_q.where(Task.status == status)\n"
    "            count_result = await self.session.execute(count_q)"
)

# Cambio 1c: rows query — agregar where condicional
OLD_ROWS = (
    "            rows_result = await self.session.execute(\n"
    "                select(Task)\n"
    "                .order_by(Task.created_at.desc())\n"
    "                .limit(limit)\n"
    "                .offset(offset)\n"
    "            )"
)
NEW_ROWS = (
    "            rows_q = (\n"
    "                select(Task)\n"
    "                .order_by(Task.created_at.desc())\n"
    "                .limit(limit)\n"
    "                .offset(offset)\n"
    "            )\n"
    "            if status is not None:\n"
    "                rows_q = rows_q.where(Task.status == status)\n"
    "            rows_result = await self.session.execute(rows_q)"
)

assert OLD_FIRMA in repo_src, "ERROR: firma list_tasks no encontrada"
assert OLD_COUNT in repo_src, "ERROR: count query no encontrada"
assert OLD_ROWS in repo_src,  "ERROR: rows query no encontrada"

repo_src = repo_src.replace(OLD_FIRMA, NEW_FIRMA)
repo_src = repo_src.replace(OLD_COUNT, NEW_COUNT)
repo_src = repo_src.replace(OLD_ROWS,  NEW_ROWS)

with open(repo_path, "w", encoding="utf-8") as f:
    f.write(repo_src)

print("✅ task_repository.py — list_tasks actualizado con filtro status")

# ── ARCHIVO 2: tasks.py (router) ────────────────────────────────────────────

router_path = r"C:\Users\admin\knowledge-core\hermes\app\routers\tasks.py"

with open(router_path, "r", encoding="utf-8") as f:
    router_src = f.read()

# Cambio 2a: imports — agregar Optional
OLD_IMPORT = "from typing import"
if "from typing import" not in router_src:
    # No hay typing import, lo agregamos junto a los otros imports
    OLD_IMPORT_BLOCK = "from uuid import UUID"
    NEW_IMPORT_BLOCK = "from typing import Optional\nfrom uuid import UUID"
    assert OLD_IMPORT_BLOCK in router_src, "ERROR: 'from uuid import UUID' no encontrado"
    router_src = router_src.replace(OLD_IMPORT_BLOCK, NEW_IMPORT_BLOCK)
    print("✅ tasks.py — import Optional agregado")

# Cambio 2b: firma del endpoint list_tasks
OLD_ENDPOINT_FIRMA = (
    "async def list_tasks(\n"
    "    limit: int = Query(default=20, ge=1, le=100, description=\"MÃ¡ximo de items a devolver.\"),\n"
    "    offset: int = Query(default=0, ge=0, description=\"NÃºmero de items a saltar.\"),\n"
    "    repo: TaskRepository = Depends(_get_repo),\n"
    ") -> list[TaskRead]:"
)
NEW_ENDPOINT_FIRMA = (
    "async def list_tasks(\n"
    "    limit: int = Query(default=20, ge=1, le=100, description=\"Máximo de items a devolver.\"),\n"
    "    offset: int = Query(default=0, ge=0, description=\"Número de items a saltar.\"),\n"
    "    status: Optional[str] = Query(default=None, description=\"Filtrar por status: pending, doing, review, done, failed.\"),\n"
    "    repo: TaskRepository = Depends(_get_repo),\n"
    ") -> list[TaskRead]:"
)

# Cambio 2c: llamada al repo dentro del endpoint
OLD_REPO_CALL = "        tasks, total = await repo.list_tasks(limit=limit, offset=offset)"
NEW_REPO_CALL = "        tasks, total = await repo.list_tasks(limit=limit, offset=offset, status=status)"

assert OLD_REPO_CALL in router_src, "ERROR: llamada repo.list_tasks no encontrada"

router_src = router_src.replace(OLD_REPO_CALL, NEW_REPO_CALL)

# Para la firma usamos búsqueda flexible por si hay encoding raro
if OLD_ENDPOINT_FIRMA in router_src:
    router_src = router_src.replace(OLD_ENDPOINT_FIRMA, NEW_ENDPOINT_FIRMA)
    print("✅ tasks.py — firma endpoint actualizada (match exacto)")
else:
    # Patch alternativo con regex tolerante a encoding
    pattern = re.compile(
        r'(async def list_tasks\(\s*\n)'
        r'(\s+limit:.*?\n)'
        r'(\s+offset:.*?\n)'
        r'(\s+repo:.*?\n)'
        r'(\) -> list\[TaskRead\]:)',
        re.DOTALL
    )
    replacement = (
        r'\1'
        r'\2'
        r'\3'
        '    status: Optional[str] = Query(default=None, description="Filtrar por status: pending, doing, review, done, failed."),\n'
        r'\4'
        r'\5'
    )
    router_src, n = pattern.subn(replacement, router_src)
    if n:
        print("✅ tasks.py — firma endpoint actualizada (regex fallback)")
    else:
        print("❌ ERROR: no se pudo parchear firma del endpoint list_tasks")

with open(router_path, "w", encoding="utf-8") as f:
    f.write(router_src)

print("✅ tasks.py — llamada repo.list_tasks actualizada con status=status")
print("\n🎯 fix_3_2.py completado — valida con py_compile a continuación")