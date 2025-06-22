import uuid
from datetime import datetime
from typing import Optional, Dict, Annotated

from pydantic import BaseModel, Field, field_validator, EmailStr, computed_field

from app.models.organization import OrganizationType, OrganizationSize
from app.models.organization_member import OrganizationRole, MemberStatus


class OrganizationSettings(BaseModel):
    """Organization settings schema"""

    # General settings
    default_project_visibility: str = "organization"
    allow_member_project_creation: bool = True
    require_project_approval: bool = False

    # # Integration settings
    # webhook_events: List[str] = []
    # api_access_enabled: bool = False


class OrganizationFeatures(BaseModel):
    """Organization features schema"""

    # Analytics features
    advanced_reporting: bool = False
    export_data: bool = True
    api_access: bool = False


class OrganizationBase(BaseModel):
    """Base organization schema with common fields"""

    name: Annotated[
        str, Field(min_length=1, max_length=200, description="Organization name")
    ]
    slug: Annotated[
        str, Field(min_length=2, max_length=50, description="URL-friendly identifier")
    ]
    display_name: Annotated[
        Optional[str],
        Field(default=None, max_length=250, description="Public display name"),
    ]
    description: Optional[str] = Field(None, description="Organization description")
    website_url: Optional[str] = Field(None, description="Organization website")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email address")
    timezone: Optional[str] = Field("UTC", description="Organization timezone")
    brand_color: Optional[str] = Field(None, description="Brand color (hex)")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug format"""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Slug can only contain letters, numbers, hyphens, and underscores"
            )
        return v.lower()

    @field_validator("brand_color")
    @classmethod
    def validate_brand_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate hex color format"""
        if v is None:
            return v
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Brand color must be in #RRGGBB format")
        try:
            int(v[1:], 16)
        except ValueError:
            raise ValueError("Invalid hex color format")
        return v.upper()


class OrganizationCreate(OrganizationBase):
    """Schema for creating a new organization"""

    org_type: OrganizationType = Field(
        OrganizationType.STARTUP, description="Organization type"
    )
    company_size: OrganizationSize = Field(
        OrganizationSize.SMALL,
        description="Size of the organization (e.g., small, medium, large)",
    )

    # Limits and quotas
    max_members: int = Field(5, ge=1, le=1000, description="Maximum number of members")
    max_projects: int = Field(3, ge=1, le=100, description="Maximum number of projects")
    max_storage_gb: int = Field(1, ge=1, le=100, description="Maximum storage in GB")

    # Configuration
    settings: Optional[OrganizationSettings] = Field(
        None, description="Organization settings"
    )
    features: Optional[OrganizationFeatures] = Field(
        None, description="Enabled features"
    )


