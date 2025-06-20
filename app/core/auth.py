import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.client import get_db
from app.models.user import User, UserStatus
from app.schemas.auth import AuthUser
from app.core.security import TokenManager
from app.db.redis_client import redis_client
from app.core.exceptions import (
    AuthenticationException,
    NotFoundException,
    ForbiddenException,
    APIException,
)

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> AuthUser:
    """
    Dependency to get the current authenticated user.
    :param credentials: HTTP authorization credentials containing the token.
    :param db: Database session dependency.
    :return: AuthUser object representing the authenticated user.
    """
    try:
        token_manager = TokenManager()
        payload = token_manager.decode_token(credentials.credentials)

        # Verify token type
        if payload.get("type") != "access":
            raise AuthenticationException("Invalid token type")

        # Check if token is blacklisted
        jti = payload.get("jti")
        if jti and await redis_client.is_token_blacklisted(jti):
            raise AuthenticationException("Token has been revoked")

        # Get user from database
        user_id = payload.get("user_id")
        if not user_id:
            raise AuthenticationException("Invalid token payload")

        stmt = select(User).where(User.id == user_id)
        user = await db.scalar(stmt)

        if not user:
            raise NotFoundException("User", user_id)

        # Check user status
        if not user.is_active or user.status in [
            UserStatus.SUSPENDED,
            UserStatus.ARCHIVED,
        ]:
            raise ForbiddenException("User account is not active")

        # Return authenticated user
        return AuthUser(
            id=str(user.id),
            email=user.email,
            username=user.username,
            role=user.role.value,
            is_verified=user.is_verified,
            is_active=user.is_active,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
        )

    except ValueError:
        # Token decode error
        raise AuthenticationException("Token has expired or is invalid")
    except APIException as e:
        raise e
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error in get_current_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


async def get_current_active_user(
    current_user: AuthUser = Depends(get_current_user),
) -> AuthUser:
    """
    Dependency to get the current active user.
    :param current_user: Authenticated user from get_current_user dependency.
    :return: AuthUser object if the user is active.
    """
    if not current_user.is_active:
        raise ForbiddenException("Inactive user")
    return current_user


async def get_current_verified_user(
    current_user: AuthUser = Depends(get_current_user),
) -> AuthUser:
    """
    Dependency to get the current verified user.
    :param current_user: Authenticated user from get_current_user dependency.
    :return: AuthUser object if the user is verified.
    """
    if not current_user.is_verified:
        raise ForbiddenException("User account is not verified")
    return current_user


async def require_role(
    required_roles: list[str],
):
    """
    Dependency to check if the current user has one of the required roles.
    :param required_roles: List of roles that are allowed.
    :return: AuthUser object if the user has a required role.
    """

    async def role_checker(
        current_user: AuthUser = Depends(get_current_active_user),
    ) -> AuthUser:
        if current_user.role not in required_roles:
            raise ForbiddenException(
                f"Access denied. Required roles: {', '.join(required_roles)}"
            )
        return current_user

    return role_checker
