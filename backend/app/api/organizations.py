import logging
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.client import get_db
from app.schemas.responses import (
    MessageResponse,
    DataResponse,
    ListResponse,
    PaginationMeta,
)
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationListItem,
    OrganizationStats,
)
from app.schemas.auth import AuthUser
from app.services.organization_service import OrganizationService
from app.core.auth import get_current_user, require_admin
from app.services.storage_service import StorageService
from app.core.exceptions import (
    ValidationException,
    ForbiddenException,
    NotFoundException,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post(
    "/",
    response_model=DataResponse[OrganizationResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[OrganizationResponse]:
    """
    Create a new organization.

    The current user will become the owner of the organization.
    """
    org_service = OrganizationService(db)
    organization = await org_service.create_organization(
        org_data, UUID(current_user.id)
    )

    return DataResponse(
        message="Organization created successfully",
        data=OrganizationResponse.model_validate(organization),
    )


@router.get("/", response_model=ListResponse)
async def get_my_organizations(
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    include_pending: bool = Query(
        False, description="Include organizations with pending membership"
    ),
) -> ListResponse:
    """
    Get all organizations that the current user is a member of.
    """
    org_service = OrganizationService(db)
    organizations = await org_service.get_user_organizations(
        UUID(current_user.id), include_pending=include_pending
    )

    org_list = [OrganizationListItem.model_validate(org) for org in organizations]

    return ListResponse(
        success=True,
        message="Organizations retrieved successfully",
        data=org_list,
        pagination=PaginationMeta(
            page=1,
            size=len(org_list),
            total=len(org_list),
            pages=1,
            has_next=False,
            has_prev=False,
        ),
    )


@router.get("/stats", response_model=DataResponse[OrganizationStats])
async def get_organization_stats(
    admin_user: Annotated[AuthUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[OrganizationStats]:
    """
    Get organization statistics for admin dashboard.
    """
    # TODO: https://github.com/Anvoria/smithy/issues/8

    # Placeholder stats
    stats = OrganizationStats(
        total_organizations=0,
        active_organizations=0,
        organizations_by_type={},
        total_members=0,
        avg_members_per_org=0.0,
        total_projects=0,
        avg_projects_per_org=0.0,
    )

    return DataResponse(
        message="Organization statistics retrieved successfully",
        data=stats,
    )


@router.get("/{org_id}", response_model=DataResponse[OrganizationResponse])
async def get_organization(
    org_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[OrganizationResponse | None]:
    """
    Get organization details by ID.

    User must be a member of the organization to access it.
    """
    org_service = OrganizationService(db)
    organization = await org_service.get_organization_by_id(org_id)

    organization_member = await org_service.get_organization_member(
        org_id, UUID(current_user.id)
    )

    if not organization_member:
        return DataResponse(
            message="You are not a member of this organization",
            data=None,
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return DataResponse(
        message="Organization retrieved successfully",
        data=OrganizationResponse.model_validate(organization),
    )


@router.get("/slug/{slug}", response_model=DataResponse[OrganizationResponse])
async def get_organization_by_slug(
    slug: str,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[OrganizationResponse | None]:
    """
    Get organization details by slug.
    """
    org_service = OrganizationService(db)
    organization = await org_service.get_organization_by_slug(slug)

    if not organization:
        from app.core.exceptions import NotFoundException

        raise NotFoundException("Organization", slug)

    organization_member = await org_service.get_organization_member(
        organization.id, UUID(current_user.id)
    )

    if not organization_member:
        return DataResponse(
            message="You are not a member of this organization",
            data=None,
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return DataResponse(
        message="Organization retrieved successfully",
        data=OrganizationResponse.model_validate(organization),
    )


@router.put("/{org_id}", response_model=DataResponse[OrganizationResponse])
async def update_organization(
    org_id: UUID,
    update_data: OrganizationUpdate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[OrganizationResponse]:
    """
    Update organization details.

    User must be an owner or admin of the organization.
    """
    org_service = OrganizationService(db)
    organization = await org_service.update_organization(
        org_id, update_data, UUID(current_user.id)
    )

    return DataResponse(
        message="Organization updated successfully",
        data=OrganizationResponse.model_validate(organization),
    )


@router.post("/{org_id}/media/{logo_type}", response_model=DataResponse[Optional[dict]])
async def upload_organization_media(
    org_id: UUID,
    logo_type: str,
    file: UploadFile,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[Optional[dict]]:
    """
    Upload organization logo, avatar, or banner.
    """
    storage_service = StorageService(db)

    try:
        public_url = await storage_service.upload_organization_logo(
            organization_id=org_id,
            file=file,
            current_user_id=UUID(current_user.id),
            logo_type=logo_type,
        )

        return DataResponse(
            message=f"Organization {logo_type} uploaded successfully",
            data={"public_url": public_url, "logo_type": logo_type},
        )

    except ValidationException as e:
        return DataResponse(
            message=str(e), data=None, status_code=status.HTTP_400_BAD_REQUEST
        )
    except ForbiddenException as e:
        return DataResponse(
            message=str(e), data=None, status_code=status.HTTP_403_FORBIDDEN
        )
    except NotFoundException as e:
        return DataResponse(
            message=str(e), data=None, status_code=status.HTTP_404_NOT_FOUND
        )


@router.delete("/{org_id}/media/{logo_type}")
async def delete_organization_media(
    org_id: UUID,
    logo_type: str,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """
    Delete organization logo, avatar, or banner.
    """
    storage_service = StorageService(db)

    try:
        public_url = await storage_service.delete_organization_logo(
            organization_id=org_id,
            current_user_id=UUID(current_user.id),
            logo_type=logo_type,
        )

        return MessageResponse(
            message=f"Organization {logo_type} deleted successfully",
            data={"public_url": public_url, "logo_type": logo_type},
        )
    except Exception as e:
        logger.error(f"Error deleting organization media: {e}")
        return MessageResponse(
            message="Failed to delete organization media",
            success=False,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/{org_id}", response_model=MessageResponse)
async def delete_organization(
    org_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """
    Delete organization (soft delete).

    Only organization owners can delete organizations.
    """
    org_service = OrganizationService(db)
    success = await org_service.delete_organization(org_id, UUID(current_user.id))

    return MessageResponse(
        "Organization deleted successfully"
        if success
        else "Failed to delete organization"
    )
