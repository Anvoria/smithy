import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Annotated

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

from app.models.user import UserStatus, UserRole, LoginProvider
from app.core.security import PasswordManager


# ==========================================
# Base Schemas
# ==========================================


class UserBase(BaseModel):
    """Base user schema with common fields"""

    email: EmailStr = Field(..., description="User email address")
    username: Annotated[
        Optional[str],
        Field(default=None, min_length=3, max_length=50, description="Unique username"),
    ]
    first_name: Annotated[
        Optional[str], Field(default=None, max_length=191, description="First name")
    ]
    last_name: Annotated[
        Optional[str], Field(default=None, max_length=191, description="Last name")
    ]
    display_name: Annotated[
        Optional[str], Field(default=None, max_length=191, description="Display name")
    ]
    bio: Optional[str] = Field(None, description="User biography")
    timezone: Optional[str] = Field("UTC", description="User timezone")
    locale: Optional[str] = Field("en_US", description="User locale")


# ==========================================
# Request Schemas
# ==========================================


class UserCreate(UserBase):
    """Schema for creating a new user"""

    password: Annotated[
        Optional[str],
        Field(default=None, min_length=8, max_length=100, description="User password"),
    ]
    login_provider: LoginProvider = Field(
        LoginProvider.LOCAL, description="Authentication provider"
    )
    external_id: Optional[str] = Field(None, description="External provider user ID")
    oauth_data: Optional[Dict[str, Any]] = Field(None, description="OAuth account data")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: Optional[str], info) -> Optional[str]:
        """Validate password requirements"""
        if not v:
            login_provider = info.data.get("login_provider", LoginProvider.LOCAL)
            if login_provider == LoginProvider.LOCAL:
                raise ValueError("Password is required for local authentication")
            return v

        # Password strength validation
        is_password_strong = PasswordManager.validate_password_strength(v)
        if not is_password_strong:
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, one digit, and one special character"
            )
        return v


class UserUpdate(BaseModel):
    """Schema for updating user information"""

    username: Annotated[
        Optional[str],
        Field(default=None, min_length=3, max_length=50, description="Unique username"),
    ]
    first_name: Annotated[
        Optional[str], Field(default=None, max_length=191, description="First name")
    ]
    last_name: Annotated[
        Optional[str], Field(default=None, max_length=191, description="Last name")
    ]
    display_name: Annotated[
        Optional[str], Field(default=None, max_length=191, description="Display name")
    ]
    bio: Optional[str] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None


class UserPasswordUpdate(BaseModel):
    """Schema for password updates"""

    current_password: str = Field(..., description="Current password")
    new_password: Annotated[
        str, Field(min_length=8, max_length=100, description="New password")
    ]

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password requirements"""
        is_password_strong = PasswordManager.validate_password_strength(v)
        if not is_password_strong:
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, one digit, and one special character"
            )
        return v


class UserEmailUpdate(BaseModel):
    """Schema for email updates"""

    new_email: EmailStr = Field(..., description="New email address")
    password: str = Field(..., description="Current password for verification")


class UserRoleUpdate(BaseModel):
    """Schema for admin role updates"""

    role: UserRole = Field(..., description="New user role")
    reason: Optional[str] = Field(None, description="Reason for role change")


class UserStatusUpdate(BaseModel):
    """Schema for admin status updates"""

    status: UserStatus = Field(..., description="New user status")
    reason: Optional[str] = Field(None, description="Reason for status change")


# ==========================================
# Response Schemas
# ==========================================


class UserPublic(BaseModel):
    """Public user information"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: Optional[str]
    display_name: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    created_at: datetime
    public_name: str


class UserProfile(UserPublic):
    """Extended user profile (for authenticated users viewing their own profile)"""

    email: EmailStr
    first_name: Optional[str]
    last_name: Optional[str]
    timezone: Optional[str]
    locale: Optional[str]
    is_verified: bool
    status: UserStatus
    role: UserRole
    mfa_enabled: bool
    login_provider: LoginProvider
    full_name: Optional[str]
    created_at: datetime
    updated_at: datetime


class UserAdmin(UserProfile):
    """Admin view of user (includes sensitive information)"""

    is_active: bool
    is_superuser: bool
    email_verification_expires: Optional[datetime]
    password_reset_expires: Optional[datetime]
    external_id: Optional[str]
    oauth_accounts: Optional[Dict[str, Any]]


class UserList(BaseModel):
    """User list response for pagination"""

    users: list[UserPublic]
    total: int
    page: int
    size: int
    pages: int


class UserListAdmin(BaseModel):
    """Admin user list response"""

    users: list[UserAdmin]
    total: int
    page: int
    size: int
    pages: int


# ==========================================
# Statistics & Analytics Schemas
# ==========================================


class UserStats(BaseModel):
    """User statistics for admin dashboard"""

    total_users: int
    active_users: int
    verified_users: int
    users_by_status: Dict[UserStatus, int]
    users_by_role: Dict[UserRole, int]
    users_by_provider: Dict[LoginProvider, int]


class UserActivity(BaseModel):
    """User activity information"""

    user_id: uuid.UUID
    last_login_at: Optional[datetime]
    last_activity_at: Optional[datetime]
    login_count: int
    is_online: bool


# ==========================================
# Verification & Security Schemas
# ==========================================


class EmailVerificationRequest(BaseModel):
    """Request email verification"""

    email: EmailStr = Field(..., description="Email to verify")


class EmailVerificationConfirm(BaseModel):
    """Confirm email verification"""

    token: str = Field(..., description="Verification token")


class PasswordResetRequest(BaseModel):
    """Request password reset"""

    email: EmailStr = Field(..., description="User email")


class PasswordResetConfirm(BaseModel):
    """Confirm password reset"""

    token: str = Field(..., description="Reset token")
    new_password: Annotated[
        str, Field(min_length=8, max_length=100, description="New password")
    ]

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password requirements"""
        is_password_strong = PasswordManager.validate_password_strength(v)
        if not is_password_strong:
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, one digit, and one special character"
            )
        return v


# ==========================================
# MFA Schemas
# ==========================================


class MFASetupRequest(BaseModel):
    """MFA setup initiation"""

    password: str = Field(..., description="Current password for verification")


class MFASetupResponse(BaseModel):
    """MFA setup response"""

    secret: str = Field(..., description="TOTP secret")
    qr_code_url: str = Field(..., description="QR code URL")
    backup_codes: list[str] = Field(..., description="Backup codes")


class MFAVerifyRequest(BaseModel):
    """MFA verification"""

    code: Annotated[
        str, Field(min_length=6, max_length=6, description="6-digit TOTP code")
    ]


class MFADisableRequest(BaseModel):
    """Disable MFA"""

    password: str = Field(..., description="Current password")
    code: Annotated[
        Optional[str],
        Field(
            default=None, min_length=6, max_length=6, description="6-digit TOTP code"
        ),
    ]


# ==========================================
# Export all schemas
# ==========================================

__all__ = [
    # Base
    "UserBase",
    # Request schemas
    "UserCreate",
    "UserUpdate",
    "UserPasswordUpdate",
    "UserEmailUpdate",
    "UserRoleUpdate",
    "UserStatusUpdate",
    # Response schemas
    "UserPublic",
    "UserProfile",
    "UserAdmin",
    "UserList",
    "UserListAdmin",
    # Statistics
    "UserStats",
    "UserActivity",
    # Verification
    "EmailVerificationRequest",
    "EmailVerificationConfirm",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    # MFA
    "MFASetupRequest",
    "MFASetupResponse",
    "MFAVerifyRequest",
    "MFADisableRequest",
]
