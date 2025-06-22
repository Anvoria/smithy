from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Text,
    Integer,
    JSON,
    Index,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.organization_member import MemberStatus


class OrganizationType(str, Enum):
    """Organization type categories"""

    STARTUP = "startup"
    SMALL_BUSINESS = "small_business"
    ENTERPRISE = "enterprise"
    NON_PROFIT = "non_profit"
    FREELANCER = "freelancer"
    AGENCY = "agency"
    PERSONAL = "personal"


class OrganizationStatus(str, Enum):
    """Organization status"""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class OrganizationSize(str, Enum):
    """Organization size categories"""

    SMALL = "1-10"
    MEDIUM = "11-50"
    LARGE = "51-200"
    ENTERPRISE = "201+"
    SOLO = "solo"  # For freelancers or solo entrepreneurs


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
        default=OrganizationSize.SOLO,
        nullable=False,
        index=True,
        comment="Size of the organization",
    )

    # Limits & Quotas
    max_members: Mapped[int] = mapped_column(
        Integer, default=5, nullable=False, comment="Maximum number of members allowed"
    )

    max_projects: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False, comment="Maximum number of projects allowed"
    )

    max_storage_gb: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, comment="Maximum storage in GB"
    )

    # Configuration & Settings
    settings: Mapped[Optional[dict]] = mapped_column(
        JSON, default=dict, nullable=True, comment="Organization configuration"
    )

    features: Mapped[Optional[dict]] = mapped_column(
        JSON, default=dict, nullable=True, comment="Enabled features and feature flags"
    )

    integrations: Mapped[Optional[dict]] = mapped_column(
        JSON, default=dict, nullable=True, comment="External integrations configuration"
    )

    # Security
    require_2fa: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Require 2FA for all members"
    )

    public_projects: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Allow public project visibility",
    )

    # Soft Delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Soft deletion timestamp",
    )

    # Relationships
    members = relationship(
        "OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
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
        """Count active members"""
        return len([m for m in self.members if m.status == MemberStatus.ACTIVE])

    @property
    def current_projects(self) -> int:
        """Count active projects"""
        return len([p for p in self.projects if not p.deleted_at])

    # TODO: Implement storage calculation based on actual project data
    # https://github.com/Anvoria/smithy-backend/issues/5
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

    @property
    def is_over_limits(self) -> dict:
        """Check if organization is over any limits"""
        return {
            "members": self.current_members >= self.max_members,
            "projects": self.current_projects >= self.max_projects,
            "storage": self.storage_used_mb >= (self.max_storage_gb * 1024),
        }

    @property
    def public_url(self) -> str:
        """Get public organization URL"""
        return f"/org/{self.slug}"

    @property
    def display_avatar(self) -> Optional[str]:
        """Get display avatar with fallbacks"""
        return self.avatar_url or self.logo_url

    def can_add_member(self) -> bool:
        """Check if organization can add more members"""
        return self.current_members < self.max_members

    def can_create_project(self) -> bool:
        """Check if organization can create more projects"""
        return self.current_projects < self.max_projects

    def has_feature(self, feature_name: str) -> bool:
        """Check if organization has specific feature enabled"""
        if not self.features:
            return False
        return self.features.get(feature_name, False)

    def get_setting(self, setting_name: str, default=None):
        """Get organization setting with default fallback"""
        if not self.settings:
            return default
        return self.settings.get(setting_name, default)

    def __repr__(self) -> str:
        return f"<Organization(slug={self.slug}, name={self.name})>"
