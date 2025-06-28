import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Annotated

from pydantic import BaseModel, Field, field_validator, computed_field

from app.models.task import TaskStatus, TaskPriority, TaskType


# ==========================================
# Base Schemas
# ==========================================


class TaskBase(BaseModel):
    """Base task schema with common fields"""

    title: Annotated[str, Field(min_length=1, max_length=500, description="Task title")]
    description: Optional[str] = Field(None, description="Detailed task description")

    # Classification
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="Task priority")
    task_type: TaskType = Field(TaskType.FEATURE, description="Task type")

    # Assignment - list of user IDs
    assignee_ids: Optional[List[uuid.UUID]] = Field(
        default_factory=list, description="List of assigned user IDs"
    )

    # Dates
    due_date: Optional[datetime] = Field(None, description="Task due date")
    start_date: Optional[datetime] = Field(None, description="When work should start")

    # Time tracking
    estimated_hours: Optional[float] = Field(
        None, ge=0, le=1000, description="Estimated hours to complete"
    )
    story_points: Optional[int] = Field(
        None, ge=0, le=100, description="Story points estimate"
    )

    # Metadata
    labels: Optional[List[str]] = Field(
        default_factory=list, description="Task labels/tags"
    )
    custom_fields: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Custom field values"
    )

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, v: List[str]) -> List[str]:
        """Validate and clean labels"""
        if not v:
            return []
        # Remove duplicates and empty strings, limit length
        clean_labels = list(set(label.strip() for label in v if label.strip()))
        return clean_labels[:20]  # Max 20 labels


# ==========================================
# Request Schemas
# ==========================================


class TaskCreate(TaskBase):
    """Schema for creating a new task"""

    project_id: uuid.UUID = Field(..., description="Project ID")
    parent_task_id: Optional[uuid.UUID] = Field(
        None, description="Parent task ID for subtasks"
    )


class TaskUpdate(BaseModel):
    """Schema for updating task information"""

    title: Annotated[Optional[str], Field(default=None, min_length=1, max_length=500)]
    description: Optional[str] = None

    # Classification
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    task_type: Optional[TaskType] = None

    # Assignment - list of user IDs
    assignee_ids: Optional[List[uuid.UUID]] = Field(
        None, description="List of assigned user IDs"
    )

    # Dates
    due_date: Optional[datetime] = None
    start_date: Optional[datetime] = None

    # Time tracking
    estimated_hours: Optional[float] = Field(None, ge=0, le=1000)
    story_points: Optional[int] = Field(None, ge=0, le=100)

    # Metadata
    labels: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate and clean labels"""
        if v is None:
            return v
        clean_labels = list(set(label.strip() for label in v if label.strip()))
        return clean_labels[:20]


class TaskStatusUpdate(BaseModel):
    """Schema for updating task status"""

    status: TaskStatus = Field(..., description="New task status")
    comment: Optional[str] = Field(
        None, description="Optional comment about status change"
    )


class TaskAssignmentUpdate(BaseModel):
    """Schema for updating task assignments"""

    assignee_ids: List[uuid.UUID] = Field(..., description="List of user IDs to assign")
    comment: Optional[str] = Field(
        None, description="Optional comment about assignment change"
    )


# ==========================================
# Assignment Schemas
# ==========================================


class TaskAssigneeResponse(BaseModel):
    """Task assignee response schema"""

    model_config = {"from_attributes": True}

    user_id: uuid.UUID
    assigned_at: datetime

    # User info
    user_name: Optional[str] = Field(None, alias="user.full_name")
    user_email: str = Field(alias="user.email")
    user_username: Optional[str] = Field(None, alias="user.username")
    user_avatar_url: Optional[str] = Field(None, alias="user.avatar_url")

    # Assigner info
    assigned_by: uuid.UUID
    assigner_name: Optional[str] = Field(None, alias="assigner.full_name")


class TaskAssigneeCreate(BaseModel):
    """Schema for creating task assignments"""

    user_ids: List[uuid.UUID] = Field(..., description="List of user IDs to assign")
    comment: Optional[str] = Field(
        None, description="Optional comment about assignment"
    )


# ==========================================
# Dependency Schemas
# ==========================================


class TaskDependencyCreate(BaseModel):
    """Schema for creating task dependencies"""

    blocking_task_id: uuid.UUID = Field(..., description="Task that blocks")
    blocked_task_id: uuid.UUID = Field(..., description="Task that is blocked")

    @field_validator("blocked_task_id")
    @classmethod
    def validate_not_self_dependency(cls, v: uuid.UUID, info) -> uuid.UUID:
        """Ensure task doesn't depend on itself"""
        if hasattr(info, "data") and info.data.get("blocking_task_id") == v:
            raise ValueError("Task cannot depend on itself")
        return v


