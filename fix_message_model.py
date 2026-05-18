content = '''import uuid
from sqlalchemy import String, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
from app.models.base import TimestampMixin


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
'''

open('app/models/message.py', 'w', encoding='utf-8').write(content)
print('OK - app/models/message.py creado')