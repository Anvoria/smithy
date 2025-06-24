import uuid
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MFABackupCode(Base):
    """
    MFA backup codes for users with 2FA enabled.
    """

    __tablename__ = "mfa_backup_codes"

    # User relationship
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who owns this backup code",
    )

    code_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Hashed backup code"
    )

    # Usage tracking
    is_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this backup code has been used",
    )

    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When this backup code was used"
    )

    used_from_ip: Mapped[Optional[str]] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
        comment="IP address from which the code was used",
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        comment="When this backup code was generated",
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this backup code expires (optional)",
    )

    # Relationships
    user = relationship("User", back_populates="mfa_backup_codes")

    __table_args__ = (
        Index("idx_mfa_backup_user_active", "user_id", "is_used"),
        Index("idx_mfa_backup_expires", "expires_at"),
        Index("idx_mfa_backup_generated", "generated_at"),
    )

    @property
    def is_expired(self) -> bool:
        """Check if backup code is expired"""
        if not self.expires_at:
            return False
        return datetime.now(UTC) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if backup code is valid (not used and not expired)"""
        return not self.is_used and not self.is_expired

    def mark_as_used(self, ip_address: Optional[str] = None) -> None:
        """Mark backup code as used"""
        self.is_used = True
        self.used_at = datetime.now(UTC)
        self.used_from_ip = ip_address

    def __repr__(self) -> str:
        return f"<MFABackupCode(user_id={self.user_id}, used={self.is_used})>"
