from fastapi import APIRouter
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@router.get('/health', response_model=HealthResponse, tags=['system'])
async def health_check() -> HealthResponse:
    return HealthResponse(
        status='ok',
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
    )