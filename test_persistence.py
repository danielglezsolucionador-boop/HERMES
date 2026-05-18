import asyncio
from app.db.engine import AsyncSessionLocal
from app.repositories.message_repository import MessageRepository
from app.core.config import settings

async def main():
    async with AsyncSessionLocal() as session:
        repo = MessageRepository(session)
        messages = await repo.get_recent_messages(
            chat_id=settings.TELEGRAM_CHAT_ID,
            limit=10
        )
        print(f"\nTotal mensajes encontrados: {len(messages)}")
        print("-" * 50)
        for msg in messages:
            print(f"[{msg.created_at}] {msg.role.upper()}: {msg.content}")
        print("-" * 50)

asyncio.run(main())