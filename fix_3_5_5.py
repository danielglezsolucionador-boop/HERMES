"""
fix_3_5_5.py — Subfase 3.5.5: Controlled Retry System
Cambios quirurgicos — NO reescrituras completas.
  1. models/task.py          — retry_count, max_retries, last_retry_at
  2. schemas/task.py         — exponer en TaskRead
  3. task_repository.py      — metodo retry_task
  4. routers/tasks.py        — endpoint PATCH /tasks/{task_id}/retry
"""

import py_compile

# ── 1. models/task.py ───────────────────────────────────────────────────────

model_path = r"C:\Users\admin\knowledge-core\hermes\app\models\task.py"

with open(model_path, "r", encoding="utf-8") as f:
    src = f.read()

OLD_COL = "    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)\n    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)"
NEW_COL = (
    "    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)\n"
    "    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)\n"
    "    last_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)\n"
    "    retry_count: Mapped[int] = mapped_column(default=0, nullable=False, server_default='0')\n"
    "    max_retries: Mapped[int] = mapped_column(default=3, nullable=False, server_default='3')"
)

if "retry_count" not in src:
    assert OLD_COL in src, "ERROR: columnas timestamp no encontradas en modelo"
    src = src.replace(OLD_COL, NEW_COL, 1)
    with open(model_path, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK models/task.py — retry_count, max_retries, last_retry_at agregados")
else:
    print("SKIP models/task.py — retry fields ya existen")

py_compile.compile(model_path, doraise=True)
print("OK models/task.py — sintaxis correcta")

# ── 2. schemas/task.py ──────────────────────────────────────────────────────

schema_path = r"C:\Users\admin\knowledge-core\hermes\app\schemas\task.py"

with open(schema_path, "r", encoding="utf-8") as f:
    src = f.read()

OLD_SCHEMA = "    started_at: datetime | None\n    completed_at: datetime | None"
NEW_SCHEMA = (
    "    started_at: datetime | None\n"
    "    completed_at: datetime | None\n"
    "    last_retry_at: datetime | None\n"
    "    retry_count: int\n"
    "    max_retries: int"
)

if "retry_count" not in src:
    assert OLD_SCHEMA in src, "ERROR: campos timestamp no encontrados en schema"
    src = src.replace(OLD_SCHEMA, NEW_SCHEMA, 1)
    with open(schema_path, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK schemas/task.py — retry fields agregados a TaskRead")
else:
    print("SKIP schemas/task.py — retry fields ya existen")

py_compile.compile(schema_path, doraise=True)
print("OK schemas/task.py — sintaxis correcta")

# ── 3. task_repository.py — metodo retry_task ───────────────────────────────

repo_path = r"C:\Users\admin\knowledge-core\hermes\app\repositories\task_repository.py"

with open(repo_path, "r", encoding="utf-8") as f:
    src = f.read()

RETRY_METHOD = '''
    # ─────────────────────────────────────────────
    # RETRY
    # ─────────────────────────────────────────────
    async def retry_task(self, task_id: UUID) -> tuple:
        """
        Reintenta una task fallida.
        Retorna (task, error_msg) donde error_msg es None si ok.
        Condiciones:
          - status debe ser failed
          - retry_count < max_retries
        Si valido: incrementa retry_count, limpia error, vuelve a pending.
        """
        from datetime import datetime, timezone
        try:
            task = await self.get_task(task_id)
            if task is None:
                return None, "not_found"

            if task.status != "failed":
                return task, "not_failed"

            if task.retry_count >= task.max_retries:
                return task, "max_retries_reached"

            values = {
                "status": "pending",
                "retry_count": task.retry_count + 1,
                "last_retry_at": datetime.now(timezone.utc),
                "error": None,
                "result": None,
                "started_at": None,
                "completed_at": None,
            }
            await self.session.execute(
                __import__("sqlalchemy").update(
                    __import__("app.models.task", fromlist=["Task"]).Task
                ).where(
                    __import__("app.models.task", fromlist=["Task"]).Task.id == task_id
                ).values(**values)
            )
            await self.session.commit()
            task = await self.get_task(task_id)
            logger.info(
                "retry_task: task_id=%s retry_count=%d max_retries=%d",
                task_id, task.retry_count, task.max_retries,
            )
            return task, None
        except Exception as exc:
            await self.session.rollback()
            logger.error("retry_task error task_id=%s: %s", task_id, exc)
            raise
'''

if "retry_task" not in src:
    # Insertar antes de DELETE
    idx = src.find("    async def delete_task")
    assert idx != -1, "ERROR: delete_task no encontrado en repository"
    src = src[:idx] + RETRY_METHOD + "\n" + src[idx:]
    with open(repo_path, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK task_repository.py — retry_task agregado")
else:
    print("SKIP task_repository.py — retry_task ya existe")

py_compile.compile(repo_path, doraise=True)
print("OK task_repository.py — sintaxis correcta")

# ── 4. routers/tasks.py — endpoint retry ────────────────────────────────────

router_path = r"C:\Users\admin\knowledge-core\hermes\app\routers\tasks.py"

with open(router_path, "r", encoding="utf-8") as f:
    src = f.read()

RETRY_ENDPOINT = '''

@router.patch(
    "/{task_id}/retry",
    response_model=TaskRead,
    summary="Reintentar una task fallida",
)
async def retry_task(
    task_id: str,
    repo: TaskRepository = Depends(_get_repo),
) -> TaskRead:
    """
    Reintenta una task fallida.
    409 si no esta en failed o si alcanzo max_retries.
    """
    uid = _validate_uuid(task_id)
    try:
        task, error = await repo.retry_task(uid)
    except SQLAlchemyError as exc:
        logger.error("PATCH /tasks/%s/retry DB error: %s", task_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de base de datos al reintentar task.",
        )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task no encontrada: {}".format(task_id),
        )

    if error == "not_failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se pueden reintentar tasks en estado failed.",
        )

    if error == "max_retries_reached":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task alcanzo el maximo de retries ({}).".format(task.max_retries),
        )

    logger.info(
        "PATCH /tasks/%s/retry -> pending retry_count=%d",
        task_id, task.retry_count,
    )
    return TaskRead.model_validate(task)
'''

if "retry_task" not in src:
    src = src.rstrip() + RETRY_ENDPOINT + "\n"
    with open(router_path, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK routers/tasks.py — endpoint PATCH /retry agregado")
else:
    print("SKIP routers/tasks.py — endpoint retry ya existe")

py_compile.compile(router_path, doraise=True)
print("OK routers/tasks.py — sintaxis correcta")

print("\nfix_3_5_5.py completado — genera migracion alembic a continuacion")