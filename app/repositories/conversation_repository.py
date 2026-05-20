"""
conversation_repository.py - Subfase 3.7.3
Persistencia conversacional minima.
"""
import logging
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import TelegramConversation

logger = logging.getLogger(__name__)

CONVERSATION_LIMIT = 10
_METADATA_COLUMN_READY = False


def _message_metadata(role: str, message: str, metadata: dict | None) -> dict:
    data = {
        "source": "telegram",
        "role": role,
        "message_chars": len(message or ""),
    }
    if metadata:
        data.update(metadata)
    return data


async def ensure_metadata_column(db: AsyncSession) -> None:
    """Ensure local PostgreSQL can persist conversation metadata."""
    global _METADATA_COLUMN_READY
    if _METADATA_COLUMN_READY:
        return
    await db.execute(
        text("ALTER TABLE telegram_conversations ADD COLUMN IF NOT EXISTS metadata JSONB")
    )
    await db.commit()
    _METADATA_COLUMN_READY = True


async def save_message(
    db: AsyncSession,
    role: str,
    message: str,
    metadata: dict | None = None,
) -> None:
    """Persiste un mensaje de la conversacion."""
    await ensure_metadata_column(db)
    entry = TelegramConversation(
        role=role,
        message=message,
        message_metadata=_message_metadata(role, message, metadata),
    )
    db.add(entry)
    await db.commit()
    logger.debug("conversation: saved role=%s chars=%d", role, len(message))


async def get_recent(db: AsyncSession, limit: int = CONVERSATION_LIMIT) -> list[dict]:
    """Retorna los ultimos N mensajes ordenados cronologicamente."""
    await ensure_metadata_column(db)
    result = await db.execute(
        select(TelegramConversation)
        .order_by(TelegramConversation.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    rows = list(reversed(rows))
    return [
        {
            "role": r.role,
            "message": r.message,
            "created_at": r.created_at.isoformat(),
            "metadata": r.message_metadata or {},
        }
        for r in rows
    ]
