from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.api import api_router
from app.core.config import settings
from app.core.logging import logger
from app.db.engine import engine
from app.telegram.polling import start_polling, stop_polling

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("HERMES starting up")
    logger.info(f"  env     : {settings.APP_ENV}")
    logger.info(f"  version : {settings.APP_VERSION}")
    logger.info(f"  debug   : {settings.DEBUG}")
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("  database : connected")
    except Exception as e:
        logger.warning(f"  database : disconnected - {e}")
    import asyncio
    asyncio.ensure_future(start_polling())
    logger.info("  telegram : polling started")
    yield
    await stop_polling()
    logger.info("HERMES shutting down - goodbye.")

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME.capitalize(),
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app

app = create_app()
