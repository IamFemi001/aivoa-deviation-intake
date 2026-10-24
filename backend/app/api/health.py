"""Simple health check — matches deviationApi.checkHealth() on the frontend."""
from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check():
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "ai_service": "langgraph" if settings.AI_SERVICE_ENABLED else "stub",
    }
