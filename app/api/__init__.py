from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.status import router as status_router
from app.api.runtime import router as runtime_router
from app.routers.tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(status_router)
api_router.include_router(runtime_router)
api_router.include_router(tasks_router)