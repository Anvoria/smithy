from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class LoginRequest(BaseModel):
    """User login request"""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")
    remember_me: bool = Field(False, description="Remember login session")


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


class AuthUser(BaseModel):
    """Authenticated user information"""

    id: str
    email: str
    username: Optional[str]
    role: UserRole
    is_verified: bool
    is_active: bool
    full_name: Optional[str]
    avatar_url: Optional[str]


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
]