class TaskDependencyResponse(BaseModel):
    """Task dependency response schema"""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    blocking_task_id: uuid.UUID
    blocked_task_id: uuid.UUID
    created_at: datetime

    # Related task info
    blocking_task_title: Optional[str] = Field(None, alias="blocking_task.title")
    blocked_task_title: Optional[str] = Field(None, alias="blocked_task.title")


# ==========================================
# Comment Schemas
# ==========================================


class TaskCommentCreate(BaseModel):
    """Schema for creating task comments"""

    content: Annotated[
        str, Field(min_length=1, max_length=10000, description="Comment content")
    ]
    parent_comment_id: Optional[uuid.UUID] = Field(
        None, description="Parent comment ID for replies"
    )


class TaskCommentUpdate(BaseModel):
    """Schema for updating comments"""

    content: Annotated[
        str,
        Field(min_length=1, max_length=10000, description="Updated comment content"),
    ]


class TaskCommentResponse(BaseModel):
    """Task comment response schema"""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    content: str
    parent_comment_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    # Author info
    author_id: uuid.UUID
    author_name: Optional[str] = Field(None, alias="author.full_name")
    author_email: str = Field(alias="author.email")
    author_avatar_url: Optional[str] = Field(None, alias="author.avatar_url")

    # Reply count
    @property
    @computed_field
    def reply_count(self) -> int:
        """Count of replies to this comment"""
        return getattr(self, "_reply_count", 0)


# ==========================================
# Time Tracking Schemas
# ==========================================


class TaskTimeLogCreate(BaseModel):
    """Schema for creating time logs"""

    hours: Annotated[
        float, Field(gt=0, le=24, description="Hours worked (max 24 per entry)")
    ]
    description: Optional[str] = Field(None, description="Description of work done")
    date_worked: Optional[datetime] = Field(
        None, description="Date when work was done (defaults to today)"
    )


class TaskTimeLogUpdate(BaseModel):
    """Schema for updating time logs"""

    hours: Annotated[
        float, Field(gt=0, le=24, description="Hours worked (max 24 per entry)")
    ]
    description: Optional[str] = Field(None, description="Description of work done")
    date_worked: Optional[datetime] = Field(None, description="Date when work was done")


class TaskTimeLogResponse(BaseModel):
    """Time log response schema"""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    hours: float
    description: Optional[str]
    date_worked: datetime
    created_at: datetime

    # User info
    user_id: uuid.UUID
    user_name: Optional[str] = Field(None, alias="user.full_name")
    user_email: str = Field(alias="user.email")


# ==========================================
# Response Schemas
# ==========================================


class TaskResponse(BaseModel):
    """Complete task response schema"""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    task_number: int
    title: str
    description: Optional[str]

    # Project info
    project_id: uuid.UUID
    project_key: Optional[str] = Field(None, alias="project.key")
    project_name: Optional[str] = Field(None, alias="project.name")

    # Hierarchy
    parent_task_id: Optional[uuid.UUID]

    # Assignments (list of assignees)
    assignees: List[TaskAssigneeResponse] = Field(default_factory=list)

    reporter_id: uuid.UUID
    reporter_name: Optional[str] = Field(None, alias="reporter.full_name")
    reporter_email: str = Field(alias="reporter.email")

    # Classification
    status: TaskStatus
    priority: TaskPriority
    task_type: TaskType

    # Dates
    due_date: Optional[datetime]
    start_date: Optional[datetime]
    completed_at: Optional[datetime]

    # Time tracking
    estimated_hours: Optional[float]
    logged_hours: float
    story_points: Optional[int]

    # Metadata
    labels: List[str]
    custom_fields: Dict[str, Any]

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Computed fields
    @property
    @computed_field
    def task_id(self) -> str:
        """Get full task ID (PROJECT-123)"""
        if self.project_key:
            return f"{self.project_key}-{self.task_number}"
        return f"TASK-{self.task_number}"

    @property
    @computed_field
    def is_subtask(self) -> bool:
        """Check if this is a subtask"""
        return self.parent_task_id is not None

    @property
    @computed_field
    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        if not self.due_date or self.status in [TaskStatus.DONE, TaskStatus.CANCELLED]:
            return False
        return datetime.now() > self.due_date

    @property
    @computed_field
    def days_until_due(self) -> Optional[int]:
        """Get days until due date"""
        if not self.due_date:
            return None
        delta = self.due_date.date() - datetime.now().date()
        return delta.days

    @property
    @computed_field
    def time_spent_percentage(self) -> Optional[float]:
        """Calculate percentage of estimated time spent"""
        if not self.estimated_hours or self.estimated_hours == 0:
            return None
        return min((self.logged_hours / self.estimated_hours) * 100, 999.9)

    @property
    @computed_field
    def assignee_count(self) -> int:
        """Count of assigned users"""
        return len(self.assignees)

    @property
    @computed_field
    def assignee_names(self) -> List[str]:
        """List of assignee display names"""
        return [
            assignee.user_name
            or assignee.user_username
            or assignee.user_email.split("@")[0]
            for assignee in self.assignees
        ]


