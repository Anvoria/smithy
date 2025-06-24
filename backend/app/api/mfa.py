import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.client import get_db
from app.schemas.auth import (
    AuthUser,
    MFAVerifyRequest,
    MFASetupRequest,
    MFASetupResponse,
    MFADisableRequest,
    MFABackupCodesInfo,
)
from app.schemas.responses import DataResponse, MessageResponse
from app.services.mfa_service import MFAService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mfa", tags=["Multi-Factor Authentication"])


@router.post("/setup", response_model=DataResponse[MFASetupResponse])
async def setup_mfa(
    setup_data: MFASetupRequest,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[MFASetupResponse]:
    """
    Set up multi-factor authentication for the current user.

    Returns TOTP secret and QR code URL for the user to scan with their authenticator app
    """
    mfa_service = MFAService(db)
    mfa_response = await mfa_service.setup_mfa(UUID(current_user.id), setup_data)

    return DataResponse(message="MFA setup initiated successfully", data=mfa_response)


@router.post("/verify", response_model=MessageResponse)
async def verify_mfa_setup(
    verify_data: MFAVerifyRequest,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """
    Verify the multi-factor authentication setup for the current user.

    This completes the MFA setup process.
    """
    mfa_service = MFAService(db)
    success = await mfa_service.verify_and_enable_mfa(
        UUID(current_user.id), verify_data
    )

    if success:
        return MessageResponse(message="MFA setup verified and enabled successfully")
    else:
        return MessageResponse(message="MFA setup verification failed", success=False)


@router.post("/disable", response_model=MessageResponse)
async def disable_mfa(
    disable_data: MFADisableRequest,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """
    Disable MFA for the current user.

    Requires current password and MFA code/backup code to confirm the action.
    """
    mfa_service = MFAService(db)
    success = await mfa_service.disable_mfa(UUID(current_user.id), disable_data)

    if success:
        return MessageResponse(message="MFA disabled successfully")
    else:
        return MessageResponse(message="Failed to disable MFA", success=False)


@router.post("/backup-codes/generate", response_model=DataResponse[list[str]])
async def generate_backup_codes(
    setup_data: MFASetupRequest,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[list[str]]:
    """
    Generate backup codes for the current user.

    This invalidates all previous backup codes and returns a new set.
    """
    mfa_service = MFAService(db)
    backup_codes = await mfa_service.generate_backup_codes(
        UUID(current_user.id), setup_data.password
    )

    return DataResponse(
        message="Backup codes generated successfully", data=backup_codes
    )


@router.post("/backup-codes/info", response_model=DataResponse[MFABackupCodesInfo])
async def get_backup_codes_info(
    setup_data: MFASetupRequest,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[MFABackupCodesInfo]:
    """
    Get information about the user's backup codes.

    Requires current password to confirm the request.
    """
    mfa_service = MFAService(db)
    backup_codes_info = await mfa_service.get_backup_codes_info(
        UUID(current_user.id), setup_data.password
    )

    return DataResponse(
        message="Backup codes information retrieved successfully",
        data=backup_codes_info,
    )


@router.post("/verify-code", response_model=MessageResponse)
async def verify_mfa_code(
    verify_data: MFAVerifyRequest,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """
    Verify a multi-factor authentication code for the current user.

    This endpoint can be used to verify MFA codes for sensitive actions
    """
    mfa_service = MFAService(db)
    success = await mfa_service.verify_mfa_code(UUID(current_user.id), verify_data.code)

    if success:
        return MessageResponse(message="MFA code verified successfully")
    else:
        return MessageResponse(message="Invalid MFA code", success=False)
