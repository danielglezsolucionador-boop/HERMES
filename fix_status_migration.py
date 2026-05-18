import asyncio
from app.db.engine import AsyncSessionLocal
from sqlalchemy import text

async def migrate():
    async with AsyncSessionLocal() as session:
        # Ver cuántas tasks tienen status running
        r = await session.execute(
            text("SELECT count(*) FROM tasks WHERE status = 'running'")
        )
        count = r.scalar()
        print(f"Tasks con status 'running': {count}")

        # Migrar running → doing
        await session.execute(
            text("UPDATE tasks SET status = 'doing' WHERE status = 'running'")
        )
        await session.commit()
        print("OK - running → doing migrado")

        # Verificar
        r2 = await session.execute(
            text("SELECT status, count(*) FROM tasks GROUP BY status")
        )
        for row in r2:
            print(f"  {row[0]}: {row[1]}")

asyncio.run(migrate())