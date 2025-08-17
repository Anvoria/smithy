from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Text,
    Integer,
    Index,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrganizationType(str, Enum):
    """Organization type categories"""

    STARTUP = "startup"
    SMALL_BUSINESS = "small_business"
    ENTERPRISE = "enterprise"
    NON_PROFIT = "non_profit"
    FREELANCER = "freelancer"
    AGENCY = "agency"
    PERSONAL = "personal"


class OrganizationSize(str, Enum):
    """Organization size categories"""

    SOLO = "solo"  # 1 person
    SMALL = "small"  # 2-10 people
    MEDIUM = "medium"  # 11-50 people
    LARGE = "large"  # 51-200 people
    ENTERPRISE = "enterprise"  # 200+ people


class Organization(Base):
    """
    Organization model - central entity for multi-tenancy.
    """

    # Basic Information
    name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="Organization name"
    )

    slug: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-friendly organization identifier",
    )

    display_name: Mapped[Optional[str]] = mapped_column(
        String(250),
        nullable=True,
        comment="Public display name (can be different from name)",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Organization description"
    )

    # Visual Branding
    logo_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Organization logo URL"
    )

    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Organization avatar URL"
    )

    banner_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Organization banner/cover URL"
    )

    brand_color: Mapped[Optional[str]] = mapped_column(
        String(7),  # #RRGGBB
        nullable=True,
        comment="Primary brand color (hex)",
    )

    # Contact
    website_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Organization website"
    )

    contact_email: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Contact email address"
    )

    timezone: Mapped[Optional[str]] = mapped_column(
        String(50), default="UTC", nullable=True, comment="Organization timezone"
    )

    # Organization Classification
    org_type: Mapped[OrganizationType] = mapped_column(
        default=OrganizationType.STARTUP,
        nullable=False,
        index=True,
        comment="Organization type",
    )

    company_size: Mapped[OrganizationSize] = mapped_column(
        default=OrganizationSize.SMALL,
        nullable=False,
        index=True,
        comment="Size category of organization",
    )

    # Settings & Features
    public_projects: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Allow public projects visible to non-members",
    )

    require_email_verification: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Require email verification for new members",
    )

    allow_guest_access: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Allow temporary guest access to projects",
    )

    # Limits & Quotas
    max_members: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False, comment="Maximum number of members"
    )

    max_projects: Mapped[int] = mapped_column(
        Integer, default=5, nullable=False, comment="Maximum number of projects"
    )

    max_storage_gb: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, comment="Maximum storage in GB"
    )

    # Status & Lifecycle
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Organization active status"
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Soft deletion timestamp",
    )

    # Relationships
    user_roles = relationship(
        "UserRole",
        primaryjoin="and_(Organization.id == foreign(UserRole.resource_id), UserRole.resource_type == 'organization')",
        cascade="all, delete-orphan",
        viewonly=True,
    )

    projects = relationship(
        "Project", back_populates="organization", cascade="all, delete-orphan"
    )

    # Database Constraints
    __table_args__ = (
        # Indexes for performance
        Index("idx_org_slug_active", "slug", "deleted_at"),
        Index("idx_org_type_size", "org_type", "company_size"),
        # Check constraints
        CheckConstraint(
            "LENGTH(slug) >= 2 AND LENGTH(slug) <= 50", name="org_slug_length"
        ),
        CheckConstraint("slug ~ '^[a-z0-9-]+$'", name="org_slug_format"),
        CheckConstraint(
            "brand_color IS NULL OR brand_color ~ '^#[0-9A-Fa-f]{6}$'",
            name="valid_brand_color",
        ),
        CheckConstraint("max_members > 0", name="positive_max_members"),
        CheckConstraint("max_projects > 0", name="positive_max_projects"),
        CheckConstraint("max_storage_gb > 0", name="positive_max_storage"),
        # Unique constraints
        UniqueConstraint("slug", name="unique_org_slug"),
    )

    @property
    def current_members(self) -> int:
        """Count active members using RBAC"""
        return len([r for r in self.user_roles if r.is_active])

    @property
    def current_projects(self) -> int:
        """Count active projects"""
        return len([p for p in self.projects if not p.deleted_at])

    # TODO: Implement storage calculation based on actual project data
    # https://github.com/Anvoria/smithy/issues/5
    @property
    def storage_used_mb(self) -> int:
        return 0

    @property
    def usage_stats(self) -> dict:
        """Get usage statistics as percentage"""
        return {
            "members": (self.current_members / self.max_members) * 100
            if self.max_members > 0
            else 0,
            "projects": (self.current_projects / self.max_projects) * 100
            if self.max_projects > 0
            else 0,
            "storage": (self.storage_used_mb / (self.max_storage_gb * 1024)) * 100
            if self.max_storage_gb > 0
            else 0,
        }

    def __repr__(self) -> str:
        return f"<Organization(slug={self.slug}, name={self.name})>"
