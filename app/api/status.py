import time
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from app.core.config import settings
from app.db.engine import engine

router = APIRouter()

START_TIME = time.time()


class StatusResponse(BaseModel):
    status: str
    service: str
    version: str
    env: str
    database: str
    uptime_seconds: int


class ReadyResponse(BaseModel):
    ready: bool
    checks: dict


@router.get('/status', response_model=StatusResponse, tags=['system'])
async def status_check() -> StatusResponse:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return StatusResponse(
        status="ok",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        env=settings.APP_ENV,
        database=db_status,
        uptime_seconds=int(time.time() - START_TIME),
    )


@router.get('/ready', tags=['system'])
async def ready_check():
    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    ready = db_ok
    content = ReadyResponse(ready=ready, checks={"database": db_ok})

    if ready:
        return content
    return JSONResponse(status_code=503, content=content.model_dump())