from fastapi import APIRouter
from app.core.config import settings
import psutil
from datetime import datetime, UTC

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", tags=["Health"])
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": settings.ENVIRONMENT,
    }


@router.get("/details", tags=["Health"])
async def health_check_details():
    """
    Detailed health check endpoint
    """
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()

    return {
        "status": "healthy",
        "version": settings.VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": settings.ENVIRONMENT,
        "cpu_usage": cpu_usage,
        "memory_total": memory_info.total,
        "memory_used": memory_info.used,
        "memory_free": memory_info.free,
        "memory_percent": memory_info.percent,
    }
