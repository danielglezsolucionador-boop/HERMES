import asyncio
from app.db.engine import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as s:
        r = await s.execute(text('SELECT count(*) FROM tasks'))
        print('Tasks en DB:', r.scalar())

asyncio.run(check())