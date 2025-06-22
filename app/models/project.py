import uuid
from datetime import datetime, UTC
from typing import Optional, TYPE_CHECKING
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

if TYPE_CHECKING:
    from app.models.project_member import ProjectMember

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

    # Project Lead
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

    # # Template System
    # is_template: Mapped[bool] = mapped_column(
    #     Boolean,
    #     default=False,
    #     nullable=False,
    #     index=True,
    #     comment="Is this project a template"
    # )
    #
    # template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
    #     UUID(as_uuid=True),
    #     ForeignKey("projects.id", ondelete="SET NULL"),
    #     nullable=True,
    #     comment="Source template if created from template"
    # )

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
    # tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan") #TODO https://github.com/Anvoria/smithy-backend/issues/7
    tasks: list = []
    members = relationship(
        "ProjectMember", back_populates="project", cascade="all, delete-orphan"
    )

    # Database Constraints
    __table_args__ = (
        # Unique key per organization
        UniqueConstraint("organization_id", "key", name="unique_project_key_per_org"),
        # Indexes for performance
        Index("idx_project_org_status", "organization_id", "status"),
        Index("idx_project_org_key", "organization_id", "key"),
        Index("idx_project_lead_active", "lead_id", "status"),
        Index("idx_project_visibility_public", "visibility", "organization_id"),
        Index("idx_project_dates", "start_date", "due_date"),
        Index("idx_project_archived", "archived_at", "organization_id"),
        # Check constraints
        CheckConstraint(
            "LENGTH(key) >= 2 AND LENGTH(key) <= 6", name="project_key_length"
        ),
        CheckConstraint("key ~ '^[A-Z][A-Z0-9]*$'", name="project_key_format"),
        CheckConstraint(
            "color IS NULL OR color ~ '^#[0-9A-Fa-f]{6}$'", name="valid_hex_color"
        ),
        CheckConstraint(
            "start_date IS NULL OR due_date IS NULL OR start_date <= due_date",
            name="valid_date_range",
        ),
    )

    # Properties for common operations
    @property
    def progress_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100

    @property
    def is_overdue(self) -> bool:
        """Check if project is overdue"""
        if not self.due_date or self.status == ProjectStatus.COMPLETED:
            return False
        return datetime.now(UTC) > self.due_date

    @property
    def is_active(self) -> bool:
        """Check if project is currently active"""
        return (
            self.status == ProjectStatus.ACTIVE
            and not self.deleted_at
            and not self.archived_at
        )

    @property
    def days_until_due(self) -> Optional[int]:
        """Get days until due date"""
        if not self.due_date:
            return None
        delta = self.due_date.date() - datetime.now(UTC).date()
        return delta.days

    @property
    def next_task_number(self) -> int:
        """Get next task number (MAX + 1)"""
        if not self.tasks:
            return 1
        return max(task.task_number for task in self.tasks) + 1

    @property
    def next_task_id(self) -> str:
        """Get next task ID"""
        return f"{self.key}-{self.next_task_number}"

    @property
    def total_tasks(self) -> int:
        """Count all tasks"""
        return len([t for t in self.tasks if not t.deleted_at])

    @property
    def completed_tasks(self) -> int:
        """Count completed tasks"""
        return len([t for t in self.tasks if t.status == "done" and not t.deleted_at])

    @property
    def display_icon(self) -> str:
        """Get display icon with fallback"""
        if self.icon:
            return self.icon
        # Default icons based on status
        status_icons = {
            ProjectStatus.PLANNING: "📋",
            ProjectStatus.ACTIVE: "🚀",
            ProjectStatus.ON_HOLD: "⏸️",
            ProjectStatus.COMPLETED: "✅",
            ProjectStatus.ARCHIVED: "📦",
            ProjectStatus.CANCELLED: "❌",
        }
        return status_icons.get(self.status, "📁")

    @property
    def display_color(self) -> str:
        """Get display color with fallback"""
        if self.color:
            return self.color
        # Default colors based on priority
        priority_colors = {
            ProjectPriority.LOW: "#10B981",  # Green
            ProjectPriority.MEDIUM: "#F59E0B",  # Yellow
            ProjectPriority.HIGH: "#EF4444",  # Red
            ProjectPriority.CRITICAL: "#7C2D12",  # Dark Red
        }
        return priority_colors.get(self.priority, "#6B7280")  # Gray default

    @property
    def full_key(self) -> str:
        """Get full project identifier with org"""
        return f"{self.organization.slug}/{self.key}"

    def get_user_project_membership(
        self, user_id: uuid.UUID
    ) -> Optional["ProjectMember"]:
        """
        Get project membership for a specific user.
        :param user_id: UUID of the user
        :return: ProjectMember if user is a member, None otherwise
        """
        for member in self.members:
            if member.user_id == user_id:
                return member
        return None

    def can_user_access(
        self, user_id: uuid.UUID, user_role_in_org: str | None = None
    ) -> bool:
        """
        Check if user can access this project.
        :param user_id: UUID of the user trying to access
        :param user_role_in_org: Role of the user in the organization (if known)
        :return: True if user can access, False otherwise
        """
        # Project lead can always access
        if self.lead_id == user_id:
            return True

        # Check if user is project member
        project_member = self.get_user_project_membership(user_id)
        if project_member:
            return True  # Any project member can access

        # If public and org allows public projects
        if (
            self.visibility == ProjectVisibility.PUBLIC
            and self.organization.public_projects
        ):
            return True

        # For organization visibility, check org membership
        if self.visibility == ProjectVisibility.ORGANIZATION and user_role_in_org:
            return True

        # Org admins can access any project
        if user_role_in_org in ["owner", "admin"]:
            return True

        return False

    def can_user_edit(
        self, user_id: uuid.UUID, user_role_in_org: str | None = None
    ) -> bool:
        """
        Check if user can edit this project.
        :param user_id: UUID of the user trying to edit
        :param user_role_in_org: Role of the user in the organization (if known)
        :return: True if user can edit, False otherwise
        """
        # Project lead can edit
        if self.lead_id == user_id:
            return True

        # Check project-specific permissions
        project_member = self.get_user_project_membership(user_id)
        if (
            project_member
            and project_member.role
            and str(project_member.role.value) == "lead"
        ):
            return True

        # Org owners/admins can edit any project
        if user_role_in_org in ["owner", "admin"]:
            return True

        # Org managers can edit if they're project members
        if user_role_in_org == "manager" and project_member:
            return True

        return False

    def can_user_manage_tasks(
        self, user_id: uuid.UUID, user_role_in_org: str | None = None
    ) -> bool:
        """
        Check if user can manage tasks in this project.
        :param user_id: UUID of the user trying to manage tasks
        :param user_role_in_org: Role of the user in the organization (if known)
        :return: True if user can manage tasks, False otherwise
        """
        # Project lead can manage tasks
        if self.lead_id == user_id:
            return True

        # Check project-specific permissions
        project_member = self.get_user_project_membership(user_id)
        if project_member:
            return project_member.can_manage_tasks

        # Org admins/managers can manage tasks
        if user_role_in_org in ["owner", "admin", "manager"]:
            return True

        return False

    def get_project_url(self) -> str:
        """Get project URL"""
        return f"/org/{self.organization.slug}/projects/{self.key}"

    def __repr__(self) -> str:
        return (
            f"<Project(org={self.organization.slug}, key={self.key}, name={self.name})>"
        )
