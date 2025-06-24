import logging
from datetime import datetime, UTC, timedelta
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, or_

from app.models.user import User, UserStatus, UserRole
from app.schemas.user import (
    UserUpdate,
    UserRoleUpdate,
    UserStatusUpdate,
    UserStats,
    UserPasswordUpdateMFA,
    UserEmailUpdateMFA,
)
from app.core.security import PasswordManager, VerificationTokenManager
from app.core.exceptions import (
    NotFoundException,
    ConflictError,
    ValidationException,
    ForbiddenException,
    AuthenticationException,
)
from app.services.mfa_service import MFAService

logger = logging.getLogger(__name__)


class UserService:
    """User management service with CRUD operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.password_manager = PasswordManager()
        self.verification_manager = VerificationTokenManager()

    async def get_user_by_id(self, user_id: UUID) -> User:
        """
        Retrieve a user by their ID.
        :param user_id: UUID of the user to retrieve.
        :return: User object if found.
        """
        stmt = select(User).where(User.id == user_id)

        user = await self.db.scalar(stmt)
        if not user:
            raise NotFoundException("User", str(user_id))

        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by their email.
        :param email: Email of the user to retrieve.
        :return: User object if found, otherwise None.
        """
        stmt = select(User).where(User.email == email)

        return await self.db.scalar(stmt)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Retrieve a user by their username.
        :param username: Username of the user to retrieve.
        :return: User object if found, otherwise None.
        """
        stmt = select(User).where(User.username == username)

        return await self.db.scalar(stmt)

    async def update_user_profile(
        self,
        user_id: UUID,
        profile_data: UserUpdate,
    ) -> User:
        """
        Update user profile information.
        :param user_id: UUID of the user to update.
        :param profile_data: UserUpdate schema containing the new profile data.
        :return: Updated User object.
        """
        user = await self.get_user_by_id(user_id)

        # Check is username is already taken
        if profile_data.username and profile_data.username != user.username:
            existing_user = await self.get_user_by_username(profile_data.username)
            if existing_user and existing_user.id != user_id:
                raise ConflictError("Username already taken")

        # Update fields
        update_values = {}
        for field, value in profile_data.model_dump(exclude_unset=True).items():
            if hasattr(user, field):
                update_values[field] = value

        if update_values:
            update_values["updated_at"] = datetime.now(UTC)

            stmt = update(User).where(User.id == user_id).values(**update_values)
            await self.db.execute(stmt)
            await self.db.commit()
            await self.db.refresh(user)

        return user

    async def change_user_password(
        self,
        user_id: UUID,
        password_data: UserPasswordUpdateMFA,
        ip_address: Optional[str] = None,
    ) -> bool:
        """
        Change the password for a user.
        :param user_id: UUID of the user whose password is to be changed.
        :param password_data: UserPasswordUpdateMFA schema containing the current password, new password, and optional MFA code.
        :param ip_address: Optional IP address for MFA verification.
        :return: True if password was changed successfully, otherwise raises an exception.
        """
        user = await self.get_user_by_id(user_id)

        # Verify current password
        if not user.password_hash or not self.password_manager.verify_password(
            password_data.current_password, user.password_hash
        ):
            raise AuthenticationException("Current password is incorrect")

        if user.mfa_enabled:
            if not password_data.mfa_code:
                raise AuthenticationException("MFA code required for password change")

            mfa_service = MFAService(self.db)

            if not await mfa_service.verify_mfa_code(
                user_id, password_data.mfa_code, ip_address
            ):
                raise AuthenticationException("Invalid MFA code")

        # Hash new password
        new_password_hash = self.password_manager.hash_password(
            password_data.new_password
        )

        # Update password
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                password_hash=new_password_hash,
                updated_at=datetime.now(UTC),
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()

        return True

    async def change_user_email(
        self,
        user_id: UUID,
        email_data: UserEmailUpdateMFA,
        ip_address: Optional[str] = None,
    ) -> User:
        """
        Change the email address for a user.
        :param user_id: UUID of the user whose email is to be changed.
        :param email_data: UserEmailUpdateMFA schema containing the new email, current password, and optional MFA code.
        :param ip_address: Optional IP address for MFA verification.
        :return: Updated User object with new email.
        """
        user = await self.get_user_by_id(user_id)

        # Verify current password
        if not user.password_hash or not self.password_manager.verify_password(
            email_data.password, user.password_hash
        ):
            raise AuthenticationException("Current password is incorrect")

        if user.mfa_enabled:
            if not email_data.mfa_code:
                raise AuthenticationException("MFA code required for email change")

            mfa_service = MFAService(self.db)

            if not await mfa_service.verify_mfa_code(
                user_id, email_data.mfa_code, ip_address
            ):
                raise AuthenticationException("Invalid MFA code")

        # Check if new email is already taken
        existing_user = await self.get_user_by_email(str(email_data.new_email))
        if existing_user and existing_user.id != user_id:
            raise ConflictError("Email already in use")

        # Update email
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                email=email_data.new_email,
                is_verified=False,
                email_verification_token=self.verification_manager.generate_verification_token(),
                email_verification_expires=datetime.now(UTC) + timedelta(hours=24),
                updated_at=datetime.now(UTC),
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def get_users_list(
        self,
        page: int = 1,
        size: int = 20,
        search: Optional[str] = None,
        status: Optional[UserStatus] = None,
        role: Optional[UserRole] = None,
        is_verified: Optional[bool] = None,
    ) -> Tuple[List[User], int]:
        """
        Retrieve a paginated list of users with optional filters.
        :param page: Page number for pagination.
        :param size: Number of users per page.
        :param search: Search term to filter users by email, username, first name, or last name.
        :param status: Filter users by their status (e.g., active, suspended).
        :param role: Filter users by their role (e.g., admin, user).
        :param is_verified: Filter users by verification status (True/False).
        :return: Tuple containing a list of User objects and the total count of users.
        """
        stmt = select(User)

        # Filters
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    User.email.ilike(search_term),
                    User.username.ilike(search_term),
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                )
            )

        if status:
            stmt = stmt.where(User.status == status)

        if role:
            stmt = stmt.where(User.role == role)

        if is_verified is not None:
            stmt = stmt.where(User.is_verified == is_verified)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt)

        # Paginate
        offset = (page - 1) * size
        stmt = stmt.offset(offset).limit(size).order_by(User.created_at.desc())

        result = await self.db.execute(stmt)
        users = result.scalars().all()

        return list(users), total or 0

    async def update_user_role(
        self, user_id: UUID, role_data: UserRoleUpdate, admin_user_id: UUID
    ) -> User:
        """
        Update the role of a user and log the change.
        :param user_id: UUID of the user whose role is to be updated.
        :param role_data: UserRoleUpdate schema containing the new role and reason for change.
        :param admin_user_id: UUID of the admin performing the role change.
        :return:
        """
        user = await self.get_user_by_id(user_id)

        # Log the change
        logger.info(
            f"User role change: {user.email} "
            f"from {user.role} to {role_data.role} "
            f"by admin {admin_user_id}. Reason: {role_data.reason or 'None'}"
        )  # TODO: Move to logging service

        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(role=role_data.role, updated_at=datetime.now(UTC))
        )
        await self.db.execute(stmt)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def update_user_status(
        self, user_id: UUID, status_data: UserStatusUpdate, admin_user_id: UUID
    ) -> User:
        """
        Update the status of a user and log the change.
        :param user_id: UUID of the user whose status is to be updated.
        :param status_data: UserStatusUpdate schema containing the new status and reason for change.
        :param admin_user_id: UUID of the admin performing the status change.
        :return:
        """
        user = await self.get_user_by_id(user_id)

        # Log the change
        logger.info(
            f"User status change: {user.email} "
            f"from {user.status} to {status_data.status} "
            f"by admin {admin_user_id}. Reason: {status_data.reason or 'None'}"
        )  # TODO: Move to logging service

        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(status=status_data.status, updated_at=datetime.now(UTC))
        )
        await self.db.execute(stmt)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def soft_delete_user(self, user_id: UUID, admin_user_id: UUID) -> bool:
        """
        Soft delete a user account.
        :param user_id: UUID of the user to be soft deleted.
        :param admin_user_id: UUID of the admin performing the deletion.
        :return:
        """
        user = await self.get_user_by_id(user_id)

        if not user:
            raise NotFoundException("User", str(user_id))

        # Prevent self-deletion
        if user_id == admin_user_id:
            raise ForbiddenException("Cannot delete your own account")

        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(status=UserStatus.ARCHIVED, updated_at=datetime.now(UTC))
        )
        await self.db.execute(stmt)
        await self.db.commit()

        return True

    async def restore_user(self, user_id: UUID, admin_user_id: UUID) -> User:
        """
        Restore a soft-deleted user account.
        :param user_id: UUID of the user to be restored.
        :param admin_user_id: UUID of the admin performing the restoration.
        :return:
        """
        user = await self.get_user_by_id(user_id)

        if user.is_active:
            raise ValidationException("User is already active")

        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(status=UserStatus.ACTIVE, updated_at=datetime.now(UTC))
        )
        await self.db.execute(stmt)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def get_user_stats(self) -> UserStats:
        """
        Retrieve statistics about users in the system.
        :return: UserStats object containing various user metrics.
        """
        total_stmt = select(func.count(User.id)).where(
            User.status != UserStatus.ARCHIVED
        )
        total_users = await self.db.scalar(total_stmt) or 0

        # Active users
        active_stmt = select(func.count(User.id)).where(
            User.status == UserStatus.ACTIVE,
            User.last_activity_at >= datetime.now(UTC) - timedelta(days=14),
        )
        active_users = await self.db.scalar(active_stmt) or 0

        # Verified users
        verified_stmt = select(func.count(User.id)).where(
            User.status == UserStatus.ACTIVE, User.is_verified
        )
        verified_users = await self.db.scalar(verified_stmt) or 0

        # Users by status
        status_stmt = select(User.status, func.count(User.id)).group_by(User.status)
        status_result = await self.db.execute(status_stmt)
        users_by_status = {status: count for status, count in status_result.fetchall()}

        # Users by role
        role_stmt = select(User.role, func.count(User.id)).where().group_by(User.role)
        role_result = await self.db.execute(role_stmt)
        users_by_role = {role: count for role, count in role_result.fetchall()}

        return UserStats(
            total_users=total_users,
            active_users=active_users,
            verified_users=verified_users,
            users_by_status=users_by_status,
            users_by_role=users_by_role,
            users_by_provider={},  # TODO: Implement
        )
