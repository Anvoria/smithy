import uuid
from datetime import datetime, UTC
from enum import Enum
from typing import Optional, Set

from sqlalchemy import (
    Text,
    Boolean,
    CheckConstraint,
    Index,
    ForeignKey,
    UniqueConstraint,
    DateTime,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ResourceType(str, Enum):
    """Types of resource that can have permissions"""

    SYSTEM = "system"  # Global system permissions
    ORGANIZATION = "organization"  # Organization-level permissions
    PROJECT = "project"  # Project-level permissions
    TASK = "task"  # Task-level permissions
    USER = "user"  # User-level permissions


class ActionType(str, Enum):
    """Types of actions that can be performed on resources"""

    CREATE = "create"  # Create new resource
    READ = "read"  # Read/view resource
    UPDATE = "update"  # Update existing resource
    DELETE = "delete"  # Delete resource
    MANAGE = "manage"  # Manage resource (member management, settings)
    INVITE = "invite"  # Invite users to resource
    ASSIGN = "assign"  # Assign roles or permissions


class RoleScope(str, Enum):
    """Scope level where role can be applied"""

    SYSTEM = "system"  # System-wide role (super-admin)
    ORGANIZATION = "organization"  # Organization-level role
    PROJECT = "project"  # Project-level role


class Permission(Base):
    """
    Atomic permission in the system.

    Pattern: {resource_type}.{action}
    """

    name: Mapped[str] = mapped_column(
        nullable=False, unique=True, index=True, comment="Unique permission identifier"
    )

    resource_type: Mapped[ResourceType] = mapped_column(
        nullable=False, index=True, comment="Type of resource this permission controls"
    )

    action: Mapped[ActionType] = mapped_column(
        nullable=False, index=True, comment="Action that can be performed"
    )

    description: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Description of what this permission allows"
    )

    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is a system-only permission",
    )

    role_permissions = relationship(
        "RolePermission", back_populates="permission", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Ensure permission name matches pattern
        CheckConstraint("name ~ '^[a-z_]+\\.[a-z_]+$'", name="permission_name_format"),
        # Ensure name consistency
        CheckConstraint(
            "name = resource_type || '.' || action",
            name="permission_name_consistency",
        ),
        # Indexes
        Index("idx_permission_resource_action", "resource_type", "action"),
        Index("idx_permission_system", "is_system"),
    )

    def __repr__(self) -> str:
        return f"<Permission(name={self.name}, resource={self.resource_type}, action={self.action})>"


class Role(Base):
    """
    Role that groups permissions together.
    """

    name: Mapped[str] = mapped_column(
        nullable=False, index=True, comment="Readable role name"
    )

    # Role identifier (e.g., "project.lead", "org.admin")
    slug: Mapped[str] = mapped_column(
        nullable=False, index=True, unique=True, comment="Role identifier"
    )

    scope: Mapped[RoleScope] = mapped_column(
        nullable=False, index=True, comment="Scope level where this role applies"
    )

    description: Mapped[str] = mapped_column(
        Text, nullable=True, comment="Description of role responsibilities"
    )

    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is a protected system role",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether this role is active and can be assigned",
    )

    color: Mapped[Optional[str]] = mapped_column(
        nullable=False, comment="Hex color for UI display"
    )

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who created this role",
    )

    role_permissions = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )
    user_roles = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )
    creator = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        # Ensure slug format
        CheckConstraint("slug ~ '^[a-z0-9_\\.]+$'", name="role_slug_format"),
        # Ensure color format if provided
        CheckConstraint(
            "color IS NULL or color ~ '^#[0-9A-Fa-f]{6}$'", name="role_color_format"
        ),
        # Unique constraint per scope
        UniqueConstraint("name", "scope", name="unique_role_name_per_scope"),
        # Indexes
        Index("idx_role_scope_active", "scope", "is_active"),
        Index("idx_role_system", "is_system"),
    )

    def get_permissions(self) -> Set[str]:
        """Get all permission names for this role"""
        return {rp.permission.name for rp in self.role_permissions}

    def __repr__(self):
        return f"<Role(slug={self.slug}, name={self.name}, scope={self.scope})>"


class RolePermission(Base):
    """
    M:M relationship between roles and permissions.
    """

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        comment="Role ID",
    )

    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
        comment="Permission ID",
    )

    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        comment="When permission was granted to role",
    )

    granted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who granted this permission to the role",
    )

    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")
    granter = relationship("User", foreign_keys=[granted_by])

    __table_args__ = (
        # Unique role-permission combination
        UniqueConstraint("role_id", "permission_id", name="unique_role_permission"),
        # Indexes
        Index("idx_role_permission_role", "role_id"),
        Index("idx_role_permission_permission", "permission_id"),
        Index("idx_role_permission_granted", "granted_at"),
    )

    def __repr__(self) -> str:
        return f"<RolePermission(role_id={self.role_id}, permission_id={self.permission_id})>"


class UserRole(Base):
    """
    Assignment of roles to users within specific resource contexts.
    """

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User ID",
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        comment="Role ID",
    )

    # Null for system-wide roles
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID of the resource (org/project) this role applies to",
    )

    resource_type: Mapped[ResourceType] = mapped_column(
        nullable=False, comment="Type of resource this role assignment applies to"
    )

    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        comment="When roles was granted to user",
    )

    granted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who granted this role",
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this role assignment expires (null = never)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether this role assignment is currently active",
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Optional notes about this role assignment"
    )

    user = relationship("User", foreign_keys=[user_id])
    role = relationship("Role", back_populates="user_roles")
    granter = relationship("User", foreign_keys=[granted_by])

    __table_args__ = (
        # Unique user-role-resource combination
        UniqueConstraint(
            "user_id",
            "role_id",
            "resource_id",
            "resource_type",
            name="unique_user_role_resource",
        ),
        # System roles should not have resource_id
        CheckConstraint(
            "(resource_type = 'system' AND resource_id IS NULL) OR (resource_type != 'system' AND resource_id IS NOT NULL)",
            name="system_role_no_resource",
        ),
        # Expiration should be in the future when set
        CheckConstraint(
            "expires_at IS NULL OR expires_at > granted_at", name="valid_expiration"
        ),
        # Indexes
        Index("idx_user_role_user", "user_id", "is_active"),
        Index("idx_user_role_resource", "resource_type", "resource_id", "is_active"),
        Index("idx_user_role_expiration", "expires_at", "is_active"),
        Index("idx_user_role_granted", "granted_at"),
        Index("idx_user_role_active", "is_active"),
    )

    @property
    def is_expired(self) -> bool:
        """Check if this role assignment is expired"""
        if not self.expires_at:
            return False
        return datetime.now(UTC) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if this role assignment is currently valid"""
        return self.is_active and not self.is_expired

    def __repr__(self) -> str:
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id}, resource={self.resource_type}:{self.resource_id})>"
