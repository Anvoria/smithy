from datetime import datetime, UTC
from typing import Optional
from enum import Enum

from sqlalchemy import String, Boolean, DateTime, Text, Integer, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserStatus(str, Enum):
    """
    User account status
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    ARCHIVED = "archived"


class UserRole(str, Enum):
    """User roles for RBAC"""

    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    GUEST = "guest"


class LoginProvider(str, Enum):
    """Authentication providers"""

    LOCAL = "local"


class User(Base):
    """
    User model representing application users.
    Contains fields for user information, authentication, and roles.
    """

    # Basic user information
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User's email address",
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="User's username",
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        comment="Hashed password for authentication (null if using external auth)",
    )

    login_provider: Mapped[LoginProvider] = mapped_column(
        String(50),
        default=LoginProvider.LOCAL,
        nullable=False,
        comment="Authentication provider used for login",
    )

    # Personal information
    first_name: Mapped[Optional[str]] = mapped_column(
        String(191),
        nullable=True,
        comment="User's first name",
    )

    last_name: Mapped[Optional[str]] = mapped_column(
        String(191),
        nullable=True,
        comment="User's last name",
    )

    display_name: Mapped[Optional[str]] = mapped_column(
        String(191),
        nullable=True,
        comment="User's display name (if different from username)",
    )

    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Short biography or description of the user",
    )

    # Other information
    timezone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="User's preferred timezone in IANA format",
    )

    locale: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="User's preferred locale (e.g., en-US)",
    )

    # Account status and roles
    status: Mapped[UserStatus] = mapped_column(
        String(20),
        default=UserStatus.ACTIVE,
        nullable=False,
        comment="Current status of the user account",
    )

    role: Mapped[UserRole] = mapped_column(
        String(20),
        default=UserRole.USER,
        nullable=False,
        comment="Role of the user for access control",
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indicates if the user's email is verified",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indicates if the user account is active",
    )

    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indicates if the user has superuser privileges",
    )

    # Security fields
    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indicates if multi-factor authentication is enabled",
    )

    mfa_secret: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="TOTP secret for MFA"
    )

    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="Consecutive failed login attempts"
    )

    # OAuth and external accounts
    oauth_accounts: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="Connected OAuth accounts data"
    )

    external_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True, comment="External system user ID"
    )

    # Activity tracking
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful login timestamp",
    )

    last_activity_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Last activity timestamp",
    )

    login_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="Total login count"
    )

    # Verification & Recovery
    email_verification_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True, comment="Email verification token"
    )

    email_verification_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Email verification token expiration",
    )

    password_reset_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True, comment="Password reset token"
    )

    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Password reset token expiration",
    )

    # Database Constraints
    __table_args__ = (
        # Indexes for performance
        Index("idx_user_email_status", "email", "status"),
        Index("idx_user_last_activity", "last_activity_at"),
        Index("idx_user_created_status", "created_at", "status"),
        Index("idx_user_role_status", "role", "status"),
        # Check constraints
        CheckConstraint(
            r"email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'",
            name="valid_email_format",
        ),
        CheckConstraint("login_count >= 0", name="non_negative_login_count"),
        CheckConstraint(
            "LENGTH(username) >= 3 OR username IS NULL", name="username_min_length"
        ),
    )

    # Properties for common operations
    @property
    def full_name(self) -> Optional[str]:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name

    @property
    def public_name(self) -> str:
        """Get public display name with fallbacks"""
        return (
            self.display_name
            or self.full_name
            or self.username
            or self.email.split("@")[0]
        )

    @property
    def is_email_verification_expired(self) -> bool:
        """Check if email verification token is expired"""
        if not self.email_verification_expires:
            return True
        return datetime.now(UTC) > self.email_verification_expires

    @property
    def is_password_reset_expired(self) -> bool:
        """Check if password reset token is expired"""
        if not self.password_reset_expires:
            return True
        return datetime.now(UTC) > self.password_reset_expires

    def __repr__(self) -> str:
        return f"<User(email={self.email}, status={self.status}, role={self.role})>"
