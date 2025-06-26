import uuid
from datetime import datetime
from typing import Optional, Dict, Annotated

from pydantic import BaseModel, Field, field_validator, computed_field

from app.models.project import ProjectStatus, ProjectPriority, ProjectVisibility
from app.models.project_member import ProjectRole


class ProjectSettings(BaseModel):
    """Project settings schema"""

    # Task management
    default_task_priority: ProjectPriority = ProjectPriority.MEDIUM
    auto_close_completed_tasks: bool = False

    # Workflow settings
    require_task_approval: bool = False
    allow_subtasks: bool = True
    enable_time_tracking: bool = False

    # Notifications
    notify_on_task_creation: bool = True
    notify_on_task_completion: bool = True
    notify_on_due_date: bool = True


class ProjectBase(BaseModel):
    """Base project schema with common fields"""

    name: Annotated[
        str, Field(min_length=1, max_length=200, description="Project name")
    ]
    key: Annotated[
        str,
        Field(
            min_length=2,
            max_length=6,
            description="Project key (2-6 uppercase letters)",
        ),
    ]
    description: Optional[str] = Field(None, description="Project description")
    icon: Optional[str] = Field(None, description="Project icon (emoji or icon name)")
    color: Optional[str] = Field(None, description="Project color (hex)")
    cover_image_url: Optional[str] = Field(None, description="Cover image URL")

    # Dates
    start_date: Optional[datetime] = Field(None, description="Project start date")
    due_date: Optional[datetime] = Field(None, description="Project due date")

    # Configuration
    priority: ProjectPriority = Field(
        ProjectPriority.MEDIUM, description="Project priority"
    )
    visibility: ProjectVisibility = Field(
        ProjectVisibility.ORGANIZATION, description="Project visibility"
    )
    enable_subtasks: bool = Field(True, description="Enable subtask creation")

    # Settings
    settings: Optional[ProjectSettings] = Field(None, description="Project settings")

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        """Validate project key format"""
        if not v.isupper():
            v = v.upper()
        if not v.isalnum():
            raise ValueError("Project key must contain only letters and numbers")
        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate hex color format"""
        if v is None:
            return v
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Color must be in #RRGGBB format")
        try:
            int(v[1:], 16)
        except ValueError:
            raise ValueError("Invalid hex color format")
        return v.upper()


class ProjectCreate(ProjectBase):
    """Schema for creating a new project"""

    organization_id: uuid.UUID = Field(..., description="Organization ID")
    lead_id: Optional[uuid.UUID] = Field(None, description="Project lead user ID")


class ProjectUpdate(BaseModel):
    """Schema for updating project information"""

    name: Annotated[Optional[str], Field(default=None, min_length=1, max_length=200)]
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    cover_image_url: Optional[str] = None

    # Status and priority
    status: Optional[ProjectStatus] = None
    priority: Optional[ProjectPriority] = None
    visibility: Optional[ProjectVisibility] = None

    # Dates
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None

    # Project lead
    lead_id: Optional[uuid.UUID] = None

    # Configuration
    enable_subtasks: Optional[bool] = None
    settings: Optional[ProjectSettings] = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate hex color format"""
        if v is None:
            return v
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Color must be in #RRGGBB format")
        try:
            int(v[1:], 16)
        except ValueError:
            raise ValueError("Invalid hex color format")
        return v.upper()


class ProjectMemberInvite(BaseModel):
    """Schema for inviting a member to project"""

    user_id: uuid.UUID = Field(..., description="User ID to invite")
    role: ProjectRole = Field(ProjectRole.DEVELOPER, description="Role to assign")


class ProjectMemberUpdate(BaseModel):
    """Schema for updating project member role"""

    role: ProjectRole = Field(..., description="New role for the member")


class ProjectMemberResponse(BaseModel):
    """Project member response schema"""

    model_config = {"from_attributes": True}

    user_id: uuid.UUID
    role: ProjectRole
    added_at: datetime

    # User information
    user_email: str = Field(alias="user.email")
    user_username: Optional[str] = Field(alias="user.username", default=None)
    user_first_name: Optional[str] = Field(alias="user.first_name", default=None)
    user_last_name: Optional[str] = Field(alias="user.last_name", default=None)
    user_avatar_url: Optional[str] = Field(alias="user.avatar_url", default=None)

    @property
    def display_name(self) -> str:
        """Get member display name"""
        if self.user_first_name and self.user_last_name:
            return f"{self.user_first_name} {self.user_last_name}"
        elif self.user_first_name:
            return self.user_first_name
        elif self.user_username:
            return self.user_username
        return self.user_email


