from typing import Dict, Any
from datetime import datetime, UTC
from time import time

from fastapi import APIRouter, Depends
from app.core.config import settings, startup_time
from app.core.auth import get_current_user
from app.models.user import User
from app import __version__
import psutil

router = APIRouter(prefix="/system", tags=["System"])


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


@router.get("/info", response_model=Dict[str, Any])
async def get_system_info():
    """
    Get public system information.
    This endpoint is public and does not require authentication.
    """
    return {
        "app": {
            "name": settings.APP_NAME,
            "version": __version__,
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "docs_enabled": settings.DOCS_ENABLED,
        },
        "server": {
            "timestamp": datetime.now(UTC).isoformat(),
            **calculate_uptime(),
        },
    }


@router.get("/info/detailed", response_model=Dict[str, Any])
async def get_detailed_system_info(current_user: User = Depends(get_current_user)):
    """
    Get detailed system information (requires authentication).
    This includes sensitive information like resource usage.
    """
    basic_info = await get_system_info()

    cpu_info = psutil.cpu_percent(interval=0.1)
    memory_info = psutil.virtual_memory()
    disk_info = psutil.disk_usage("/")

    net_io = psutil.net_io_counters()

    detailed_info = {
        **basic_info,
        "resources": {
            "cpu": {
                "usage_percent": cpu_info,
                "count": psutil.cpu_count(logical=False),
                "count_logical": psutil.cpu_count(logical=True),
            },
            "memory": {
                "total": memory_info.total,
                "available": memory_info.available,
                "used": memory_info.used,
                "free": memory_info.free,
                "percent": memory_info.percent,
                "total_formatted": f"{memory_info.total / (1024**3):.2f} GB",
                "used_formatted": f"{memory_info.used / (1024**3):.2f} GB",
            },
            "disk": {
                "total": disk_info.total,
                "used": disk_info.used,
                "free": disk_info.free,
                "percent": disk_info.percent,
                "total_formatted": f"{disk_info.total / (1024**3):.2f} GB",
                "used_formatted": f"{disk_info.used / (1024**3):.2f} GB",
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "bytes_sent_formatted": f"{net_io.bytes_sent / (1024**2):.2f} MB",
                "bytes_recv_formatted": f"{net_io.bytes_recv / (1024**2):.2f} MB",
            },
        },
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "role": current_user.role.value,
        },
    }

    return detailed_info
