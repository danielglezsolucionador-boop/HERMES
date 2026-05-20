"""
conversation.py - Subfase 3.7.3
Modelo para persistencia conversacional Telegram.
"""
from datetime import datetime, timezone
from sqlalchemy import JSON, String, Text, DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class TelegramConversation(Base):
    __tablename__ = "telegram_conversations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    message_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