class ProjectResponse(BaseModel):
    """Complete project response schema"""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    key: str
    description: Optional[str]

    # Organization
    organization_id: uuid.UUID
    organization_slug: str = Field(alias="organization.slug")

    # Lead
    lead_id: Optional[uuid.UUID]
    lead_name: Optional[str] = Field(None, alias="lead.full_name")
    lead_email: Optional[str] = Field(None, alias="lead.email")

    # Visual
    icon: Optional[str]
    color: Optional[str]
    cover_image_url: Optional[str]

    # Status and priority
    status: ProjectStatus
    priority: ProjectPriority
    visibility: ProjectVisibility

    # Dates
    start_date: Optional[datetime]
    due_date: Optional[datetime]
    completed_at: Optional[datetime]

    # Configuration
    enable_subtasks: bool
    settings: Optional[ProjectSettings] = None

    # Metadata
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime]

    @property
    @computed_field
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
    @computed_field
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
    @computed_field
    def progress_percentage(self) -> float:
        """Calculate completion percentage"""
        # TODO: Calculate from actual tasks when task system is implemented
        # https://github.com/Anvoria/smithy/issues/7
        return 0.0

    @property
    @computed_field
    def total_tasks(self) -> int:
        """Count all tasks"""
        # TODO: Calculate from actual tasks
        return 0

    @property
    @computed_field
    def completed_tasks(self) -> int:
        """Count completed tasks"""
        # TODO: Calculate from actual tasks
        return 0

    @property
    @computed_field
    def is_overdue(self) -> bool:
        """Check if project is overdue"""
        if not self.due_date or self.status == ProjectStatus.COMPLETED:
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
    def project_url(self) -> str:
        """Get project URL"""
        return f"/org/{self.organization_slug}/projects/{self.key}"

    @property
    @computed_field
    def full_key(self) -> str:
        """Get full project identifier with org"""
        return f"{self.organization_slug}/{self.key}"


class ProjectListItem(BaseModel):
    """Simplified project schema for lists"""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    key: str
    description: Optional[str]

    # Visual
    icon: Optional[str]
    color: Optional[str]

    # Status
    status: ProjectStatus
    priority: ProjectPriority
    visibility: ProjectVisibility

    # Dates
    due_date: Optional[datetime]

    # Lead
    lead_name: Optional[str] = Field(None, alias="lead.full_name")

    # Metadata
    created_at: datetime
    updated_at: datetime

    @property
    @computed_field
    def display_icon(self) -> str:
        """Get display icon with fallback"""
        if self.icon:
            return self.icon
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
    @computed_field
    def display_color(self) -> str:
        """Get display color with fallback"""
        if self.color:
            return self.color
        priority_colors = {
            ProjectPriority.LOW: "#10B981",
            ProjectPriority.MEDIUM: "#F59E0B",
            ProjectPriority.HIGH: "#EF4444",
            ProjectPriority.CRITICAL: "#7C2D12",
        }
        return priority_colors.get(self.priority, "#6B7280")


class ProjectStats(BaseModel):
    """Project statistics for dashboard"""

    total_projects: int
    active_projects: int
    completed_projects: int
    overdue_projects: int
    projects_by_status: Dict[ProjectStatus, int]
    projects_by_priority: Dict[ProjectPriority, int]
    avg_completion_time_days: Optional[float]


class ProjectStatusUpdate(BaseModel):
    """Schema for updating project status"""

    status: ProjectStatus = Field(..., description="New project status")
    reason: Optional[str] = Field(None, description="Reason for status change")


__all__ = [
    # Base schemas
    "ProjectBase",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectSettings",
    # Member schemas
    "ProjectMemberInvite",
    "ProjectMemberUpdate",
    "ProjectMemberResponse",
    # Response schemas
    "ProjectResponse",
    "ProjectListItem",
    "ProjectStats",
    # Action schemas
    "ProjectStatusUpdate",
]
