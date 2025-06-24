import logging
from datetime import datetime, timedelta, UTC
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.user import User, UserStatus
from app.schemas.auth import LoginRequest, RegisterRequest, AuthUser, TokenResponse
from app.core.security import PasswordManager, TokenManager, VerificationTokenManager
from app.db.redis_client import redis_client
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationException,
    ConflictError,
    NotFoundException,
    ForbiddenException,
)

from app.services.mfa_service import MFAService

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service with Redis caching and session management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.password_manager = PasswordManager()
        self.token_manager = TokenManager()
        self.verification_token_manager = VerificationTokenManager()

    async def register_user(
        self, user_data: RegisterRequest
    ) -> Tuple[User, TokenResponse]:
        """
        Register a new user and return the user object along with authentication tokens.
        :param user_data: User registration data.
        :return: Tuple containing the created User object and TokenResponse with access and refresh tokens.
        """
        # Check if user already exists
        stmt = select(User).where(
            (User.email == user_data.email) | (User.username == user_data.username)
        )

        existing_user = await self.db.scalar(stmt)
        if existing_user:
            raise ConflictError("User with this email or username already exists")

        # Create new user
        hashed_password = self.password_manager.hash_password(user_data.password)

        new_user = User(
            email=str(user_data.email),
            username=user_data.username,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            password_hash=hashed_password,
            status=UserStatus.ACTIVE,  # TODO: https://github.com/Anvoria/smithy/issues/13
        )

        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)

        # Generate tokens
        tokens = await self._create_user_session(new_user)

        logger.info(f"User registered successfully: {new_user.email}")
        return new_user, tokens

    async def authenticate_user(self, login_data: LoginRequest) -> TokenResponse:
        """
        Authenticate user and return authentication tokens.
        :param login_data: User login credentials.
        :return: TokenResponse with access and refresh tokens.
        """
        # Fetch user by email
        stmt = select(User).where(User.email == login_data.email)
        user = await self.db.scalar(stmt)

        if not user or not self.password_manager.verify_password(
            login_data.password, str(user.password_hash)
        ):
            raise AuthenticationException("Invalid email or password")

        if not user.is_active or user.status == UserStatus.SUSPENDED:
            raise ForbiddenException("User account is not active")

        if user.mfa_enabled:
            if not hasattr(login_data, "mfa_code") or not login_data.mfa_code:
                partial_auth_token = (
                    self.verification_token_manager.generate_verification_token()
                )
                await redis_client.set(
                    f"partial_auth:{partial_auth_token}",
                    {
                        "user_id": str(user.id),
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                    expire=60 * 5,
                )

                raise AuthenticationException(
                    "MFA code required",
                    details={
                        "required_mfa": True,
                        "partial_auth_token": partial_auth_token,
                    },
                )

            mfa_service = MFAService(self.db)
            if not await mfa_service.verify_mfa_code(
                UUID(str(user.id)), login_data.mfa_code
            ):
                raise AuthenticationException("Invalid MFA code")

        # Update login information
        await self._update_login_info(user)

        # Generate tokens
        tokens = await self._create_user_session(user)

        return tokens

    async def complete_mfa_authentication(
        self, partial_auth_token: str, mfa_code: str
    ) -> TokenResponse:
        """
        Complete MFA authentication using partial auth token.

        :param partial_auth_token: Token from initial authentication
        :param mfa_code: MFA code for verification
        :return: TokenResponse with access and refresh tokens
        """
        partial_data = await redis_client.get(f"partial_auth:{partial_auth_token}")
        if not partial_data:
            raise AuthenticationException("Invalid or expired authentication session")

        user_id = partial_data["user_id"]
        user = await self.db.get(User, user_id)

        if not user or not user.mfa_enabled:
            raise AuthenticationException("Invalid authentication session")

        # Verify MFA code
        mfa_service = MFAService(self.db)

        if not await mfa_service.verify_mfa_code(
            UUID(str(user.id)), mfa_code, check_backup=False
        ):
            raise AuthenticationException("Invalid MFA code")

        # Clean up partial auth
        await redis_client.delete(f"partial_auth:{partial_auth_token}")

        # Update login information
        await self._update_login_info(user)

        # Generate tokens
        tokens = await self._create_user_session(user)

        return tokens

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """
        Refresh access token using a valid refresh token.
        :param refresh_token: Valid refresh token.
        :return: TokenResponse with new access and refresh tokens.
        """
        try:
            payload = self.token_manager.decode_token(refresh_token)
        except ValueError as e:
            raise AuthenticationException(f"Invalid refresh token: {str(e)}")

        # Verify token type
        if payload.get("type") != "refresh":
            raise AuthenticationException("Invalid token type")

        # Check blacklist
        jti = payload.get("jti")
        if jti and await redis_client.is_token_blacklisted(jti):
            raise AuthenticationException("Token has been blacklisted")

        # Fetch user by ID
        user_id = payload.get("user_id")
        user = await self.db.get(User, user_id)

        if not user or not user.is_active or user.status == UserStatus.SUSPENDED:
            raise NotFoundException("User not found or inactive")

        # Create new session
        tokens = await self._create_user_session(user)

        # Blacklist old refresh token
        if jti:
            expire_time = payload.get("exp", 0)
            current_time = datetime.now(UTC).timestamp()
            if expire_time > current_time:
                await redis_client.blacklist_token(jti, int(expire_time - current_time))

        return tokens

    async def logout_user(
        self, access_token: str, refresh_token: Optional[str] = None
    ) -> bool:
        """
        Log out user by invalidating access and refresh tokens.
        :param access_token: User's access token.
        :param refresh_token: Optional refresh token to invalidate.
        :return: True if logout was successful, False otherwise.
        """
        success = True

        # Blacklist access token
        try:
            payload = self.token_manager.decode_token(access_token)
            jti = payload.get("jti")
            if jti:
                expire_time = payload.get("exp", 0)
                current_time = datetime.now(UTC).timestamp()
                if expire_time > current_time:
                    await redis_client.blacklist_token(
                        jti, int(expire_time - current_time)
                    )
        except ValueError as e:
            logger.error(f"Failed to decode access token: {str(e)}")
            success = False

        # Blacklist refresh token if provided
        if refresh_token:
            try:
                jti = self.token_manager.get_token_jti(refresh_token)
                if jti:
                    await redis_client.blacklist_token(jti, 86400 * 7)  # 7 days
            except Exception as e:
                logger.warning(f"Failed to blacklist refresh token: {e}")
                success = False

        return success

    async def _create_user_session(
        self, user: User, remember_me: bool = False
    ) -> TokenResponse:
        """
        Create user session and return authentication tokens.
        :param user: User object for which to create sessions.
        :param remember_me: Whether to create a long-lived session.
        :return: TokenResponse with access and refresh tokens.
        """
        access_expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_expire = timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS * (2 if remember_me else 1)
        )

        # Create tokens
        access_token = self.token_manager.create_access_token(
            subject=user.email,
            user_id=str(user.id),
            role=user.role.value,
            expires_delta=access_expire,
            additional_claims={
                "mfa_enabled": user.mfa_enabled,
                "is_verified": user.is_verified,
            },
        )

        refresh_token = self.token_manager.create_refresh_token(
            subject=user.email, user_id=str(user.id), expires_delta=refresh_expire
        )

        # Store session in Redis
        session_data = {
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "login_at": datetime.now(UTC).isoformat(),
            "remember_me": remember_me,
            "mfa_enabled": user.mfa_enabled,
        }

        # Get session ID from access token
        access_payload = self.token_manager.decode_token(access_token)
        session_id = access_payload.get("jti")

        if session_id:
            session_expire = int(refresh_expire.total_seconds())
            await redis_client.set_session(session_id, session_data, session_expire)

        # Create user info for response
        auth_user = AuthUser(
            id=str(user.id),
            email=user.email,
            username=user.username,
            role=user.role.value,
            is_verified=user.is_verified,
            is_active=user.is_active,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(access_expire.total_seconds()),
            user=auth_user.model_dump(),
            token_type="bearer",
        )

    async def _handle_failed_login(
        self, email: str, user: Optional[User] = None
    ) -> None:
        """
        Handle failed login attempts by incrementing the count and locking the account if necessary.
        :param email: Email of the user attempting to log in.
        :param user: User object if it exists, otherwise None.
        :return: None
        """
        if not user:
            # Don't reveal if user exists
            return

        # TODO: Implement logic to track failed login attempts
        # https://github.com/Anvoria/smithy/issues/3
        pass

    async def _update_login_info(self, user: User) -> None:
        """
        Update user's last login and activity timestamps, and increment login count.
        :param user: User object to update.
        :return: None
        """
        now = datetime.now(UTC)

        stmt = (
            update(User)
            .where(User.id == user.id)
            .values(
                last_login_at=now,
                last_activity_at=now,
                login_count=User.login_count + 1,
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()
