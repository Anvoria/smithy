import uuid
from datetime import datetime, UTC
from typing import Optional
from enum import Enum

from sqlalchemy import DateTime, Index, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrganizationRole(str, Enum):
    """Member roles within an organization"""

    OWNER = "owner"  # Full control, billing access
    ADMIN = "admin"  # Manage members, projects, settings
    MANAGER = "manager"  # Manage projects and team members
    MEMBER = "member"  # Create and manage own projects
    VIEWER = "viewer"  # Read-only access
    GUEST = "guest"  # Limited temporary access


class MemberStatus(str, Enum):
    """Member status within organization"""

    ACTIVE = "active"
    PENDING = "pending"  # Invited but not accepted
    SUSPENDED = "suspended"  # Temporarily disabled
    LEFT = "left"  # Member left organization


class OrganizationMember(Base):
    """
    Junction table for User-Organization membership with roles.
    Handles the many-to-many relationship with additional metadata.
    """

    # Foreign Keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User ID",
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        comment="Organization ID",
    )

    # Role and Status
    role: Mapped[OrganizationRole] = mapped_column(
        default=OrganizationRole.MEMBER,
        nullable=False,
        index=True,
        comment="Member role within organization",
    )

    status: Mapped[MemberStatus] = mapped_column(
        default=MemberStatus.PENDING,
        nullable=False,
        index=True,
        comment="Member status",
    )

    # Metadata
    invited_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who invited this member",
    )

    invited_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=True,
        comment="Invitation timestamp",
    )

    joined_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When member accepted invitation",
    )

    last_active_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last activity in organization"
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization", back_populates="members")
    inviter = relationship("User", foreign_keys=[invited_by])

    # Database Constraints
    __table_args__ = (
        # Composite primary key
        UniqueConstraint("user_id", "organization_id", name="unique_user_org"),
        # Indexes
        Index("idx_org_member_role", "organization_id", "role"),
        Index("idx_org_member_status", "organization_id", "status"),
        Index("idx_user_orgs_active", "user_id", "status"),
    )

    # Properties
    @property
    def is_active(self) -> bool:
        """Check if member is active in organization"""
        return self.status == MemberStatus.ACTIVE

    @property
    def is_pending(self) -> bool:
        """Check if member invitation is pending"""
        return self.status == MemberStatus.PENDING

    @property
    def can_manage_members(self) -> bool:
        """Check if member can manage other members"""
        return self.role in [OrganizationRole.OWNER, OrganizationRole.ADMIN]

    @property
    def can_manage_projects(self) -> bool:
        """Check if member can manage projects"""
        return self.role in [
            OrganizationRole.OWNER,
            OrganizationRole.ADMIN,
            OrganizationRole.MANAGER,
        ]

    @property
    def can_create_projects(self) -> bool:
        """Check if member can create projects"""
        return self.role in [
            OrganizationRole.OWNER,
            OrganizationRole.ADMIN,
            OrganizationRole.MANAGER,
            OrganizationRole.MEMBER,
        ]

    def has_permission(self, permission: str) -> bool:
        """Check if member has specific permission"""
        role_permissions = {
            OrganizationRole.OWNER: ["*"],  # All permissions
            OrganizationRole.ADMIN: [
                "manage_members",
                "manage_projects",
                "manage_settings",
                "create_projects",
                "view_analytics",
                "manage_billing",
            ],
            OrganizationRole.MANAGER: [
                "manage_projects",
                "create_projects",
                "view_analytics",
            ],
            OrganizationRole.MEMBER: ["create_projects", "view_projects"],
            OrganizationRole.VIEWER: ["view_projects"],
            OrganizationRole.GUEST: ["view_assigned_projects"],
        }

        permissions = role_permissions.get(self.role, [])
        return "*" in permissions or permission in permissions

    def __repr__(self) -> str:
        return f"<OrganizationMember(user_id={self.user_id}, org_id={self.organization_id}, role={self.role})>"
