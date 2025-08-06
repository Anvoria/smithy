import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import settings
from app.db.client import get_db
from app.models.user import UserRole
from app.schemas.auth import AuthUser
from app.schemas.responses import DataResponse
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/storage", tags=["Storage"])


@router.get("/stats", response_model=DataResponse[Optional[dict]])
async def get_storage_stats(
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[Optional[dict]]:
    """
    Get storage statistics.
    This endpoint provides information about the storage usage, including total space,
    """
    storage_service = StorageService(db)

    try:
        provider_stats = storage_service.storage_provider.get_storage_stats()

        is_admin = current_user.role == UserRole.ADMIN

        if is_admin:
            stats = {
                "provider": provider_stats,
            }
        else:
            stats = {
                "provider": {
                    "storage_type": settings.STORAGE_PROVIDER,
                    "available_space": provider_stats.get("available_space", 0),
                }
            }

        return DataResponse(
            message="Storage statistics retrieved successfully",
            data=stats,
        )
    except Exception as e:
        logger.error(f"Error retrieving storage stats: {str(e)}")
        return DataResponse(
            message="Failed to retrieve storage statistics", data=None, status_code=500
        )
