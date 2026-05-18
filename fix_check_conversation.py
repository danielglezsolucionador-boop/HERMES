import asyncio
from app.db.engine import AsyncSessionLocal
from app.repositories.conversation_repository import get_recent

async def main():
    async with AsyncSessionLocal() as session:
        rows = await get_recent(session, limit=10)
    for r in rows:
        print(f"[{r['role'].upper()}] {r['message'][:80]}")
    print(f"Total: {len(rows)}")

asyncio.run(main())