import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.client import get_db
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshTokenRequest,
    LogoutRequest,
)
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Register a new user and return authentication tokens.

    Creates a new user with email verification pending.
    Returns access and refresh tokens for immediate login.
    """
    auth_service = AuthService(db)
    user, tokens = await auth_service.register_user(user_data)

    return tokens


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> TokenResponse:
    """
    Authenticate user and create session.

    Returns access and refresh tokens on successful authentication.
    Implements account locking after failed attempts.
    """
    auth_service = AuthService(db)
    tokens = await auth_service.authenticate_user(login_data)

    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> TokenResponse:
    """
    Refresh access token using refresh token.

    Returns new access and refresh tokens.
    Invalidates the old refresh token.
    """
    auth_service = AuthService(db)
    tokens = await auth_service.refresh_access_token(refresh_data.refresh_token)

    return tokens


@router.post("/logout")
async def logout(
    logout_data: LogoutRequest,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Logout user and revoke tokens.

    Blacklists access and refresh tokens to prevent further use.
    """
    auth_service = AuthService(db)
    success = await auth_service.logout_user(
        access_token=credentials.credentials,
        refresh_token=logout_data.refresh_token,
    )

    if success:
        return {"message": "Logged out successfully"}
    else:
        logger.warning("Partial logout - some tokens may not be revoked")
        return {"message": "Logged out (some tokens may still be valid)"}
