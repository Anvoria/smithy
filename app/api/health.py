from typing import Dict, Any

from fastapi import APIRouter
from app.core.config import settings, startup_time
import psutil
from datetime import datetime, UTC
from time import time

router = APIRouter(prefix="/health", tags=["Health"])


def calculate_uptime() -> Dict[str, Any]:
    """
    Calculate the uptime of the application since startup.
    """
    uptime_seconds = time() - startup_time
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)

    return {
        "uptime_seconds": round(uptime_seconds, 2),
        "uptime_formatted": f"{hours}h {minutes}m {seconds}s",
    }


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
        **calculate_uptime(),
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
        **calculate_uptime(),
    }
