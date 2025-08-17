import uuid
from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Text,
    JSON,
    Index,
    CheckConstraint,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ProjectStatus(str, Enum):
    """Project status options"""

    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


class ProjectPriority(str, Enum):
    """Project priority levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProjectVisibility(str, Enum):
    """Project visibility settings"""

    PRIVATE = "private"  # Only organization members with access
    ORGANIZATION = "organization"  # All organization members
    PUBLIC = "public"  # Everyone can view (if org allows public projects)


class Project(Base):
    """
    Project model belonging to an organization.
    Designed for team collaboration and advanced project management.
    """

    # Basic Information
    name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="Project name"
    )

    key: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
        index=True,
        comment="Project key (e.g., PANEL, DASH) - max 6 chars, used for task IDs",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Project description"
    )

    # Organization Relationship
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Organization that owns this project",
    )

    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Project lead/manager (must be org member)",
    )

    # Visual & Branding
    icon: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Project icon (emoji, icon name, or URL)"
    )

    color: Mapped[Optional[str]] = mapped_column(
        String(7),  # #RRGGBB
        nullable=True,
        comment="Project color theme (hex color)",
    )

    cover_image_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Project cover image URL"
    )

    # Status & Priority
    status: Mapped[ProjectStatus] = mapped_column(
        default=ProjectStatus.PLANNING,
        nullable=False,
        index=True,
        comment="Current project status",
    )

    priority: Mapped[ProjectPriority] = mapped_column(
        default=ProjectPriority.MEDIUM,
        nullable=False,
        index=True,
        comment="Project priority level",
    )

    visibility: Mapped[ProjectVisibility] = mapped_column(
        default=ProjectVisibility.ORGANIZATION,
        nullable=False,
        index=True,
        comment="Project visibility settings",
    )

    # Dates
    start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Project start date"
    )

    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Project due date"
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Project completion timestamp"
    )

    enable_subtasks: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Enable subtask creation"
    )

    # Project Configuration & Settings
    settings: Mapped[Optional[dict]] = mapped_column(
        JSON, default=dict, nullable=True, comment="Project configuration and settings"
    )

    # Archival & Soft Delete
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Project archival timestamp",
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Soft deletion timestamp",
    )

    # Relationships
    organization = relationship("Organization", back_populates="projects")
    lead = relationship("User", foreign_keys=[lead_id])

    tasks = relationship(
        "Task",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Task.task_number",
    )

    # Project members
    user_roles = relationship(
        "UserRole",
        primaryjoin="and_(Project.id == foreign(UserRole.resource_id), UserRole.resource_type == 'project')",
        cascade="all, delete-orphan",
        viewonly=True,
    )

    # Database Constraints
    __table_args__ = (
        # Unique project key per organization
        UniqueConstraint("organization_id", "key", name="unique_project_key_per_org"),
        # Performance indexes
        Index("idx_project_org_key", "organization_id", "key"),
        Index("idx_project_org_status", "organization_id", "status"),
        Index("idx_project_lead_active", "lead_id", "status"),
        Index("idx_project_visibility_public", "visibility", "organization_id"),
        Index("idx_project_dates", "start_date", "due_date"),
        Index("idx_project_archived", "archived_at", "organization_id"),
        # Data validation
        CheckConstraint("key ~ '^[A-Z][A-Z0-9]*$'", name="project_key_format"),
        CheckConstraint(
            "LENGTH(key) >= 2 AND LENGTH(key) <= 6", name="project_key_length"
        ),
        CheckConstraint(
            "color IS NULL OR color ~ '^#[0-9A-Fa-f]{6}$'", name="valid_hex_color"
        ),
        CheckConstraint(
            "start_date IS NULL OR due_date IS NULL OR start_date <= due_date",
            name="valid_date_range",
        ),
    )

    @property
    def current_members(self) -> int:
        """Count active project members using RBAC"""
        return len([r for r in self.user_roles if r.is_active])

    def get_project_url(self) -> str:
        """Get project URL"""
        return f"/org/{self.organization.slug}/projects/{self.key}"

    def __repr__(self) -> str:
        return f"<Project(org={self.organization.slug if self.organization else 'None'}, key={self.key}, name={self.name})>"