class OrganizationUpdate(BaseModel):
    """Schema for updating organization information"""

    name: Annotated[
        Optional[str], Field(default=None, min_length=1, max_length=200)
    ] = None
    slug: Annotated[Optional[str], Field(default=None, min_length=2, max_length=50)] = (
        None
    )
    display_name: Annotated[Optional[str], Field(default=None, max_length=250)] = None
    description: Optional[str] = None
    website_url: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    timezone: Optional[str] = None
    brand_color: Optional[str] = None
    org_type: Optional[OrganizationType] = None
    company_size: Optional[OrganizationSize] = None

    # Configuration updates
    settings: Optional[OrganizationSettings] = None
    features: Optional[OrganizationFeatures] = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        """Validate slug format"""
        if v is None:
            return v
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Slug can only contain letters, numbers, hyphens, and underscores"
            )
        return v.lower()

    @field_validator("brand_color")
    @classmethod
    def validate_brand_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate hex color format"""
        if v is None:
            return v
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Brand color must be in #RRGGBB format")
        try:
            int(v[1:], 16)
        except ValueError:
            raise ValueError("Invalid hex color format")
        return v.upper()


class MemberInvite(BaseModel):
    """Schema for inviting a member to organization"""

    email: EmailStr = Field(..., description="Email of user to invite")
    role: OrganizationRole = Field(
        OrganizationRole.MEMBER, description="Role to assign to the member"
    )


class MemberUpdate(BaseModel):
    """Schema for updating member role"""

    role: OrganizationRole = Field(..., description="New role for the member")


class MemberResponse(BaseModel):
    """Organization member response schema"""

    model_config = {"from_attributes": True}

    user_id: uuid.UUID
    role: OrganizationRole
    status: MemberStatus
    invited_at: Optional[datetime]
    joined_at: Optional[datetime]

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

    @property
    def is_active(self) -> bool:
        """Check if member is active"""
        return self.status == MemberStatus.ACTIVE

    @property
    def can_manage_members(self) -> bool:
        """Check if member can manage other members"""
        return self.role in [OrganizationRole.OWNER, OrganizationRole.ADMIN]


class OrganizationResponse(BaseModel):
    """Complete organization response schema"""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    slug: str
    display_name: Optional[str]
    description: Optional[str]

    # Contact & branding
    website_url: Optional[str]
    contact_email: Optional[str]
    timezone: Optional[str]
    brand_color: Optional[str]
    logo_url: Optional[str]
    avatar_url: Optional[str]
    banner_url: Optional[str]

    # Classification
    org_type: OrganizationType
    company_size: OrganizationSize

    # Limits and quotas
    max_members: int
    max_projects: int
    max_storage_gb: int  # TODO: https://github.com/Anvoria/smithy-backend/issues/5

    # Configuration
    settings: Optional[OrganizationSettings] = None
    features: Optional[OrganizationFeatures] = None

    # Security settings
    require_2fa: bool
    public_projects: bool

    # Metadata
    created_at: datetime
    updated_at: datetime

    @property
    @computed_field
    def current_members(self) -> int:
        """Safe member count"""
        return getattr(self, "_current_members", 0)

    @property
    @computed_field
    def storage_used_mb(self) -> int:
        """Safe storage calculation"""
        return 0  # TODO: https://github.com/Anvoria/smithy-backend/issues/5

    @property
    @computed_field
    def current_projects(self) -> int:
        """Safe project count"""
        return getattr(self, "_current_projects", 0)

    @property
    @computed_field
    def usage_percentage(self) -> Dict[str, float]:
        """Usage statistics as percentages"""
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
    @computed_field
    def is_over_limits(self) -> Dict[str, bool]:
        """Flags indicating if organization is over any limits"""
        return {
            "members": self.current_members >= self.max_members,
            "projects": self.current_projects >= self.max_projects,
            "storage": self.storage_used_mb >= (self.max_storage_gb * 1024),
        }

    @property
    @computed_field
    def display_avatar_url(self) -> Optional[str]:
        """URL for display avatar with fallbacks"""
        return self.avatar_url or self.logo_url

    @property
    @computed_field
    def public_url(self) -> str:
        """Public URL for the organization"""
        return f"/org/{self.slug}"

    @classmethod
    def from_organization(
        cls, org, current_members: int = 0, current_projects: int = 0
    ):
        """Create response with calculated values"""
        data = {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "display_name": org.display_name,
            "description": org.description,
            "website_url": org.website_url,
            "contact_email": org.contact_email,
            "timezone": org.timezone,
            "brand_color": org.brand_color,
            "logo_url": org.logo_url,
            "avatar_url": org.avatar_url,
            "banner_url": org.banner_url,
            "org_type": org.org_type,
            "company_size": org.company_size,
            "max_members": org.max_members,
            "max_projects": org.max_projects,
            "max_storage_gb": org.max_storage_gb,
            "settings": org.settings,
            "features": org.features,
            "require_2fa": org.require_2fa,
            "public_projects": org.public_projects,
            "created_at": org.created_at,
            "updated_at": org.updated_at,
            "_current_members": current_members,
            "_current_projects": current_projects,
        }
        return cls(**data)


class OrganizationListItem(BaseModel):
    """Simplified organization schema for lists"""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    slug: str
    display_name: Optional[str]
    description: Optional[str]
    org_type: OrganizationType
    brand_color: Optional[str]
    logo_url: Optional[str]
    avatar_url: Optional[str]

    # Basic stats
    max_members: int
    max_projects: int

    # Metadata
    created_at: datetime
    updated_at: datetime

    @property
    @computed_field
    def display_avatar_url(self) -> Optional[str]:
        """URL for display avatar with fallbacks"""
        return self.avatar_url or self.logo_url

    @classmethod
    def from_organization(
        cls, org, current_members: int = 0, current_projects: int = 0
    ):
        """Create list item with calculated values"""
        return cls(
            id=org.id,
            name=org.name,
            slug=org.slug,
            display_name=org.display_name,
            description=org.description,
            org_type=org.org_type,
            brand_color=org.brand_color,
            logo_url=org.logo_url,
            avatar_url=org.avatar_url,
            max_members=org.max_members,
            max_projects=org.max_projects,
            created_at=org.created_at,
            updated_at=org.updated_at,
        )


class OrganizationStats(BaseModel):
    """Organization statistics for dashboard"""

    total_organizations: int
    active_organizations: int
    organizations_by_type: Dict[OrganizationType, int]
    total_members: int
    avg_members_per_org: float
    total_projects: int
    avg_projects_per_org: float


class InvitationToken(BaseModel):
    """Invitation token for email links"""

    organization_id: uuid.UUID
    email: str
    role: OrganizationRole
    expires_at: datetime


class JoinOrganization(BaseModel):
    """Schema for joining organization via invitation"""

    invitation_token: str = Field(..., description="Invitation token from email")


class LeaveOrganization(BaseModel):
    """Schema for leaving organization"""

    confirm: bool = Field(..., description="Confirmation to leave organization")
    transfer_ownership_to: Optional[uuid.UUID] = Field(
        None, description="User ID to transfer ownership to (if current user is owner)"
    )


__all__ = [
    # Base schemas
    "OrganizationBase",
    "OrganizationCreate",
    "OrganizationUpdate",
    "OrganizationSettings",
    "OrganizationFeatures",
    # Member schemas
    "MemberInvite",
    "MemberUpdate",
    "MemberResponse",
    # Response schemas
    "OrganizationResponse",
    "OrganizationListItem",
    "OrganizationStats",
    # Action schemas
    "InvitationToken",
    "JoinOrganization",
    "LeaveOrganization",
]
