import uuid

from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.db.client import get_db
from app.services.rbac_service import RBACService
from app.schemas.auth import AuthUser
from app.models.rbac import ResourceType
from app.core.exceptions import ForbiddenException


async def get_rbac_service(db: AsyncSession = Depends(get_db)) -> RBACService:
    """
    Dependency to get the RBAC service instance.
    :param db: Database session dependency.
    :return: An instance of RBACService.
    :raises HTTPException: If the database session is not available.
    """
    return RBACService(db)


# System-level permissions
async def require_system_admin(
    current_user: AuthUser = Depends(get_current_active_user),
    rbac: RBACService = Depends(get_rbac_service),
) -> AuthUser:
    """
    Dependency to ensure the current user has system admin permissions.
    :param current_user: The currently authenticated user.
    :param rbac: The RBAC service instance.
    :return: The current user if they have system admin permissions.
    :raises ForbiddenException: If the user does not have system admin permissions.
    """
    has_perm = await rbac.has_permission(
        user_id=uuid.UUID(current_user.id),
        permission="system.admin",
        resource_type=ResourceType.SYSTEM,
    )
    if not has_perm:
        raise ForbiddenException("System admin permissions required")
    return current_user


# Organization-level permission factories
def require_org_permission(permission: str):
    """Factory for organization permission dependencies"""

    async def permission_dependency(
        organization_id: uuid.UUID = Path(..., description="Organization ID"),
        current_user: AuthUser = Depends(get_current_active_user),
        rbac: RBACService = Depends(get_rbac_service),
    ) -> AuthUser:
        """
        Dependency to check if the current user has a specific permission
        for the given organization.
        :param organization_id: The ID of the organization to check permissions against.
        :param current_user: The currently authenticated user.
        :param rbac: The RBAC service instance.
        :return: The current user if they have the required permission.
        :raises ForbiddenException: If the user does not have the required permission.
        """
        has_perm = await rbac.has_permission(
            user_id=uuid.UUID(current_user.id),
            permission=permission,
            resource_id=organization_id,
            resource_type=ResourceType.ORGANIZATION,
        )
        if not has_perm:
            raise ForbiddenException(f"Missing permission: {permission}")
        return current_user

    return permission_dependency


# Project-level permission factories
def require_project_permission(permission: str):
    """Factory for project permission dependencies"""

    async def permission_dependency(
        project_id: uuid.UUID = Path(..., description="Project ID"),
        current_user: AuthUser = Depends(get_current_active_user),
        rbac: RBACService = Depends(get_rbac_service),
    ) -> AuthUser:
        """
        Dependency to check if the current user has a specific permission
        for the given project.
        :param project_id: The ID of the project to check permissions against.
        :param current_user: The currently authenticated user.
        :param rbac: The RBAC service instance.
        :return: The current user if they have the required permission.
        :raises ForbiddenException: If the user does not have the required permission.
        """
        has_perm = await rbac.has_permission(
            user_id=uuid.UUID(current_user.id),
            permission=permission,
            resource_id=project_id,
            resource_type=ResourceType.PROJECT,
        )
        if not has_perm:
            raise ForbiddenException(f"Missing permission: {permission}")
        return current_user

    return permission_dependency


# Task permissions
def require_task_permission(permission: str):
    """Factory for task permission dependencies"""

    async def permission_dependency(
        task_id: uuid.UUID = Path(..., description="Task ID"),
        current_user: AuthUser = Depends(get_current_active_user),
        rbac: RBACService = Depends(get_rbac_service),
    ) -> AuthUser:
        # For tasks, we need to check project permissions since tasks belong to projects
        # This would require getting the project_id from task_id first
        has_perm = await rbac.has_permission(
            user_id=uuid.UUID(current_user.id),
            permission=permission,
            resource_id=task_id,
            resource_type=ResourceType.TASK,
        )
        if not has_perm:
            raise ForbiddenException(f"Missing permission: {permission}")
        return current_user

    return permission_dependency
