import uuid
from typing import Set, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, distinct

from app.models.rbac import (
    Permission,
    Role,
    RolePermission,
    UserRole,
    ResourceType,
)
import logging

logger = logging.getLogger(__name__)


class RBACService:
    """Basic RBAC service for permission checking"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def has_permission(
        self,
        user_id: uuid.UUID,
        permission: str,
        resource_id: Optional[uuid.UUID] = None,
        resource_type: Optional[ResourceType] = None,
    ) -> bool:
        """
        Check if user has a specific permission.

        :param user_id: UUID of the user
        :param permission: Permission name to check (e.g., 'project.update')
        :param resource_id: Optional resource ID to check against
        :param resource_type: Optional resource type to check against
        :return: True if user has permission, False otherwise
        """
        try:
            user_permissions = await self.get_user_permissions(
                user_id, resource_id, resource_type
            )

            if permission in user_permissions:
                return True

            if "system.admin" in user_permissions:
                return True

            return False

        except Exception as e:
            logger.error(
                f"Error checking permission {permission} for user {user_id}: {e}"
            )
            return False

    async def get_user_permissions(
        self,
        user_id: uuid.UUID,
        resource_id: Optional[uuid.UUID] = None,
        resource_type: Optional[ResourceType] = None,
    ) -> Set[str]:
        """
        Get all permissions for a user in the given context.

        :param user_id: UUID of the user
        :param resource_id: Optional resource ID to filter permissions
        :param resource_type: Optional resource type to filter permissions
        """
        base_cond = and_(UserRole.user_id == user_id, UserRole.is_active)

        # Context predicates
        ctx_parts = []
        if resource_type:
            ctx_parts.append(UserRole.resource_type == resource_type.value)
        if resource_id:
            ctx_parts.append(UserRole.resource_id == resource_id)

        ctx_cond = and_(*ctx_parts) if ctx_parts else None

        system_cond = UserRole.resource_type == ResourceType.SYSTEM.value

        if resource_type == ResourceType.SYSTEM:
            final_cond = and_(base_cond, system_cond)
        elif ctx_cond is not None:
            final_cond = and_(base_cond, or_(ctx_cond, system_cond))
        else:
            final_cond = base_cond

        stmt = (
            select(distinct(Permission.name))
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                final_cond,
                Role.is_active.is_(True),
            )
        )

        result = await self.db.execute(stmt)
        return set(result.scalars().all())
