from datetime import datetime
from typing import Optional, Annotated

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.user import UserRole


class LoginRequest(BaseModel):
    """User login request"""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")
    mfa_code: Optional[str] = Field(
        None, min_length=6, max_length=8, description="MFA code (TOTP or backup code)"
    )
    remember_me: bool = Field(False, description="Remember login session")


class MFALoginRequest(BaseModel):
    """Complete MFA authentication request"""

    partial_auth_token: str = Field(
        ..., description="Partial authentication token from initial login"
    )
    mfa_code: str = Field(
        ..., min_length=6, max_length=8, description="MFA code (TOTP or backup code)"
    )


class TokenResponse(BaseModel):
    """Token response after successful authentication"""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    user: dict = Field(..., description="User information")


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""

    refresh_token: str = Field(..., description="Valid refresh token")


class LogoutRequest(BaseModel):
    """Logout request"""

    refresh_token: Optional[str] = Field(None, description="Refresh token to revoke")


class RegisterRequest(BaseModel):
    """User registration request"""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="User password")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    username: Optional[str] = Field(
        None, min_length=3, max_length=50, description="Username"
    )

    @model_validator(mode="before")
    @classmethod
    def set_username_if_missing(cls, data):
        print("Setting username if missing")
        if not data.get("username") and data.get("email"):
            data["username"] = data["email"].split("@")[0]
        return data


class AuthUser(BaseModel):
    """Authenticated user information"""

    id: str
    email: str
    username: Optional[str]
    role: UserRole
    is_superuser: bool
    is_verified: bool
    is_active: bool
    full_name: Optional[str]
    avatar_url: Optional[str]


class MFARequiredResponse(BaseModel):
    """Response indicating MFA is required"""

    message: str = Field(
        "Multi-factor authentication is required", description="MFA requirement message"
    )
    requires_mfa: bool = Field(
        True, description="Indicates that MFA is required for this action"
    )
    partial_auth_token: Optional[str] = Field(
        None, description="Partial authentication token for MFA completion"
    )


class MFAVerifyRequest(BaseModel):
    """MFA verification"""

    code: Annotated[
        str, Field(min_length=6, max_length=6, description="6-digit TOTP code")
    ]


class MFASetupRequest(BaseModel):
    """MFA setup initiation"""

    password: str = Field(..., description="Current password for verification")


class MFASetupResponse(BaseModel):
    """MFA setup response"""

    secret: str = Field(..., description="TOTP secret")
    qr_code_url: str = Field(..., description="QR code URL")
    backup_codes: list[str] = Field(..., description="Backup codes")


class MFADisableRequest(BaseModel):
    """Disable MFA"""

    password: str = Field(..., description="Current password")
    code: str = Field(..., description="Current MFA code for verification")


class MFABackupCodesInfo(BaseModel):
    """MFA backup codes information"""

    total_codes: int = Field(default=10, description="Total number of backup codes")
    used_codes: int = Field(default=0, description="Number of used backup codes")
    remaining_codes: int = Field(
        default=10, description="Number of remaining backup codes"
    )
    last_generated: Optional[datetime] = Field(
        default=None, description="Timestamp when backup codes were last generated"
    )


# ==========================================
# Export all schemas
# ==========================================

__all__ = [
    "LoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "LogoutRequest",
    "RegisterRequest",
    "AuthUser",
    "MFARequiredResponse",
    "MFAVerifyRequest",
    "MFASetupRequest",
    "MFASetupResponse",
    "MFADisableRequest",
    "MFABackupCodesInfo",
    "MFALoginRequest",
]
