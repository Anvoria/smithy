import uuid
from datetime import datetime, UTC
from typing import Optional, Set
from enum import Enum

from sqlalchemy import (
    DateTime,
    Index,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Text,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ResourceType(str, Enum):
    """Types of resources that can have permissions"""

    SYSTEM = "SYSTEM"  # Global system permissions
    ORGANIZATION = "ORGANIZATION"  # Organization-level permissions
    PROJECT = "PROJECT"  # Project-level permissions
    TASK = "TASK"  # Task-level permissions (future)
    USER = "USER"  # User management permissions


class ActionType(str, Enum):
    """Types of actions that can be performed on resources"""

    CREATE = "CREATE"  # Create new resources
    READ = "READ"  # View/read resources
    UPDATE = "UPDATE"  # Modify existing resources
    DELETE = "DELETE"  # Remove resources
    MANAGE = "MANAGE"  # Full management (includes member management, settings)
    INVITE = "INVITE"  # Invite users to resource
    ASSIGN = "ASSIGN"  # Assign tasks/roles to users


class RoleScope(str, Enum):
    """Scope level where role can be applied"""

    SYSTEM = "SYSTEM"  # System-wide role (super admin)
    ORGANIZATION = "ORGANIZATION"  # Organization-level role
    PROJECT = "PROJECT"  # Project-level role


class Permission(Base):
    """
    Atomic permission in the system.

    Pattern: {resource_type}.{action}
    """

    name: Mapped[str] = mapped_column(
        nullable=False,
        unique=True,
        index=True,
        comment="Unique permission identifier (e.g., 'project.create')",
    )

    resource_type: Mapped[ResourceType] = mapped_column(
        nullable=False, index=True, comment="Type of resource this permission controls"
    )

    action: Mapped[ActionType] = mapped_column(
        nullable=False, index=True, comment="Action that can be performed"
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable description of what this permission allows",
    )

    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is a system-only permission",
    )

    # Relationships
    role_permissions = relationship(
        "RolePermission", back_populates="permission", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Ensure permission name matches pattern
        CheckConstraint("name ~ '^[a-z_]+\\.[a-z_]+$'", name="permission_name_format"),
        # Ensure name consistency
        CheckConstraint(
            "name = resource_type || '.' || action", name="permission_name_consistency"
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
        nullable=False, index=True, comment="Human-readable role name"
    )

    # Role identifier (e.g., "project.lead", "org.admin")
    slug: Mapped[str] = mapped_column(
        nullable=False,
        unique=True,
        index=True,
        comment="Machine-readable role identifier",
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
        nullable=True, comment="Hex color for UI display"
    )

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who created this role",
    )

    # Relationships
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
            "color IS NULL OR color ~ '^#[0-9A-Fa-f]{6}$'", name="role_color_format"
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

    def __repr__(self) -> str:
        return f"<Role(slug={self.slug}, name={self.name}, scope={self.scope})>"


