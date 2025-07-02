import uuid
from datetime import datetime, UTC
from typing import Optional, List, TYPE_CHECKING
from enum import Enum

from sqlalchemy import (
    String,
    DateTime,
    Text,
    Integer,
    JSON,
    Index,
    CheckConstraint,
    ForeignKey,
    UniqueConstraint,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    pass

from app.db.base import Base


class TaskStatus(str, Enum):
    """Task status options"""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels"""

    LOWEST = "lowest"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    HIGHEST = "highest"


class TaskType(str, Enum):
    """Task type categories"""

    FEATURE = "feature"
    BUG = "bug"
    IMPROVEMENT = "improvement"
    DOCUMENTATION = "documentation"
    RESEARCH = "research"
    MAINTENANCE = "maintenance"
    TESTING = "testing"


class Task(Base):
    """
    Task model for project management.
    Supports hierarchical tasks, assignments, dependencies, and time tracking.
    """

    title: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Task title"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Detailed task description"
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Project this task belongs to",
    )

    # Task identification within project
    task_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sequential task number within project (e.g., 1, 2, 3...)",
    )

    # Task hierarchy
    parent_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Parent task for subtasks",
    )

    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
        comment="User who created/reported this task",
    )

    # Status and Classification
    status: Mapped[TaskStatus] = mapped_column(
        default=TaskStatus.TODO,
        nullable=False,
        index=True,
        comment="Current task status",
    )

    priority: Mapped[TaskPriority] = mapped_column(
        default=TaskPriority.MEDIUM,
        nullable=False,
        index=True,
        comment="Task priority level",
    )

    task_type: Mapped[TaskType] = mapped_column(
        default=TaskType.FEATURE,
        nullable=False,
        index=True,
        comment="Task type/category",
    )

    # Dates and Time Tracking
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Task due date"
    )

    start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When work started"
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When task was completed"
    )

    # Time estimates and tracking (in hours)
    estimated_hours: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Estimated hours to complete"
    )

    logged_hours: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False, comment="Actual hours logged"
    )

    # Story points for agile teams
    story_points: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Story points estimate"
    )

    # Labels and metadata
    labels: Mapped[Optional[List[str]]] = mapped_column(
        JSON, default=list, nullable=True, comment="Task labels/tags"
    )

    custom_fields: Mapped[Optional[dict]] = mapped_column(
        JSON, default=dict, nullable=True, comment="Custom field values"
    )

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Soft deletion timestamp",
    )

    # Relationships
    project = relationship("Project", back_populates="tasks")
    reporter = relationship("User", foreign_keys=[reporter_id])

    # Task assignments (many-to-many)
    assignees = relationship(
        "TaskAssignee", back_populates="task", cascade="all, delete-orphan"
    )

    # Hierarchical relationships
    parent_task = relationship("Task", remote_side="Task.id", back_populates="subtasks")
    subtasks = relationship(
        "Task", back_populates="parent_task", cascade="all, delete-orphan"
    )

    # Dependencies
    blocking_tasks = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.blocked_task_id",
        back_populates="blocked_task",
        cascade="all, delete-orphan",
    )

    blocked_by_tasks = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.blocking_task_id",
        back_populates="blocking_task",
    )

    # Comments and attachments
    comments = relationship(
        "TaskComment",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskComment.created_at.desc()",
    )

    attachments = relationship(
        "TaskAttachment", back_populates="task", cascade="all, delete-orphan"
    )

    # Time logs
    time_logs = relationship(
        "TaskTimeLog", back_populates="task", cascade="all, delete-orphan"
    )

    # Database Constraints
    __table_args__ = (
        # Unique task number per project
        UniqueConstraint(
            "project_id", "task_number", name="unique_task_number_per_project"
        ),
        # Indexes for performance
        Index("idx_task_project_status", "project_id", "status"),
        Index("idx_task_project_priority", "project_id", "priority"),
        Index("idx_task_due_date", "due_date", "status"),
        Index("idx_task_hierarchy", "parent_task_id", "project_id"),
        Index("idx_task_deleted", "deleted_at", "project_id"),
        # Check constraints
        CheckConstraint(
            "estimated_hours IS NULL OR estimated_hours >= 0",
            name="positive_estimated_hours",
        ),
        CheckConstraint("logged_hours >= 0", name="positive_logged_hours"),
        CheckConstraint(
            "story_points IS NULL OR story_points >= 0", name="positive_story_points"
        ),
        CheckConstraint("task_number > 0", name="positive_task_number"),
        CheckConstraint(
            "start_date IS NULL OR due_date IS NULL OR start_date <= due_date",
            name="valid_task_date_range",
        ),
    )

    # Properties for common operations
    @property
    def task_id(self) -> str:
        """Get full task ID (PROJECT-123)"""
        if hasattr(self, "project") and self.project:
            return f"{self.project.key}-{self.task_number}"
        return f"TASK-{self.task_number}"

    @property
    def is_subtask(self) -> bool:
        """Check if this is a subtask"""
        return self.parent_task_id is not None

    @property
    def is_parent_task(self) -> bool:
        """Check if this task has subtasks"""
        return len(self.subtasks) > 0

    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        if not self.due_date or self.status in [TaskStatus.DONE, TaskStatus.CANCELLED]:
            return False
        return datetime.now(UTC) > self.due_date

    @property
    def is_blocked(self) -> bool:
        """Check if task is blocked by dependencies"""
        if self.status == TaskStatus.BLOCKED:
            return True

        # Check if any blocking dependencies are not done
        for dep in self.blocked_by_tasks:
            if dep.blocking_task.status != TaskStatus.DONE:
                return True
        return False

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage based on subtasks"""
        if not self.subtasks:
            return 100.0 if self.status == TaskStatus.DONE else 0.0

        completed_subtasks = sum(
            1 for subtask in self.subtasks if subtask.status == TaskStatus.DONE
        )
        return (completed_subtasks / len(self.subtasks)) * 100

    @property
    def time_spent_percentage(self) -> Optional[float]:
        """Calculate percentage of estimated time spent"""
        if not self.estimated_hours or self.estimated_hours == 0:
            return None
        return min((self.logged_hours / self.estimated_hours) * 100, 999.9)

    @property
    def days_until_due(self) -> Optional[int]:
        """Get days until due date"""
        if not self.due_date:
            return None
        delta = self.due_date.date() - datetime.now(UTC).date()
        return delta.days

    def can_user_view(
        self, user_id: uuid.UUID, user_role_in_project: str | None = None
    ) -> bool:
        """Check if user can view this task"""
        # Reporter and assignees can always view
        if self.reporter_id == user_id:
            return True

        # Check if user is assigned to this task
        if any(assignment.user_id == user_id for assignment in self.assignees):
            return True

        # Project leads and organization admins can view all tasks
        if user_role_in_project in ["lead", "admin", "owner"]:
            return True

        # Regular project members can view tasks
        if user_role_in_project in ["developer", "reviewer"]:
            return True

        return False

    def can_user_edit(
        self, user_id: uuid.UUID, user_role_in_project: str | None = None
    ) -> bool:
        """Check if user can edit this task"""
        # Assignees can edit their tasks
        if any(assignment.user_id == user_id for assignment in self.assignees):
            return True

        # Reporter can edit their tasks
        if self.reporter_id == user_id:
            return True

        # Project leads and admins can edit all tasks
        if user_role_in_project in ["lead", "admin", "owner"]:
            return True

        return False

    def __repr__(self) -> str:
        return (
            f"<Task(id={self.task_id}, title={self.title[:30]}, status={self.status})>"
        )


class TaskAssignee(Base):
    """
    Junction table for task assignments (many-to-many relationship).
    Allows multiple users to be assigned to a single task.
    """

    __tablename__ = "task_assignees"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="Task ID",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Assigned user ID",
    )

    assigned_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        comment="User who made this assignment",
    )

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        comment="When user was assigned",
    )

    # Relationships
    task = relationship("Task", back_populates="assignees")
    user = relationship("User", foreign_keys=[user_id])
    assigner = relationship("User", foreign_keys=[assigned_by])

    __table_args__ = (
        UniqueConstraint("task_id", "user_id", name="unique_task_assignee"),
        Index("idx_task_assignee_task", "task_id"),
        Index("idx_task_assignee_user", "user_id"),
    )


