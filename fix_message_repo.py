content = '''"""
MessageRepository — Subfase 2.5
Persistencia real de conversación en PostgreSQL.
"""

import logging
import uuid
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message

logger = logging.getLogger(__name__)


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_message(self, role: str, content: str, chat_id: int) -> Message:
        """Persiste un mensaje en la DB."""
        try:
            msg = Message(
                id=uuid.uuid4(),
                role=role,
                content=content,
                chat_id=chat_id,
            )
            self.session.add(msg)
            await self.session.commit()
            await self.session.refresh(msg)
            logger.info("Message guardado: role=%s chat_id=%s", role, chat_id)
            return msg
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error("Error guardando message: %s", exc)
            raise

    async def get_recent_messages(self, chat_id: int, limit: int = 20) -> list[Message]:
        """Retorna los ultimos N mensajes de un chat ordenados por created_at asc."""
        try:
            result = await self.session.execute(
                select(Message)
                .where(Message.chat_id == chat_id)
                .order_by(Message.created_at.asc())
                .limit(limit)
            )
            messages = list(result.scalars().all())
            logger.debug(
                "get_recent_messages: chat_id=%s limit=%s devueltos=%s",
                chat_id, limit, len(messages)
            )
            return messages
        except SQLAlchemyError as exc:
            logger.error("Error obteniendo messages: %s", exc)
            raise
'''

open('app/repositories/message_repository.py', 'w', encoding='utf-8').write(content)
print('OK - app/repositories/message_repository.py creado')