import secrets
import qrcode
import io
import base64
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, UTC, timedelta
from typing import List, Optional, Tuple
from uuid import UUID

import pyotp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
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
    schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=6
)

# Global thread pool for CPU-intensive operations
thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="mfa_")


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
        if user.mfa_enabled:
            raise ValidationException("MFA is already enabled for this user")

        secret = pyotp.random_base32()

        loop = asyncio.get_event_loop()

        backup_codes_task = loop.run_in_executor(
            thread_pool, self._generate_backup_codes, 10
        )

        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=str(user.email), issuer_name=settings.APP_NAME
        )

        qr_code_task = loop.run_in_executor(
            thread_pool, self._generate_qr_code, provisioning_uri
        )

        backup_codes, qr_code_url = await asyncio.gather(
            backup_codes_task, qr_code_task
        )

        # Store temporary data in Redis
        temp_data = {
            "secret": secret,
            "backup_codes": backup_codes,
            "setup_timestamp": datetime.now(UTC).isoformat(),
        }

        await redis_client.set(f"mfa_setup:{user_id}", temp_data, expire=600)

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
        cache_key = f"mfa_user:{user_id}"
        cached_user = await redis_client.get(cache_key)

        if cached_user and isinstance(cached_user, dict):
            user_secret = cached_user.get("mfa_secret")
            if user_secret and self._verify_totp_code(user_secret, code):
                return True
        else:
            user = await self.db.get(User, user_id)
            if not user or not user.mfa_enabled or not user.mfa_secret:
                raise NotFoundException("User not found or MFA not enabled")

            # Cache user data for 5 minutes
            await redis_client.set(
                cache_key,
                {"mfa_secret": user.mfa_secret, "mfa_enabled": True},
                expire=300,
            )

            if self._verify_totp_code(str(user.mfa_secret), code):
                return True

        if check_backup:
            return await self._verify_backup_code(user_id, code, ip_address)

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

            await redis_client.delete(f"mfa_user:{user_id}")

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

        # Generate codes in thread pool
        loop = asyncio.get_event_loop()
        backup_codes = await loop.run_in_executor(
            thread_pool, self._generate_backup_codes, 10
        )

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

        result = await self.db.execute(
            select(
                func.count(MFABackupCode.id).label("total"),
                func.sum(func.cast(MFABackupCode.is_used, func.INTEGER())).label(
                    "used"
                ),
                func.max(MFABackupCode.generated_at).label("last_generated"),
            ).where(MFABackupCode.user_id == user_id)
        )

        row = result.fetchone()
        if row:
            total_codes = row.total or 0
            used_codes = row.used or 0
            last_generated = row.last_generated
        else:
            total_codes = 0
            used_codes = 0
            last_generated = None

        return MFABackupCodesInfo(
            total_codes=total_codes,
            used_codes=used_codes,
            remaining_codes=total_codes - used_codes,
            last_generated=last_generated,
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

        if not user.password_hash:
            raise AuthenticationException("Invalid password")

        # Verify password in thread pool (bcrypt is CPU intensive)
        loop = asyncio.get_event_loop()
        is_valid = await loop.run_in_executor(
            thread_pool,
            self.password_manager.verify_password,
            password,
            str(user.password_hash),
        )

        if not is_valid:
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
        return totp.verify(code, valid_window=1)

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

        async def hash_code(code: str) -> str:
            """Hash single code in thread pool"""
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                thread_pool, backup_code_context.hash, code
            )

        hash_tasks = [hash_code(code) for code in backup_codes]
        hashed_codes = await asyncio.gather(*hash_tasks)

        # Create objects for batch insert
        now = datetime.now(UTC)
        expires = now + timedelta(days=365)

        backup_code_objects = [
            MFABackupCode(
                user_id=user_id,
                code_hash=hashed_code,
                generated_at=now,
                expires_at=expires,
            )
            for hashed_code in hashed_codes
        ]

        # Bulk insert
        self.db.add_all(backup_code_objects)

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
        # Get only a limited number of unused codes
        stmt = (
            select(MFABackupCode)
            .where(
                MFABackupCode.user_id == user_id,
                MFABackupCode.is_used == False,  # noqa: E712
                MFABackupCode.expires_at > datetime.now(UTC),
            )
            .limit(15)
        )

        result = await self.db.execute(stmt)
        backup_codes = result.scalars().all()

        if not backup_codes:
            return False

        loop = asyncio.get_event_loop()

        async def verify_single_code(
            backup_code: MFABackupCode,
        ) -> Tuple[MFABackupCode, bool]:
            """Verify single backup code in thread pool"""
            is_match = await loop.run_in_executor(
                thread_pool,
                lambda: backup_code_context.verify(code, backup_code.code_hash),
            )
            return (backup_code, is_match)

        # Create and run all verification tasks
        verification_tasks = [
            asyncio.create_task(verify_single_code(backup_code))
            for backup_code in backup_codes
        ]

        # Use asyncio.as_completed for early termination
        for completed_task in asyncio.as_completed(verification_tasks):
            try:
                backup_code_obj, is_match = await completed_task

                if is_match:
                    # Found matching code - mark as used
                    backup_code_obj.mark_as_used(ip_address)
                    await self.db.commit()

                    # Cancel remaining tasks to save CPU
                    for task in verification_tasks:
                        if not task.done():
                            task.cancel()

                    return True

            except asyncio.CancelledError:
                continue

        for task in verification_tasks:
            if not task.done():
                task.cancel()

        return False
