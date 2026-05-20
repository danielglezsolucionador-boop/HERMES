"""
Tasks Router
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskRead, TaskStatus, TaskStatusUpdate, TaskUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _validate_uuid(raw: str) -> UUID:
    try:
        return UUID(raw)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"UUID inválido: '{raw}'",
        )


def _get_repo(session: AsyncSession = Depends(get_session)) -> TaskRepository:
    return TaskRepository(session)


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(body: TaskCreate, repo: TaskRepository = Depends(_get_repo)):
    try:
        task = await repo.create_task(body)
        logger.info("POST /tasks task_id=%s", task.id)
        return task
    except SQLAlchemyError as exc:
        logger.error("POST /tasks DB error: %s", exc)
        raise HTTPException(status_code=500, detail="Error de base de datos al crear la task.")


@router.get("", response_model=list[TaskRead])
async def list_tasks(
    status: TaskStatus | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    repo: TaskRepository = Depends(_get_repo),
):
    try:
        status_value = status.value if status else None
        tasks, total = await repo.list_tasks(limit=limit, offset=offset, status=status_value)
        return tasks
    except SQLAlchemyError as exc:
        logger.error("GET /tasks DB error: %s", exc)
        raise HTTPException(status_code=500, detail="Error de base de datos al listar tasks.")


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: str, repo: TaskRepository = Depends(_get_repo)):
    uid = _validate_uuid(task_id)
    try:
        task = await repo.get_task(uid)
    except SQLAlchemyError as exc:
        logger.error("GET /tasks/%s DB error: %s", task_id, exc)
        raise HTTPException(status_code=500, detail="Error de base de datos al obtener la task.")
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task no encontrada: {task_id}")
    return task


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(task_id: str, body: TaskUpdate, repo: TaskRepository = Depends(_get_repo)):
    uid = _validate_uuid(task_id)
    try:
        task = await repo.update_task(uid, body)
    except SQLAlchemyError as exc:
        logger.error("PATCH /tasks/%s DB error: %s", task_id, exc)
        raise HTTPException(status_code=500, detail="Error de base de datos al actualizar la task.")
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task no encontrada: {task_id}")
    return task


@router.patch("/{task_id}/status", response_model=TaskRead)
async def update_task_status(
    task_id: str,
    body: TaskStatusUpdate,
    repo: TaskRepository = Depends(_get_repo),
):
    uid = _validate_uuid(task_id)
    try:
        task = await repo.update_task_status(uid, body.status)
    except SQLAlchemyError as exc:
        logger.error("PATCH /tasks/%s/status DB error: %s", task_id, exc)
        raise HTTPException(status_code=500, detail="Error de base de datos al actualizar status.")
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task no encontrada: {task_id}")
    return task


@router.patch("/{task_id}/retry", response_model=TaskRead)
async def retry_task(task_id: str, repo: TaskRepository = Depends(_get_repo)):
    uid = _validate_uuid(task_id)
    try:
        task, error = await repo.retry_task(uid)
    except SQLAlchemyError as exc:
        logger.error("PATCH /tasks/%s/retry DB error: %s", task_id, exc)
        raise HTTPException(status_code=500, detail="Error de base de datos al reintentar task.")

    if task is None:
        raise HTTPException(status_code=404, detail=f"Task no encontrada: {task_id}")
    if error == "not_failed":
        raise HTTPException(status_code=409, detail="Solo se pueden reintentar tasks failed.")
    if error == "max_retries_reached":
        raise HTTPException(status_code=409, detail="Task alcanzo max_retries.")
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, repo: TaskRepository = Depends(_get_repo)):
    uid = _validate_uuid(task_id)
    try:
        deleted = await repo.delete_task(uid)
    except SQLAlchemyError as exc:
        logger.error("DELETE /tasks/%s DB error: %s", task_id, exc)
        raise HTTPException(status_code=500, detail="Error de base de datos al eliminar la task.")
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Task no encontrada: {task_id}")
