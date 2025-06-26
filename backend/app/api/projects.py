import logging
from typing import Annotated, Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.client import get_db
from app.schemas.responses import (
    MessageResponse,
    DataResponse,
    ListResponse,
    PaginationMeta,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListItem,
    ProjectStats,
    ProjectStatusUpdate,
    ProjectMemberInvite,
    ProjectMemberUpdate,
    ProjectMemberResponse,
)
from app.schemas.auth import AuthUser
from app.services.project_service import ProjectService
from app.core.auth import get_current_user
from app.models.project import ProjectStatus, ProjectPriority, ProjectVisibility

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "/",
    response_model=DataResponse[ProjectResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    project_data: ProjectCreate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[ProjectResponse]:
    """
    Create a new project.

    User must be a member of the organization with project creation permissions.
    """
    project_service = ProjectService(db)
    project = await project_service.create_project(project_data, UUID(current_user.id))

    return DataResponse(
        message="Project created successfully",
        data=ProjectResponse.model_validate(project),
    )


@router.get("/", response_model=ListResponse)
async def get_my_projects(
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    organization_id: Optional[UUID] = Query(None, description="Filter by organization"),
) -> ListResponse:
    """
    Get all projects the current user is involved in (as lead or member).
    """
    project_service = ProjectService(db)
    projects = await project_service.get_user_projects(
        UUID(current_user.id), organization_id
    )

    project_list = [ProjectListItem.model_validate(project) for project in projects]

    return ListResponse(
        success=True,
        message="Projects retrieved successfully",
        data=project_list,
        pagination=PaginationMeta(
            page=1,
            size=len(project_list),
            total=len(project_list),
            pages=1,
            has_next=False,
            has_prev=False,
        ),
    )


@router.get("/organization/{organization_id}", response_model=ListResponse)
async def get_organization_projects(
    organization_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[ProjectStatus] = Query(None, description="Filter by status"),
    priority: Optional[ProjectPriority] = Query(None, description="Filter by priority"),
    visibility: Optional[ProjectVisibility] = Query(
        None, description="Filter by visibility"
    ),
    search: Optional[str] = Query(None, description="Search term"),
    include_archived: bool = Query(False, description="Include archived projects"),
) -> ListResponse:
    """
    Get projects for a specific organization with filtering and pagination.

    User must be a member of the organization.
    """
    project_service = ProjectService(db)
    projects, total = await project_service.get_organization_projects(
        organization_id=organization_id,
        user_id=UUID(current_user.id),
        page=page,
        size=size,
        status=status,
        priority=priority,
        visibility=visibility,
        search=search,
        include_archived=include_archived,
    )

    project_list = [ProjectListItem.model_validate(project) for project in projects]
    pages = (total + size - 1) // size

    return ListResponse(
        success=True,
        message="Organization projects retrieved successfully",
        data=project_list,
        pagination=PaginationMeta(
            page=page,
            size=size,
            total=total,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        ),
    )


@router.get(
    "/organization/{organization_id}/stats", response_model=DataResponse[ProjectStats]
)
async def get_organization_project_stats(
    organization_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[ProjectStats]:
    """
    Get project statistics for an organization.

    User must be a member of the organization.
    """
    project_service = ProjectService(db)
    stats = await project_service.get_project_stats(
        organization_id, UUID(current_user.id)
    )

    return DataResponse(
        message="Project statistics retrieved successfully",
        data=stats,
    )


@router.get("/{project_id}", response_model=DataResponse[ProjectResponse])
async def get_project(
    project_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[ProjectResponse | None]:
    """
    Get project details by ID.

    User must have view access to the project.
    """
    project_service = ProjectService(db)
    project = await project_service.get_project_by_id(project_id)

    if not await project_service.can_user_view_project(UUID(current_user.id), project):
        return DataResponse(
            message="You don't have permission to view this project",
            data=None,
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return DataResponse(
        message="Project retrieved successfully",
        data=ProjectResponse.model_validate(project),
    )


@router.get(
    "/organization/{organization_id}/key/{key}",
    response_model=DataResponse[ProjectResponse],
)
async def get_project_by_key(
    organization_id: UUID,
    key: str,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[ProjectResponse | None]:
    """
    Get project details by organization and key.

    User must have view access to the project.
    """
    project_service = ProjectService(db)
    project = await project_service.get_project_by_key(organization_id, key)

    if not project:
        from app.core.exceptions import NotFoundException

        raise NotFoundException("Project", f"{organization_id}/{key}")

    if not await project_service.can_user_view_project(UUID(current_user.id), project):
        return DataResponse(
            message="You don't have permission to view this project",
            data=None,
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return DataResponse(
        message="Project retrieved successfully",
        data=ProjectResponse.model_validate(project),
    )


@router.put("/{project_id}", response_model=DataResponse[ProjectResponse])
async def update_project(
    project_id: UUID,
    update_data: ProjectUpdate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[ProjectResponse]:
    """
    Update project details.

    User must have edit permissions for the project.
    """
    project_service = ProjectService(db)
    project = await project_service.update_project(
        project_id, update_data, UUID(current_user.id)
    )

    return DataResponse(
        message="Project updated successfully",
        data=ProjectResponse.model_validate(project),
    )


@router.put("/{project_id}/status", response_model=DataResponse[ProjectResponse])
async def update_project_status(
    project_id: UUID,
    status_data: ProjectStatusUpdate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[ProjectResponse]:
    """
    Update project status.

    User must have edit permissions for the project.
    """
    project_service = ProjectService(db)
    project = await project_service.update_project_status(
        project_id, status_data, UUID(current_user.id)
    )

    return DataResponse(
        message="Project status updated successfully",
        data=ProjectResponse.model_validate(project),
    )


@router.post("/{project_id}/archive", response_model=DataResponse[ProjectResponse])
async def archive_project(
    project_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[ProjectResponse]:
    """
    Archive a project.

    User must have edit permissions for the project.
    """
    project_service = ProjectService(db)
    project = await project_service.archive_project(project_id, UUID(current_user.id))

    return DataResponse(
        message="Project archived successfully",
        data=ProjectResponse.model_validate(project),
    )


@router.post("/{project_id}/restore", response_model=DataResponse[ProjectResponse])
async def restore_project(
    project_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[ProjectResponse]:
    """
    Restore an archived project.

    User must have edit permissions for the project.
    """
    project_service = ProjectService(db)
    project = await project_service.restore_project(project_id, UUID(current_user.id))

    return DataResponse(
        message="Project restored successfully",
        data=ProjectResponse.model_validate(project),
    )


@router.delete("/{project_id}", response_model=MessageResponse)
async def delete_project(
    project_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """
    Delete a project (soft delete).

    Only project leads or organization admins can delete projects.
    """
    project_service = ProjectService(db)
    success = await project_service.delete_project(project_id, UUID(current_user.id))

    return MessageResponse(
        "Project deleted successfully" if success else "Failed to delete project"
    )


@router.get(
    "/{project_id}/members", response_model=DataResponse[List[ProjectMemberResponse]]
)
async def get_project_members(
    project_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[List[ProjectMemberResponse]]:
    """
    Get all members of a project.

    User must have view access to the project.
    """
    project_service = ProjectService(db)
    members = await project_service.get_project_members(
        project_id, UUID(current_user.id)
    )

    member_list = [ProjectMemberResponse.model_validate(member) for member in members]

    return DataResponse(
        message="Project members retrieved successfully",
        data=member_list,
    )


@router.post(
    "/{project_id}/members", response_model=DataResponse[ProjectMemberResponse]
)
async def add_project_member(
    project_id: UUID,
    invite_data: ProjectMemberInvite,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[ProjectMemberResponse]:
    """
    Add a member to the project.

    User must have project management permissions.
    """
    project_service = ProjectService(db)
    member = await project_service.add_project_member(
        project_id, invite_data, UUID(current_user.id)
    )

    return DataResponse(
        message="Project member added successfully",
        data=ProjectMemberResponse.model_validate(member),
    )


@router.put(
    "/{project_id}/members/{user_id}",
    response_model=DataResponse[ProjectMemberResponse],
)
async def update_project_member_role(
    project_id: UUID,
    user_id: UUID,
    update_data: ProjectMemberUpdate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[ProjectMemberResponse]:
    """
    Update a project member's role.

    User must have project management permissions.
    """
    project_service = ProjectService(db)
    member = await project_service.update_project_member_role(
        project_id, user_id, update_data, UUID(current_user.id)
    )

    return DataResponse(
        message="Project member role updated successfully",
        data=ProjectMemberResponse.model_validate(member),
    )


@router.delete("/{project_id}/members/{user_id}", response_model=MessageResponse)
async def remove_project_member(
    project_id: UUID,
    user_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """
    Remove a member from the project.

    User must have project management permissions.
    """
    project_service = ProjectService(db)
    success = await project_service.remove_project_member(
        project_id, user_id, UUID(current_user.id)
    )

    return MessageResponse(
        "Project member removed successfully"
        if success
        else "Failed to remove project member"
    )
