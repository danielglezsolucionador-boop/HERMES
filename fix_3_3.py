"""
fix_3_3.py — Subfase 3.3: Task State Management
Modifica:
  1. schemas/task.py      → agrega TaskStatusUpdate
  2. task_repository.py   → agrega update_task_status()
  3. tasks.py (router)    → agrega PATCH /tasks/{task_id}/status
"""

# ── ARCHIVO 1: schemas/task.py ──────────────────────────────────────────────

schema_path = r"C:\Users\admin\knowledge-core\hermes\app\schemas\task.py"

with open(schema_path, "r", encoding="utf-8") as f:
    schema_src = f.read()

# Agregar TaskStatusUpdate al final
TASK_STATUS_UPDATE = "\n\nclass TaskStatusUpdate(BaseModel):\n    status: TaskStatus\n"

if "TaskStatusUpdate" in schema_src:
    print("⚠️  TaskStatusUpdate ya existe en schemas/task.py — skip")
else:
    schema_src = schema_src.rstrip() + TASK_STATUS_UPDATE
    with open(schema_path, "w", encoding="utf-8") as f:
        f.write(schema_src)
    print("✅ schemas/task.py — TaskStatusUpdate agregado")

# ── ARCHIVO 2: task_repository.py ──────────────────────────────────────────

repo_path = r"C:\Users\admin\knowledge-core\hermes\app\repositories\task_repository.py"

with open(repo_path, "r", encoding="utf-8") as f:
    repo_src = f.read()

UPDATE_STATUS_METHOD = '''
    # ─────────────────────────────────────────────
    # UPDATE STATUS
    # ─────────────────────────────────────────────
    async def update_task_status(
        self,
        task_id: UUID,
        new_status: str,
    ) -> Optional[Task]:
        """
        Actualiza solo el status de una task.
        Retorna task actualizada o None si no existe.
        """
        try:
            task = await self.get_task(task_id)
            if task is None:
                logger.warning("update_task_status: id=%s no encontrada", task_id)
                return None

            await self.session.execute(
                update(Task).where(Task.id == task_id).values(status=new_status)
            )
            await self.session.commit()
            await self.session.refresh(task)
            logger.info(
                "Task status actualizado: id=%s status=%s",
                task_id,
                new_status,
            )
            return task
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error(
                "Error al actualizar status task id=%s: %s", task_id, exc
            )
            raise
'''

if "update_task_status" in repo_src:
    print("⚠️  update_task_status ya existe en task_repository.py — skip")
else:
    # Insertar antes del método DELETE
    OLD_DELETE_SECTION = "    # ─────────────────────────────────────────────\n    # DELETE"
    # fallback con los caracteres originales del archivo
    if OLD_DELETE_SECTION not in repo_src:
        # buscar el bloque delete por el decorator pattern
        OLD_DELETE_SECTION = "    async def delete_task"

    assert OLD_DELETE_SECTION in repo_src, "ERROR: no se encontró punto de inserción en task_repository.py"
    repo_src = repo_src.replace(OLD_DELETE_SECTION, UPDATE_STATUS_METHOD + "\n    " + OLD_DELETE_SECTION.lstrip(), 1)

    with open(repo_path, "w", encoding="utf-8") as f:
        f.write(repo_src)
    print("✅ task_repository.py — update_task_status agregado")

# ── ARCHIVO 3: tasks.py (router) ────────────────────────────────────────────

router_path = r"C:\Users\admin\knowledge-core\hermes\app\routers\tasks.py"

with open(router_path, "r", encoding="utf-8") as f:
    router_src = f.read()

# Cambio 3a: agregar TaskStatusUpdate al import de schemas
OLD_SCHEMA_IMPORT = "from app.schemas.task import TaskCreate, TaskRead"
NEW_SCHEMA_IMPORT = "from app.schemas.task import TaskCreate, TaskRead, TaskStatusUpdate"

if "TaskStatusUpdate" in router_src:
    print("⚠️  TaskStatusUpdate ya importado en tasks.py — skip import")
else:
    assert OLD_SCHEMA_IMPORT in router_src, "ERROR: import schemas no encontrado en tasks.py"
    router_src = router_src.replace(OLD_SCHEMA_IMPORT, NEW_SCHEMA_IMPORT)
    print("✅ tasks.py — import TaskStatusUpdate agregado")

# Cambio 3b: agregar endpoint PATCH /tasks/{task_id}/status al final
NEW_ENDPOINT = '''

# ─────────────────────────────────────────────────────────────
# PATCH /tasks/{task_id}/status
# ─────────────────────────────────────────────────────────────

@router.patch(
    "/{task_id}/status",
    response_model=TaskRead,
    summary="Actualizar status de una task",
)
async def update_task_status(
    task_id: str,
    body: TaskStatusUpdate,
    repo: TaskRepository = Depends(_get_repo),
) -> TaskRead:
    """Transiciona el status de una task. 404 si no existe, 422 si status inválido."""
    uid = _validate_uuid(task_id)
    try:
        task = await repo.update_task_status(uid, body.status.value)
    except SQLAlchemyError as exc:
        logger.error("PATCH /tasks/%s/status DB error: %s", task_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de base de datos al actualizar status.",
        )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task no encontrada: {task_id}",
        )

    logger.info("PATCH /tasks/%s/status → %s", task_id, body.status.value)
    return TaskRead.model_validate(task)
'''

if "update_task_status" in router_src:
    print("⚠️  endpoint update_task_status ya existe en tasks.py — skip")
else:
    router_src = router_src.rstrip() + NEW_ENDPOINT + "\n"
    print("✅ tasks.py — endpoint PATCH /{task_id}/status agregado")

with open(router_path, "w", encoding="utf-8") as f:
    f.write(router_src)

print("\n🎯 fix_3_3.py completado — valida con py_compile a continuación")