import asyncio
from sqlalchemy import text
from app.db.engine import engine

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS telegram_conversations (
    id BIGSERIAL PRIMARY KEY,
    role VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
"""

async def main():
    async with engine.begin() as conn:
        await conn.execute(text(CREATE_SQL))
    print("OK - tabla telegram_conversations creada")

asyncio.run(main())