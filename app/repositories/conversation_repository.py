"""
conversation_repository.py - Subfase 3.7.3
Persistencia conversacional minima.
"""
import logging
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import TelegramConversation

logger = logging.getLogger(__name__)

CONVERSATION_LIMIT = 10


async def save_message(db: AsyncSession, role: str, message: str) -> None:
    """Persiste un mensaje de la conversacion."""
    entry = TelegramConversation(role=role, message=message)
    db.add(entry)
    await db.commit()
    logger.debug("conversation: saved role=%s chars=%d", role, len(message))


async def get_recent(db: AsyncSession, limit: int = CONVERSATION_LIMIT) -> list[dict]:
    """Retorna los ultimos N mensajes ordenados cronologicamente."""
    result = await db.execute(
        select(TelegramConversation)
        .order_by(TelegramConversation.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    rows = list(reversed(rows))
    return [
        {"role": r.role, "message": r.message, "created_at": r.created_at.isoformat()}
        for r in rows
    ]