class TaskListItem(BaseModel):
    """Simplified task schema for lists"""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    task_number: int
    title: str
    status: TaskStatus
    priority: TaskPriority
    task_type: TaskType

    # Project info
    project_key: Optional[str] = Field(None, alias="project.key")

    # Basic assignment info
    assignee_count: int = 0

    # Dates
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @property
    @computed_field
    def task_id(self) -> str:
        """Get full task ID (PROJECT-123)"""
        if self.project_key:
            return f"{self.project_key}-{self.task_number}"
        return f"TASK-{self.task_number}"

    @property
    @computed_field
    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        if not self.due_date or self.status in [TaskStatus.DONE, TaskStatus.CANCELLED]:
            return False
        return datetime.now() > self.due_date


class TaskStats(BaseModel):
    """Task statistics for dashboard"""

    total_tasks: int
    open_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    overdue_tasks: int

    tasks_by_status: Dict[TaskStatus, int]
    tasks_by_priority: Dict[TaskPriority, int]
    tasks_by_type: Dict[TaskType, int]

    avg_completion_time_days: Optional[float]
    avg_time_to_first_response_hours: Optional[float]


class TaskFilters(BaseModel):
    """Schema for task filtering"""

    status: Optional[List[TaskStatus]] = None
    priority: Optional[List[TaskPriority]] = None
    task_type: Optional[List[TaskType]] = None
    assignee_ids: Optional[List[uuid.UUID]] = None
    reporter_id: Optional[uuid.UUID] = None
    labels: Optional[List[str]] = None
    due_date_from: Optional[datetime] = None
    due_date_to: Optional[datetime] = None
    search: Optional[str] = None
    include_subtasks: bool = True
    parent_task_id: Optional[uuid.UUID] = None


# ==========================================
# Bulk Operations
# ==========================================


class TaskBulkUpdate(BaseModel):
    """Schema for bulk task updates"""

    task_ids: List[uuid.UUID] = Field(..., description="List of task IDs to update")

    # Fields that can be bulk updated
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee_ids: Optional[List[uuid.UUID]] = None
    labels: Optional[List[str]] = None
    due_date: Optional[datetime] = None


class TaskBulkResponse(BaseModel):
    """Response for bulk operations"""

    success_count: int
    error_count: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    updated_tasks: List[TaskListItem] = Field(default_factory=list)


# ==========================================
# Export all schemas
# ==========================================

__all__ = [
    # Base
    "TaskBase",
    # Request schemas
    "TaskCreate",
    "TaskUpdate",
    "TaskStatusUpdate",
    "TaskAssignmentUpdate",
    "TaskAssigneeCreate",
    "TaskBulkUpdate",
    # Dependency schemas
    "TaskDependencyCreate",
    "TaskDependencyResponse",
    # Comment schemas
    "TaskCommentCreate",
    "TaskCommentUpdate",
    "TaskCommentResponse",
    # Time tracking schemas
    "TaskTimeLogCreate",
    "TaskTimeLogUpdate",
    "TaskTimeLogResponse",
    # Assignment schemas
    "TaskAssigneeResponse",
    # Response schemas
    "TaskResponse",
    "TaskListItem",
    "TaskStats",
    # Utility schemas
    "TaskFilters",
    "TaskBulkResponse",
]