class RolePermission(Base):
    """
    Many-to-many relationship between roles and permissions.
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

    # Resource context (null for system-wide roles)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID of the resource (organization/project) this role applies to",
    )

    resource_type: Mapped[ResourceType] = mapped_column(
        nullable=False, comment="Type of resource this role assignment applies to"
    )

    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        comment="When role was granted to user",
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

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    role = relationship("Role", back_populates="user_roles")
    granter = relationship("User", foreign_keys=[granted_by])

    # Database Constraints
    __table_args__ = (
        # Unique user-role-resource combination
        UniqueConstraint(
            "user_id",
            "role_id",
            "resource_id",
            "resource_type",
            name="unique_user_role_resource",
        ),
        # System roles should have resource_type = SYSTEM and resource_id = NULL
        CheckConstraint(
            "(resource_type = 'SYSTEM' AND resource_id IS NULL) OR (resource_type != 'SYSTEM' AND resource_id IS NOT NULL)",
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


# Helper function for seeding default permissions and roles
def get_default_permissions() -> list[dict]:
    """Default permissions to seed in the database"""
    return [
        # System permissions
        {
            "name": "system.admin",
            "resource_type": "SYSTEM",
            "action": "MANAGE",
            "description": "Full system administration access",
            "is_system": True,
        },
        # Organization permissions
        {
            "name": "organization.create",
            "resource_type": "ORGANIZATION",
            "action": "CREATE",
            "description": "Create new organizations",
        },
        {
            "name": "organization.read",
            "resource_type": "ORGANIZATION",
            "action": "READ",
            "description": "View organization details",
        },
        {
            "name": "organization.update",
            "resource_type": "ORGANIZATION",
            "action": "UPDATE",
            "description": "Update organization settings",
        },
        {
            "name": "organization.delete",
            "resource_type": "ORGANIZATION",
            "action": "DELETE",
            "description": "Delete organization",
        },
        {
            "name": "organization.manage",
            "resource_type": "ORGANIZATION",
            "action": "MANAGE",
            "description": "Full organization management including settings and billing",
        },
        {
            "name": "organization.invite",
            "resource_type": "ORGANIZATION",
            "action": "INVITE",
            "description": "Invite users to organization",
        },
        # Project permissions
        {
            "name": "project.create",
            "resource_type": "PROJECT",
            "action": "CREATE",
            "description": "Create new projects",
        },
        {
            "name": "project.read",
            "resource_type": "PROJECT",
            "action": "READ",
            "description": "View project details",
        },
        {
            "name": "project.update",
            "resource_type": "PROJECT",
            "action": "UPDATE",
            "description": "Update project settings",
        },
        {
            "name": "project.delete",
            "resource_type": "PROJECT",
            "action": "DELETE",
            "description": "Delete project",
        },
        {
            "name": "project.manage",
            "resource_type": "PROJECT",
            "action": "MANAGE",
            "description": "Full project management including members and settings",
        },
        {
            "name": "project.invite",
            "resource_type": "PROJECT",
            "action": "INVITE",
            "description": "Invite users to project",
        },
        # Task permissions
        {
            "name": "task.create",
            "resource_type": "TASK",
            "action": "CREATE",
            "description": "Create new tasks",
        },
        {
            "name": "task.read",
            "resource_type": "TASK",
            "action": "READ",
            "description": "View task details",
        },
        {
            "name": "task.update",
            "resource_type": "TASK",
            "action": "UPDATE",
            "description": "Update task details",
        },
        {
            "name": "task.delete",
            "resource_type": "TASK",
            "action": "DELETE",
            "description": "Delete tasks",
        },
        {
            "name": "task.assign",
            "resource_type": "TASK",
            "action": "ASSIGN",
            "description": "Assign tasks to users",
        },
        # User permissions
        {
            "name": "user.read",
            "resource_type": "USER",
            "action": "READ",
            "description": "View user profiles",
        },
        {
            "name": "user.update",
            "resource_type": "USER",
            "action": "UPDATE",
            "description": "Update user profiles",
        },
        {
            "name": "user.manage",
            "resource_type": "USER",
            "action": "MANAGE",
            "description": "Full user management including roles",
        },
    ]


def get_default_roles() -> list[dict]:
    """Default roles to seed in the database"""
    return [
        # System roles
        {
            "name": "Super Admin",
            "slug": "system.super_admin",
            "scope": "SYSTEM",
            "description": "Full system access - can do anything",
            "is_system": True,
            "color": "#dc2626",
            "permissions": ["system.admin"],
        },
        # Organization roles
        {
            "name": "Organization Owner",
            "slug": "org.owner",
            "scope": "ORGANIZATION",
            "description": "Full organization control including billing and deletion",
            "is_system": True,
            "color": "#7c3aed",
            "permissions": [
                "organization.read",
                "organization.update",
                "organization.delete",
                "organization.manage",
                "organization.invite",
                "project.create",
                "project.read",
                "project.update",
                "project.delete",
                "project.manage",
                "project.invite",
                "task.create",
                "task.read",
                "task.update",
                "task.delete",
                "task.assign",
                "user.read",
                "user.manage",
            ],
        },
        {
            "name": "Organization Admin",
            "slug": "org.admin",
            "scope": "ORGANIZATION",
            "description": "Manage organization and all projects",
            "is_system": True,
            "color": "#dc2626",
            "permissions": [
                "organization.read",
                "organization.update",
                "organization.invite",
                "project.create",
                "project.read",
                "project.update",
                "project.delete",
                "project.manage",
                "project.invite",
                "task.create",
                "task.read",
                "task.update",
                "task.delete",
                "task.assign",
                "user.read",
                "user.manage",
            ],
        },
        {
            "name": "Organization Manager",
            "slug": "org.manager",
            "scope": "ORGANIZATION",
            "description": "Create and manage projects within organization",
            "is_system": True,
            "color": "#ea580c",
            "permissions": [
                "organization.read",
                "project.create",
                "project.read",
                "project.update",
                "project.manage",
                "project.invite",
                "task.create",
                "task.read",
                "task.update",
                "task.delete",
                "task.assign",
                "user.read",
            ],
        },
        {
            "name": "Organization Member",
            "slug": "org.member",
            "scope": "ORGANIZATION",
            "description": "Basic organization member - can create projects",
            "is_system": True,
            "color": "#0891b2",
            "permissions": [
                "organization.read",
                "project.create",
                "project.read",
                "task.create",
                "task.read",
                "task.update",
                "task.assign",
                "user.read",
            ],
        },
        {
            "name": "Organization Viewer",
            "slug": "org.viewer",
            "scope": "ORGANIZATION",
            "description": "Read-only access to organization and public projects",
            "is_system": True,
            "color": "#6b7280",
            "permissions": [
                "organization.read",
                "project.read",
                "task.read",
                "user.read",
            ],
        },
        # Project roles
        {
            "name": "Project Lead",
            "slug": "project.lead",
            "scope": "PROJECT",
            "description": "Full project control - can manage all aspects",
            "is_system": True,
            "color": "#7c3aed",
            "permissions": [
                "project.read",
                "project.update",
                "project.delete",
                "project.manage",
                "project.invite",
                "task.create",
                "task.read",
                "task.update",
                "task.delete",
                "task.assign",
                "user.read",
            ],
        },
        {
            "name": "Project Maintainer",
            "slug": "project.maintainer",
            "scope": "PROJECT",
            "description": "Manage project settings and all tasks",
            "is_system": True,
            "color": "#dc2626",
            "permissions": [
                "project.read",
                "project.update",
                "project.invite",
                "task.create",
                "task.read",
                "task.update",
                "task.delete",
                "task.assign",
                "user.read",
            ],
        },
        {
            "name": "Project Developer",
            "slug": "project.developer",
            "scope": "PROJECT",
            "description": "Create and manage tasks within project",
            "is_system": True,
            "color": "#0891b2",
            "permissions": [
                "project.read",
                "task.create",
                "task.read",
                "task.update",
                "task.assign",
                "user.read",
            ],
        },
        {
            "name": "Project Reviewer",
            "slug": "project.reviewer",
            "scope": "PROJECT",
            "description": "Review and approve tasks",
            "is_system": True,
            "color": "#059669",
            "permissions": ["project.read", "task.read", "task.update", "user.read"],
        },
        {
            "name": "Project Viewer",
            "slug": "project.viewer",
            "scope": "PROJECT",
            "description": "Read-only access to project",
            "is_system": True,
            "color": "#6b7280",
            "permissions": ["project.read", "task.read", "user.read"],
        },
    ]