class TaskDependency(Base):
    """
    Task dependency relationships (task A blocks task B).
    """

    __tablename__ = "task_dependencies"

    blocking_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="Task that blocks another task",
    )

    blocked_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="Task that is blocked",
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        comment="User who created this dependency",
    )

    # Relationships
    blocking_task = relationship("Task", foreign_keys=[blocking_task_id])
    blocked_task = relationship("Task", foreign_keys=[blocked_task_id])
    creator = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "blocking_task_id", "blocked_task_id", name="unique_task_dependency"
        ),
        Index("idx_dependency_blocking", "blocking_task_id"),
        Index("idx_dependency_blocked", "blocked_task_id"),
    )


class TaskComment(Base):
    """
    Comments on tasks for collaboration and discussion.
    """

    __tablename__ = "task_comments"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Task this comment belongs to",
    )

    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        comment="User who wrote this comment",
    )

    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Comment content (markdown supported)"
    )

    # Optional parent comment for threading
    parent_comment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("task_comments.id", ondelete="CASCADE"),
        nullable=True,
        comment="Parent comment for replies",
    )

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Soft deletion timestamp"
    )

    # Relationships
    task = relationship("Task", back_populates="comments")
    author = relationship("User")
    parent_comment = relationship("TaskComment", remote_side="TaskComment.id")
    replies = relationship("TaskComment", back_populates="parent_comment")

    __table_args__ = (
        Index("idx_comment_task", "task_id", "created_at"),
        Index("idx_comment_author", "author_id"),
    )


class TaskAttachment(Base):
    """
    File attachments for tasks.
    """

    __tablename__ = "task_attachments"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Task this attachment belongs to",
    )

    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        comment="User who uploaded this file",
    )

    filename: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Original filename"
    )

    file_path: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Storage path/URL"
    )

    file_size: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="File size in bytes"
    )

    content_type: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="MIME type"
    )

    # Relationships
    task = relationship("Task", back_populates="attachments")
    uploader = relationship("User")

    __table_args__ = (
        Index("idx_attachment_task", "task_id"),
        CheckConstraint("file_size > 0", name="positive_file_size"),
    )


class TaskTimeLog(Base):
    """
    Time tracking entries for tasks.
    """

    __tablename__ = "task_time_logs"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Task this time log belongs to",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        comment="User who logged this time",
    )

    hours: Mapped[float] = mapped_column(Float, nullable=False, comment="Hours worked")

    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Description of work done"
    )

    date_worked: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        comment="Date when work was done",
    )

    # Relationships
    task = relationship("Task", back_populates="time_logs")
    user = relationship("User")

    __table_args__ = (
        Index("idx_time_log_task", "task_id", "date_worked"),
        Index("idx_time_log_user", "user_id", "date_worked"),
        CheckConstraint("hours > 0", name="positive_hours"),
    )
