"""
TaskRepository — Subfase 1.6
Persistencia real PostgreSQL para tasks.
Operaciones: create, get, list, update, delete.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskStatus, TaskUpdate

logger = logging.getLogger(__name__)


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ─────────────────────────────────────────────
    # CREATE
    # ─────────────────────────────────────────────
    async def create_task(self, data: TaskCreate) -> Task:
        """Persiste una nueva task en la DB."""
        try:
            task = Task(
                id=uuid.uuid4(),
                title=data.title,
                description=data.description,
                phase=data.phase,
                payload=data.payload,
                status=TaskStatus.pending.value,
                result=None,
                error=None,
            )
            self.session.add(task)
            await self.session.flush()
            await self.session.commit()
            logger.info("Task creada: id=%s status=%s", task.id, task.status)
            return task
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error("Error al crear task: %s", exc)
            raise

    # ─────────────────────────────────────────────
    # GET
    # ─────────────────────────────────────────────
    async def get_task(self, task_id: UUID) -> Optional[Task]:
        """Retorna una task por UUID. None si no existe."""
        try:
            result = await self.session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            if task:
                logger.debug("Task encontrada: id=%s", task_id)
            else:
                logger.debug("Task no encontrada: id=%s", task_id)
            return task
        except SQLAlchemyError as exc:
            logger.error("Error al obtener task id=%s: %s", task_id, exc)
            raise

    # ─────────────────────────────────────────────
    # LIST (paginado)
    # ─────────────────────────────────────────────
    async def list_tasks(
        self,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
    ) -> tuple[list[Task], int]:
        """
        Retorna (tasks, total).
        Aplica paginación con limit/offset.
        """
        try:
            base_q = select(Task)
            if status:
                base_q = base_q.where(Task.status == status)

            count_q = select(func.count(Task.id))
            if status:
                count_q = count_q.where(Task.status == status)
            count_result = await self.session.execute(count_q)
            total = count_result.scalar_one()

            rows_result = await self.session.execute(
                base_q
                .order_by(Task.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            tasks = list(rows_result.scalars().all())
            logger.debug(
                "list_tasks: total=%d, limit=%d, offset=%d, devueltas=%d",
                total,
                limit,
                offset,
                len(tasks),
            )
            return tasks, total
        except SQLAlchemyError as exc:
            logger.error("Error al listar tasks: %s", exc)
            raise

    # ─────────────────────────────────────────────
    # UPDATE
    # ─────────────────────────────────────────────
    async def update_task(
        self, task_id: UUID, data: TaskUpdate
    ) -> Optional[Task]:
        """
        Actualiza campos no-None del payload.
        Retorna task actualizada o None si no existe.
        """
        try:
            # Construir solo los campos que vienen en el body
            values = data.model_dump(exclude_none=True)
            if "status" in values:
                values["status"] = values["status"].value
            if not values:
                logger.debug("update_task sin cambios: id=%s", task_id)
                return await self.get_task(task_id)

            await self.session.execute(
                update(Task).where(Task.id == task_id).values(**values)
            )
            await self.session.commit()

            task = await self.get_task(task_id)
            if task:
                logger.info(
                    "Task actualizada: id=%s campos=%s", task_id, list(values.keys())
                )
            return task
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error("Error al actualizar task id=%s: %s", task_id, exc)
            raise

    async def update_task_status(
        self, task_id: UUID, status: TaskStatus | str
    ) -> Optional[Task]:
        """
        Actualiza solo el estado operacional de una task.
        Retorna task actualizada o None si no existe.
        """
        status_value = status.value if isinstance(status, TaskStatus) else status
        try:
            await self.session.execute(
                update(Task).where(Task.id == task_id).values(status=status_value)
            )
            await self.session.commit()

            task = await self.get_task(task_id)
            if task:
                logger.info("Task status actualizado: id=%s status=%s", task_id, status_value)
            return task
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error("Error al actualizar status task id=%s: %s", task_id, exc)
            raise

    # ─────────────────────────────────────────────
    # RETRY
    # ─────────────────────────────────────────────
    async def retry_task(self, task_id: UUID) -> tuple[Optional[Task], str | None]:
        """
        Requeue a failed task if it has retries available.
        Returns (task, error_code). error_code is None when retry was accepted.
        """
        try:
            task = await self.get_task(task_id)
            if task is None:
                return None, "not_found"
            if task.status != TaskStatus.failed.value:
                return task, "not_failed"
            if task.retry_count >= task.max_retries:
                return task, "max_retries_reached"

            values = {
                "status": TaskStatus.pending.value,
                "retry_count": task.retry_count + 1,
                "last_retry_at": datetime.now(timezone.utc),
                "error": None,
                "result": None,
                "started_at": None,
                "completed_at": None,
            }
            await self.session.execute(
                update(Task).where(Task.id == task_id).values(**values)
            )
            await self.session.commit()
            task = await self.get_task(task_id)
            logger.info(
                "Task reintento solicitado: id=%s retry_count=%s",
                task_id,
                task.retry_count if task else None,
            )
            return task, None
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error("Error al reintentar task id=%s: %s", task_id, exc)
            raise

    # DELETE
    async def delete_task(self, task_id: UUID) -> bool:
        """
        Elimina la task. Retorna True si existía, False si no.
        """
        try:
            result = await self.session.execute(
                delete(Task).where(Task.id == task_id)
            )
            await self.session.commit()
            deleted = result.rowcount > 0
            if deleted:
                logger.info("Task eliminada: id=%s", task_id)
            else:
                logger.warning("delete_task: id=%s no encontrada", task_id)
            return deleted
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error("Error al eliminar task id=%s: %s", task_id, exc)
            raise
