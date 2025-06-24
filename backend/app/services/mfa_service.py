import secrets
import qrcode
import io
import base64
import logging
from datetime import datetime, UTC, timedelta
from typing import List, Optional
from uuid import UUID

import pyotp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from passlib.context import CryptContext

from app.core.config import settings
from app.models.user import User
from app.models.mfa_backup_code import MFABackupCode
from app.schemas.auth import (
    MFAVerifyRequest,
    MFASetupRequest,
    MFASetupResponse,
    MFADisableRequest,
    MFABackupCodesInfo,
)
from app.core.security import PasswordManager
from app.core.exceptions import (
    AuthenticationException,
    ValidationException,
    NotFoundException,
)
from app.db.redis_client import redis_client

logger = logging.getLogger(__name__)

backup_code_context = CryptContext(
    schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=8
)


class MFAService:
    """Multi-Factor Authentication service with TOTP and persistent backup codes"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.password_manager = PasswordManager()

    async def setup_mfa(
        self, user_id: UUID, setup_data: MFASetupRequest
    ) -> MFASetupResponse:
        """
        Setup MFA for a user by generating TOTP secret and backup codes.

        :param user_id: UUID of the user setting up MFA
        :param setup_data: MFA setup request containing current password
        :return: MFASetupResponse with secret, QR code, and backup codes
        """
        user = await self._get_user_and_verify_password(user_id, setup_data.password)

        secret = pyotp.random_base32()

        backup_codes = self._generate_backup_codes()

        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=str(user.email), issuer_name=settings.APP_NAME
        )

        qr_code_url = self._generate_qr_code(provisioning_uri)

        # Store temporary data in Redis
        temp_data = {
            "secret": secret,
            "backup_codes": backup_codes,
            "setup_timestamp": datetime.now(UTC).isoformat(),
        }

        await redis_client.set(f"mfa_setup:{user_id}", temp_data, expire=60 * 10)

        return MFASetupResponse(
            secret=secret, qr_code_url=qr_code_url, backup_codes=backup_codes
        )

    async def verify_and_enable_mfa(
        self, user_id: UUID, verify_data: MFAVerifyRequest
    ) -> bool:
        """
        Verify TOTP code and enable MFA for the user.

        :param user_id: UUID of the user
        :param verify_data: MFA verification request with TOTP code
        :return: True if MFA was successfully enabled
        """
        temp_data = await redis_client.get(f"mfa_setup:{user_id}")
        if not temp_data:
            raise ValidationException("MFA setup session expired")

        secret = temp_data.get("secret")
        backup_codes = temp_data.get("backup_codes")
        if not secret or not backup_codes:
            raise ValidationException("MFA setup data not found")

        if not self._verify_totp_code(secret, verify_data.code):
            raise ValidationException("Invalid TOTP code")

        try:
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(
                    mfa_enabled=True, mfa_secret=secret, updated_at=datetime.now(UTC)
                )
            )
            await self.db.execute(stmt)

            await self._store_backup_codes(user_id, backup_codes)
            await self.db.commit()

            await redis_client.delete(f"mfa_setup:{user_id}")

            await self.db.get(User, user_id)

            return True
        except Exception as e:
            await self.db.rollback()
            raise ValidationException(f"Failed to enable MFA: {str(e)}")

    async def verify_mfa_code(
        self,
        user_id: UUID,
        code: str,
        ip_address: Optional[str] = None,
        check_backup: bool = True,
    ) -> bool:
        """
        Verify MFA code (TOTP or backup code) for a user.
        :param user_id: UUID of the user
        :param code: 6-digit TOTP code or backup code
        :param ip_address: IP address for logging purposes
        :param check_backup: Whether to check backup codes if TOTP verification fails
        :return: True if the code is valid, False otherwise
        """
        user = await self.db.get(User, user_id)
        if not user or not user.mfa_enabled or not user.mfa_secret:
            raise NotFoundException("User not found or MFA not enabled")

        if self._verify_totp_code(str(user.mfa_secret), code):
            return True

        if check_backup:
            if await self._verify_backup_code(user_id, code, ip_address):
                return True

        return False

    async def disable_mfa(self, user_id: UUID, disable_data: MFADisableRequest) -> bool:
        """
        Disable MFA for a user.
        :param user_id: UUID of the user
        :param disable_data: MFADisableRequest containing current password and optional TOTP code
        :return: True if MFA was successfully disabled
        """
        user = await self._get_user_and_verify_password(user_id, disable_data.password)

        if not user.mfa_enabled:
            raise ValidationException("MFA is not enabled for this user")

        if not await self.verify_mfa_code(user_id, disable_data.code):
            if not await self._verify_backup_code(user_id, disable_data.code):
                raise ValidationException("Invalid MFA code")

        try:
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(
                    mfa_enabled=False, mfa_secret=None, updated_at=datetime.now(UTC)
                )
            )
            await self.db.execute(stmt)

            delete_stmt = delete(MFABackupCode).where(MFABackupCode.user_id == user_id)
            await self.db.execute(delete_stmt)

            await self.db.commit()

            return True
        except Exception as e:
            await self.db.rollback()
            raise ValidationException(f"Failed to disable MFA: {str(e)}")

    async def generate_backup_codes(self, user_id: UUID, password: str) -> List[str]:
        """
        Generate new backup codes for a user.
        :param user_id: UUID of the user
        :param password: Current password for verification
        :return: List of new backup codes
        """
        user = await self._get_user_and_verify_password(user_id, password)

        if not user.mfa_enabled or not user.mfa_secret:
            raise ValidationException("MFA is not enabled for this user")

        backup_codes = self._generate_backup_codes()

        try:
            delete_stmt = delete(MFABackupCode).where(MFABackupCode.user_id == user_id)
            await self.db.execute(delete_stmt)

            await self._store_backup_codes(user_id, backup_codes)
            await self.db.commit()

            return backup_codes
        except Exception as e:
            await self.db.rollback()
            raise ValidationException(f"Failed to generate backup codes: {str(e)}")

    async def get_backup_codes_info(
        self, user_id: UUID, password: str
    ) -> MFABackupCodesInfo:
        """
        Get backup codes information for a user.
        :param user_id: UUID of the user
        :param password: Current password for verification
        :return: MFABackupCodesInfo containing backup codes and their usage status
        """
        user = await self._get_user_and_verify_password(user_id, password)

        if not user.mfa_enabled or not user.mfa_secret:
            raise ValidationException("MFA is not enabled for this user")

        stmt = select(MFABackupCode).where(MFABackupCode.user_id == user_id)
        result = await self.db.execute(stmt)
        backup_codes = result.scalars().all()

        total_codes = len(backup_codes)
        used_codes = len([code for code in backup_codes if code.is_used])
        remaining_codes = total_codes - used_codes

        return MFABackupCodesInfo(
            total_codes=total_codes,
            used_codes=used_codes,
            remaining_codes=remaining_codes,
            last_generated=backup_codes[0].generated_at if backup_codes else None,
        )

    async def _get_user_and_verify_password(
        self, user_id: UUID, password: str
    ) -> type[User]:
        """
        Retrieve user by ID and verify their password.
        :param user_id: UUID of the user
        :param password: Current password for verification
        :return: User object if found and password is correct
        """
        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundException("User", str(user_id))

        if not user.password_hash or not self.password_manager.verify_password(
            password, str(user.password_hash)
        ):
            raise AuthenticationException("Invalid password")

        return user

    def _generate_backup_codes(self, count: int = 10) -> List[str]:
        """
        Generate a list of secure backup codes.
        :param count: Number of backup codes to generate
        :return: List of backup codes
        """
        codes = []
        for _ in range(count):
            code = "".join(
                secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(8)
            )
            formatted_code = f"{code[:4]}-{code[4:]}"
            codes.append(formatted_code)
        return codes

    def _verify_totp_code(self, secret: str, code: str) -> bool:
        """
        Verify a TOTP code against the user's secret.
        :param secret: TOTP secret key
        :param code: 6-digit TOTP code to verify
        :return: True if the code is valid, False otherwise
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)  # clock skew tolerance of 1 minute

    def _generate_qr_code(self, provisioning_uri: str) -> str:
        """
        Generate a QR code for the TOTP provisioning URI.
        :param provisioning_uri: TOTP provisioning URI
        :return: Base64-encoded QR code image
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        buffered.seek(0)
        return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"

    async def _store_backup_codes(self, user_id: UUID, backup_codes: List[str]) -> None:
        """
        Store backup codes in the database for a user.
        :param user_id: UUID of the user
        :param backup_codes: List of backup codes to store
        """
        for code in backup_codes:
            hashed_code = backup_code_context.hash(code)
            backup_code = MFABackupCode(
                user_id=user_id,
                code_hash=hashed_code,
                generated_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(days=365),
            )
            self.db.add(backup_code)

        # Do not commit here, let the caller handle it

    async def _verify_backup_code(
        self, user_id: UUID, code: str, ip_address: Optional[str] = None
    ) -> bool:
        """
        Verify a backup code for a user.
        :param user_id: UUID of the user
        :param code: Backup code to verify
        :param ip_address: IP address for logging purposes
        :return: True if the backup code is valid and not used, False otherwise
        """
        stmt = select(MFABackupCode).where(
            MFABackupCode.user_id == user_id,
            MFABackupCode.is_used == False,  # noqa: E712
            MFABackupCode.expires_at > datetime.now(UTC),
        )
        result = await self.db.execute(stmt)
        backup_codes = result.scalars().all()

        for backup_code in backup_codes:
            if backup_code_context.verify(code, backup_code.code_hash):
                backup_code.mark_as_used(ip_address)
                await self.db.commit()

                return True
        return False
