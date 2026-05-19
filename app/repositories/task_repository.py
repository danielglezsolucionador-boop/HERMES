"""
TaskRepository — Subfase 1.6
Persistencia real PostgreSQL para tasks.
Operaciones: create, get, list, update, delete.
"""

import logging
import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate

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
                name=data.name or "task",
                payload=data.payload,
                status="pending",
                result=None,
                error=None,
            )
            self.session.add(task)
            await self.session.commit()
            await self.session.refresh(task)
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

    # ─────────────────────────────────────────────
    # DELETE
    # ─────────────────────────────────────────────
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
