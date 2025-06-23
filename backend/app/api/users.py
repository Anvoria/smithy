import logging
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.client import get_db
from app.schemas.responses import MessageResponse, DataResponse
from app.schemas.user import (
    UserUpdate,
    UserPasswordUpdate,
    UserEmailUpdate,
    UserRoleUpdate,
    UserStatusUpdate,
    UserProfile,
    UserAdmin,
    UserListAdmin,
    UserStats,
)
from app.schemas.auth import AuthUser
from app.services.user_service import UserService
from app.core.auth import get_current_user, require_moderator_or_admin, require_admin
from app.models.user import UserStatus, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=DataResponse[UserProfile])
async def get_my_profile(
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[UserProfile]:
    """
    Get the profile of the currently authenticated user.
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_id(UUID(current_user.id))
    return DataResponse(
        message="User profile retrieved successfully",
        data=UserProfile.model_validate(user),
    )


@router.put("/me", response_model=DataResponse[UserProfile])
async def update_my_profile(
    update_data: UserUpdate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[UserProfile]:
    """
    Update the profile of the currently authenticated user.
    """
    user_service = UserService(db)
    user = await user_service.update_user_profile(UUID(current_user.id), update_data)
    return DataResponse(
        message="User profile updated successfully",
        data=UserProfile.model_validate(user),
    )


@router.post("/me/change-password")
async def change_my_password(
    password_data: UserPasswordUpdate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """
    Change current user's password
    """
    user_service = UserService(db)
    success = await user_service.change_user_password(
        UUID(current_user.id), password_data
    )
    return MessageResponse(
        "Password changed successfully" if success else "Failed to change password"
    )


@router.post("/me/change-email", response_model=DataResponse[UserProfile])
async def change_my_email(
    email_data: UserEmailUpdate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[UserProfile]:
    """
    Change the email address of the currently authenticated user.
    """
    user_service = UserService(db)
    user = await user_service.change_user_email(UUID(current_user.id), email_data)
    return DataResponse(
        message="Email address updated successfully",
        data=UserProfile.model_validate(user),
    )


@router.get("/", response_model=DataResponse[UserListAdmin])
async def get_users_list(
    admin_user: Annotated[AuthUser, Depends(require_moderator_or_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search term"),
    user_status: Optional[UserStatus] = Query(None, description="Filter by status"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    is_verified: Optional[bool] = Query(
        None, description="Filter by verification status"
    ),
) -> DataResponse[UserListAdmin]:
    """
    Get a paginated list of users with optional filters.
    """
    user_service = UserService(db)
    users, total = await user_service.get_users_list(
        page=page,
        size=size,
        search=search,
        status=user_status,
        role=role,
        is_verified=is_verified,
    )

    pages = (total + size - 1) // size

    return DataResponse(
        message="Users list retrieved successfully",
        data=UserListAdmin(
            users=[UserAdmin.model_validate(user) for user in users],
            total=total,
            page=page,
            size=size,
            pages=pages,
        ),
    )


@router.get("/stats", response_model=DataResponse[UserStats])
async def get_user_stats(
    admin_user: Annotated[AuthUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[UserStats]:
    """
    Get user statistics for the admin dashboard.
    """
    user_service = UserService(db)
    return DataResponse(
        message="User statistics retrieved successfully",
        data=await user_service.get_user_stats(),
    )


@router.get("/{user_id}", response_model=DataResponse[UserAdmin])
async def get_user_by_id(
    user_id: UUID,
    admin_user: Annotated[AuthUser, Depends(require_moderator_or_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[UserAdmin]:
    """
    Get user details by user ID.
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    return DataResponse(
        message="User details retrieved successfully",
        data=UserAdmin.model_validate(user),
    )


@router.put("/{user_id}/role", response_model=DataResponse[UserAdmin])
async def update_user_role(
    user_id: UUID,
    role_data: UserRoleUpdate,
    admin_user: Annotated[AuthUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[UserAdmin]:
    """
    Update the role of a user by user ID.
    """
    user_service = UserService(db)
    user = await user_service.update_user_role(user_id, role_data, UUID(admin_user.id))
    return DataResponse(
        message="User role updated successfully", data=UserAdmin.model_validate(user)
    )


@router.put("/{user_id}/status", response_model=DataResponse[UserAdmin])
async def update_user_status(
    user_id: UUID,
    status_data: UserStatusUpdate,
    admin_user: Annotated[AuthUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[UserAdmin]:
    """
    Update the status of a user by user ID.
    """
    user_service = UserService(db)
    user = await user_service.update_user_status(
        user_id, status_data, UUID(admin_user.id)
    )
    return DataResponse(
        message="User status updated successfully", data=UserAdmin.model_validate(user)
    )


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: UUID,
    admin_user: Annotated[AuthUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """
    Soft delete a user by user ID.
    """
    user_service = UserService(db)
    success = await user_service.soft_delete_user(user_id, UUID(admin_user.id))
    return MessageResponse(
        "User deleted successfully" if success else "Failed to delete user"
    )


@router.post("/{user_id}/restore", response_model=DataResponse[UserAdmin])
async def restore_user(
    user_id: UUID,
    admin_user: Annotated[AuthUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[UserAdmin]:
    """
    Restore a soft-deleted user by user ID.
    """
    user_service = UserService(db)
    user = await user_service.restore_user(user_id, UUID(admin_user.id))
    return DataResponse(
        message="User restored successfully", data=UserAdmin.model_validate(user)
    )
