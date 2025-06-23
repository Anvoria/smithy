import uuid
from datetime import datetime, UTC
from typing import Optional
from enum import Enum

from sqlalchemy import DateTime, Index, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProjectRole(str, Enum):
    """Roles within a specific project"""

    LEAD = "lead"  # Project manager/lead
    DEVELOPER = "developer"  # Can create/edit tasks
    REVIEWER = "reviewer"  # Can review/approve tasks
    VIEWER = "viewer"  # Read-only access


class ProjectMember(Base):
    """
    Project-specific member roles (optional granular access control).
    For when you need more fine-grained permissions than org-level roles.
    """

    # Foreign Keys
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        comment="Project ID",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User ID",
    )

    # Role within this specific project
    role: Mapped[ProjectRole] = mapped_column(
        default=ProjectRole.DEVELOPER,
        nullable=False,
        comment="Role within this project",
    )

    # Metadata
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        comment="When user was added to project",
    )

    added_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Who added this user to project",
    )

    # Relationships
    project = relationship("Project")
    user = relationship("User", foreign_keys=[user_id])
    adder = relationship("User", foreign_keys=[added_by])

    # Database Constraints
    __table_args__ = (
        # Unique user per project
        UniqueConstraint("project_id", "user_id", name="unique_project_member"),
        # Indexes
        Index("idx_project_members", "project_id", "role"),
        Index("idx_user_projects", "user_id", "role"),
    )

    @property
    def can_manage_tasks(self) -> bool:
        """Check if member can manage tasks"""
        return self.role in [ProjectRole.LEAD, ProjectRole.DEVELOPER]

    @property
    def can_review_tasks(self) -> bool:
        """Check if member can review tasks"""
        return self.role in [ProjectRole.LEAD, ProjectRole.REVIEWER]

    def __repr__(self) -> str:
        return f"<ProjectMember(project_id={self.project_id}, user_id={self.user_id}, role={self.role})>"
