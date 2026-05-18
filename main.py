from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.api import api_router
from app.core.config import settings
from app.core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("HERMES starting up")
    logger.info(f"  env     : {settings.APP_ENV}")
    logger.info(f"  version : {settings.APP_VERSION}")
    logger.info(f"  debug   : {settings.DEBUG}")

    yield

    logger.info("HERMES shutting down - goodbye.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME.capitalize(),
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    app.include_router(api_router)

    return app


app = create_app()