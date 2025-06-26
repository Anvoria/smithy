import logging
from datetime import datetime, UTC
from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.orm import selectinload

from app.models.project import (
    Project,
    ProjectStatus,
    ProjectPriority,
    ProjectVisibility,
)
from app.models.project_member import ProjectMember, ProjectRole
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember, OrganizationRole
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectMemberInvite,
    ProjectMemberUpdate,
    ProjectStatusUpdate,
    ProjectStats,
)
from app.core.exceptions import (
    NotFoundException,
    ConflictError,
    ValidationException,
    ForbiddenException,
)
from app.services.common import CommonService

logger = logging.getLogger(__name__)


class ProjectService:
    """Project management service with member operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_project_by_id(
        self, project_id: UUID, include_deleted: bool = False
    ) -> Project:
        """
        Retrieve a project by its ID.
        :param project_id: UUID of the project to retrieve.
        :param include_deleted: Whether to include deleted projects.
        :return: Project object if found, otherwise raises NotFoundException.
        """
        stmt = select(Project).where(Project.id == project_id)

        if not include_deleted:
            stmt = stmt.where(Project.deleted_at.is_(None))

        stmt = stmt.options(
            selectinload(Project.organization),
            selectinload(Project.lead),
            selectinload(Project.members).selectinload(ProjectMember.user),
        )

        project = await self.db.scalar(stmt)
        if not project:
            raise NotFoundException("Project", str(project_id))

        return project

    async def get_project_by_key(
        self, organization_id: UUID, key: str, include_deleted: bool = False
    ) -> Optional[Project]:
        """
        Retrieve a project by its key within an organization.
        :param organization_id: UUID of the organization.
        :param key: Project key to search for.
        :param include_deleted: Whether to include deleted projects.
        :return: Project object if found, otherwise None.
        """
        stmt = select(Project).where(
            Project.organization_id == organization_id, Project.key == key.upper()
        )

        if not include_deleted:
            stmt = stmt.where(Project.deleted_at.is_(None))

        stmt = stmt.options(
            selectinload(Project.organization),
            selectinload(Project.lead),
            selectinload(Project.members).selectinload(ProjectMember.user),
        )

        return await self.db.scalar(stmt)

    async def create_project(
        self, project_data: ProjectCreate, creator_id: UUID
    ) -> Project:
        """
        Create a new project with the provided data.
        :param project_data: ProjectCreate schema containing project details.
        :param creator_id: UUID of the user creating the project.
        :return: Created Project object.
        """
        org_member = await self._get_organization_member(
            project_data.organization_id, creator_id
        )
        if not org_member or not org_member.is_active:
            raise ForbiddenException("You are not a member of this organization")

        if not self._can_create_projects(org_member.role):
            raise ForbiddenException("Insufficient permissions to create projects")

        org = await self.db.get(Organization, project_data.organization_id)
        if not org:
            raise ValidationException("Organization not found")

        # Check project limits
        current_projects_stmt = select(func.count(Project.id)).where(
            Project.organization_id == project_data.organization_id,
            Project.deleted_at.is_(None),
        )
        current_projects_count = await self.db.scalar(current_projects_stmt) or 0

        if current_projects_count >= org.max_projects:
            raise ValidationException("Organization has reached its project limit")

        existing_project = await self.get_project_by_key(
            project_data.organization_id, project_data.key
        )
        if existing_project:
            raise ConflictError(
                f"Project with key '{project_data.key}' already exists in this organization"
            )

        if project_data.lead_id:
            lead_member = await self._get_organization_member(
                project_data.organization_id, project_data.lead_id
            )
            if not lead_member or not lead_member.is_active:
                raise ValidationException(
                    "Project lead must be an active organization member"
                )

        settings_dict = CommonService.serialize_pydantic_to_dict(project_data.settings)

        project = Project(
            name=project_data.name,
            key=project_data.key.upper(),
            description=project_data.description,
            organization_id=project_data.organization_id,
            lead_id=project_data.lead_id or creator_id,
            icon=project_data.icon,
            color=project_data.color,
            cover_image_url=project_data.cover_image_url,
            priority=project_data.priority,
            visibility=project_data.visibility,
            start_date=project_data.start_date,
            due_date=project_data.due_date,
            enable_subtasks=project_data.enable_subtasks,
            settings=settings_dict or {},
        )

        self.db.add(project)
        await self.db.flush()

        lead_user_id = project_data.lead_id or creator_id

        lead_membership = ProjectMember(
            project_id=project.id,
            user_id=lead_user_id,
            role=ProjectRole.LEAD,
            added_by=creator_id,
        )
        self.db.add(lead_membership)

        if project_data.lead_id and project_data.lead_id != creator_id:
            creator_membership = ProjectMember(
                project_id=project.id,
                user_id=creator_id,
                role=ProjectRole.DEVELOPER,
                added_by=creator_id,
            )
            self.db.add(creator_membership)

        await self.db.commit()

        # Load relations for response
        stmt = (
            select(Project)
            .where(Project.id == project.id)
            .options(
                selectinload(Project.organization),
                selectinload(Project.lead),
            )
        )

        project_with_relations = await self.db.scalar(stmt)
        return project_with_relations

    async def update_project(
        self, project_id: UUID, update_data: ProjectUpdate, user_id: UUID
    ) -> Project:
        """
        Update an existing project with the provided data.
        :param project_id: UUID of the project to update.
        :param update_data: ProjectUpdate schema containing updated project details.
        :param user_id: UUID of the user performing the update.
        :return: Updated Project object.
        """
        project = await self.get_project_by_id(project_id)

        if not await self.can_user_edit_project(user_id, project):
            raise ForbiddenException("Insufficient permissions to update this project")

        if update_data.lead_id:
            lead_member = await self._get_organization_member(
                project.organization_id, update_data.lead_id
            )
            if (
                not lead_member or not lead_member.is_active
            ):  # This shouldn't be possible
                raise ValidationException(
                    "Lead user is not an active member of the organization"
                )

        update_values: Dict[str, Any] = {}
        for field, value in update_data.model_dump(exclude_unset=True).items():
            if hasattr(project, field) and value is not None:
                if field == "settings":
                    update_values[field] = CommonService.serialize_pydantic_to_dict(
                        value
                    )
                else:
                    update_values[field] = value

        if update_values:
            update_values["updated_at"] = datetime.now(UTC)

            stmt = (
                update(Project).where(Project.id == project_id).values(**update_values)
            )
            await self.db.execute(stmt)
            await self.db.commit()
            await self.db.refresh(project)

        return project

    async def update_project_status(
        self, project_id: UUID, status_data: ProjectStatusUpdate, user_id: UUID
    ) -> Project:
        """
        Update the status of a project.
        :param project_id: UUID of the project to update.
        :param status_data: ProjectStatusUpdate schema containing new status and priority.
        :param user_id: UUID of the user performing the update.
        :return: Updated Project object.
        """
        project = await self.get_project_by_id(project_id)

        if not await self.can_user_edit_project(user_id, project):
            raise ForbiddenException("Insufficient permissions to update this project")

        update_values = {"status": status_data.status, "updated_at": datetime.now(UTC)}

        if status_data.status == ProjectStatus.COMPLETED and not project.completed_at:
            update_values["completed_at"] = datetime.now(UTC)
        elif status_data.status != ProjectStatus.COMPLETED and project.completed_at:
            update_values["completed_at"] = None

        stmt = update(Project).where(Project.id == project_id).values(**update_values)
        await self.db.execute(stmt)
        await self.db.commit()
        await self.db.refresh(project)

        return project

    async def get_organization_projects(
        self,
        organization_id: UUID,
        user_id: UUID,
        page: int = 1,
        size: int = 20,
        status: Optional[ProjectStatus] = None,
        priority: Optional[ProjectPriority] = None,
        visibility: Optional[ProjectVisibility] = None,
        search: Optional[str] = None,
        include_archived: bool = False,
    ) -> Tuple[List[Project], int]:
        """
        Retrieve projects for an organization with optional filters and pagination.
        :param organization_id: UUID of the organization.
        :param user_id: UUID of the user requesting the projects.
        :param page: Page number for pagination.
        :param size: Number of projects per page.
        :param status: Filter by project status.
        :param priority: Filter by project priority.
        :param visibility: Filter by project visibility.
        :param search: Search term to filter projects by name or key.
        :param include_archived: Whether to include archived projects.
        :return: Tuple of list of Project objects and total count.
        """
        org_member = await self._get_organization_member(organization_id, user_id)
        if not org_member or not org_member.is_active:
            raise ForbiddenException("You are not a member of this organization")

        stmt = select(Project).where(
            Project.organization_id == organization_id, Project.deleted_at.is_(None)
        )

        if org_member.role not in [OrganizationRole.OWNER, OrganizationRole.ADMIN]:
            visibility_conditions = [
                Project.visibility == ProjectVisibility.ORGANIZATION,
                Project.visibility == ProjectVisibility.PUBLIC,
                and_(
                    Project.visibility == ProjectVisibility.PRIVATE,
                    or_(
                        Project.lead_id == user_id,
                        Project.members.any(ProjectMember.user_id == user_id),
                    ),
                ),
            ]
            stmt = stmt.where(or_(*visibility_conditions))

        if status:
            stmt = stmt.where(Project.status == status)

        if priority:
            stmt = stmt.where(Project.priority == priority)

        if visibility:
            stmt = stmt.where(Project.visibility == visibility)

        if not include_archived:
            stmt = stmt.where(Project.archived_at.is_(None))

        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Project.name.ilike(search_term),
                    Project.description.ilike(search_term),
                    Project.key.ilike(search_term),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = await self.db.scalar(count_stmt)

        # Pagination
        offset = (page - 1) * size
        stmt = (
            stmt.offset(offset)
            .limit(size)
            .order_by(Project.updated_at.desc())
            .options(
                selectinload(Project.organization),
                selectinload(Project.lead),
                selectinload(Project.members).selectinload(ProjectMember.user),
            )
        )

        result = await self.db.execute(stmt)
        projects = result.scalars().all()

        return list(projects), total_count or 0

    async def get_user_projects(
        self, user_id: UUID, organization_id: Optional[UUID] = None
    ) -> List[Project]:
        """
        Retrieve all projects for a user, optionally filtered by organization.
        :param user_id: UUID of the user.
        :param organization_id: Optional UUID of the organization to filter by.
        :return: List of Project objects.
        """
        stmt = (
            select(Project)
            .where(
                Project.deleted_at.is_(None),
                Project.archived_at.is_(None),
                or_(
                    Project.lead_id == user_id,
                    Project.members.any(ProjectMember.user_id == user_id),
                ),
            )
            .options(
                selectinload(Project.organization),
                selectinload(Project.lead),
            )
        )

        if organization_id:
            stmt = stmt.where(Project.organization_id == organization_id)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def add_project_member(
        self, project_id: UUID, invite_data: ProjectMemberInvite, inviter_id: UUID
    ) -> ProjectMember:
        """
        Add a member to a project.
        :param project_id: UUID of the project.
        :param invite_data: ProjectMemberInvite schema containing user and role.
        :param inviter_id: UUID of the user adding the member.
        :return: Created ProjectMember object.
        """
        project = await self.get_project_by_id(project_id)

        if not await self.can_user_manage_project_members(inviter_id, project):
            raise ForbiddenException("Insufficient permissions to add project members")

        org_member = await self._get_organization_member(
            project.organization_id, invite_data.user_id
        )
        if not org_member or not org_member.is_active:
            raise ValidationException("User must be an active organization member")

        existing_member = await self._get_project_member(
            project_id, invite_data.user_id
        )
        if existing_member:
            raise ConflictError("User is already a member of this project")

        membership = ProjectMember(
            project_id=project_id,
            user_id=invite_data.user_id,
            role=invite_data.role,
            added_by=inviter_id,
        )

        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(membership)

        return membership

    async def update_project_member_role(
        self,
        project_id: UUID,
        user_id: UUID,
        update_data: ProjectMemberUpdate,
        updater_id: UUID,
    ) -> ProjectMember:
        """
        Update a project member's role.
        :param project_id: UUID of the project.
        :param user_id: UUproject.id, user_id):ID of the member to update.
        :param update_data: ProjectMemberUpdate schema containing new role.
        :param updater_id: UUID of the user performing the update.
        :return: Updated ProjectMember object.
        """
        project = await self.get_project_by_id(project_id)

        if not await self.can_user_manage_project_members(updater_id, project):
            raise ForbiddenException(
                "Insufficient permissions to update project members"
            )

        member = await self._get_project_member(project_id, user_id)
        if not member:
            raise NotFoundException(
                "ProjectMember", f"User {user_id} not found in project"
            )

        member.role = update_data.role
        await self.db.commit()
        await self.db.refresh(member)

        return member

    async def remove_project_member(
        self, project_id: UUID, user_id: UUID, remover_id: UUID
    ) -> ProjectMember:
        """
        Remove a member from a project.
        :param project_id: UUID of the project.
        :param user_id: UUID of the member to remove.
        :param remover_id: UUID of the user performing the removal.
        :return: Removed ProjectMember object.
        """
        project = await self.get_project_by_id(project_id)

        if not await self.can_user_manage_project_members(remover_id, project):
            raise ForbiddenException(
                "Insufficient permissions to remove project members"
            )

        member = await self._get_project_member(project_id, user_id)
        if not member:
            raise NotFoundException(
                "ProjectMember", f"User {user_id} not found in project"
            )

        if member.role == ProjectRole.LEAD:
            lead_count = len(
                [
                    m
                    for m in project.members
                    if m.role == ProjectRole.LEAD and m.user_id != user_id
                ]
            )
            if lead_count == 0 and project.lead_id == user_id:
                raise ValidationException("Cannot remove the last project lead")

        await self.db.delete(member)
        await self.db.commit()

        return member

    async def get_project_members(
        self, project_id: UUID, user_id: UUID
    ) -> List[ProjectMember]:
        """
        Get all members of a project.
        :param project_id: UUID of the project.
        :param user_id: UUID of the requesting user.
        :return: List of ProjectMember objects.
        """
        project = await self.get_project_by_id(project_id)

        # Check if user can view project
        if not await self.can_user_view_project(user_id, project):
            raise ForbiddenException("Insufficient permissions to view project members")

        stmt = (
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .options(selectinload(ProjectMember.user))
            .order_by(ProjectMember.added_at.desc())
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_project_stats(
        self, organization_id: UUID, user_id: UUID
    ) -> ProjectStats:
        """
        Get project statistics for an organization.
        :param organization_id: UUID of the organization.
        :param user_id: UUID of the requesting user.
        :return: ProjectStats object.
        """
        org_member = await self._get_organization_member(organization_id, user_id)
        if not org_member or not org_member.is_active:
            raise ForbiddenException("You are not a member of this organization")

        base_stmt = select(Project).where(
            Project.organization_id == organization_id, Project.deleted_at.is_(None)
        )

        total_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_projects = await self.db.scalar(total_stmt) or 0

        # Active projects
        active_stmt = select(func.count()).select_from(
            base_stmt.where(
                Project.status == ProjectStatus.ACTIVE, Project.archived_at.is_(None)
            ).subquery()
        )
        active_projects = await self.db.scalar(active_stmt) or 0

        completed_stmt = select(func.count()).select_from(
            base_stmt.where(Project.status == ProjectStatus.COMPLETED).subquery()
        )
        completed_projects = await self.db.scalar(completed_stmt) or 0

        overdue_stmt = select(func.count()).select_from(
            base_stmt.where(
                Project.due_date < datetime.now(UTC),
                Project.status != ProjectStatus.COMPLETED,
                Project.archived_at.is_(None),
            ).subquery()
        )
        overdue_projects = await self.db.scalar(overdue_stmt) or 0

        status_stmt = (
            select(Project.status, func.count(Project.id))
            .where(
                Project.organization_id == organization_id, Project.deleted_at.is_(None)
            )
            .group_by(Project.status)
        )
        status_result = await self.db.execute(status_stmt)
        projects_by_status = {
            status: count for status, count in status_result.fetchall()
        }

        priority_stmt = (
            select(Project.priority, func.count(Project.id))
            .where(
                Project.organization_id == organization_id, Project.deleted_at.is_(None)
            )
            .group_by(Project.priority)
        )
        priority_result = await self.db.execute(priority_stmt)
        projects_by_priority = {
            priority: count for priority, count in priority_result.fetchall()
        }

        # Average completion time (placeholder)
        avg_completion_time_days = None  # TODO: Calculate when we have task completion data https://github.com/Anvoria/smithy/issues/7

        return ProjectStats(
            total_projects=total_projects,
            active_projects=active_projects,
            completed_projects=completed_projects,
            overdue_projects=overdue_projects,
            projects_by_status=projects_by_status,
            projects_by_priority=projects_by_priority,
            avg_completion_time_days=avg_completion_time_days,
        )

    async def archive_project(self, project_id: UUID, user_id: UUID) -> Project:
        """
        Archive a project.
        :param project_id: UUID of the project to archive.
        :param user_id: UUID of the user performing the archival.
        :return: Archived Project object.
        """
        project = await self.get_project_by_id(project_id)

        if not await self.can_user_edit_project(user_id, project):
            raise ForbiddenException("Insufficient permissions to archive project")

        stmt = (
            update(Project)
            .where(Project.id == project_id)
            .values(archived_at=datetime.now(UTC), updated_at=datetime.now(UTC))
        )
        await self.db.execute(stmt)
        await self.db.commit()
        await self.db.refresh(project)

        return project

    async def restore_project(self, project_id: UUID, user_id: UUID) -> Project:
        """
        Restore an archived project.
        :param project_id: UUID of the project to restore.
        :param user_id: UUID of the user performing the restoration.
        :return: Restored Project object.
        """
        project = await self.get_project_by_id(project_id, include_deleted=True)

        if not await self.can_user_edit_project(user_id, project):
            raise ForbiddenException("Insufficient permissions to restore project")

        stmt = (
            update(Project)
            .where(Project.id == project_id)
            .values(archived_at=None, updated_at=datetime.now(UTC))
        )
        await self.db.execute(stmt)
        await self.db.commit()
        await self.db.refresh(project)

        return project

    async def delete_project(self, project_id: UUID, user_id: UUID) -> bool:
        """
        Soft delete a project.
        :param project_id: UUID of the project to delete.
        :param user_id: UUID of the user performing the deletion.
        :return: True if deletion was successful.
        """
        project = await self.get_project_by_id(project_id)

        org_member = await self._get_organization_member(
            project.organization_id, user_id
        )
        is_project_lead = project.lead_id == user_id
        is_org_admin = org_member and org_member.role in [
            OrganizationRole.OWNER,
            OrganizationRole.ADMIN,
        ]

        if not (is_project_lead or is_org_admin):
            raise ForbiddenException(
                "Only project leads or organization admins can delete projects"
            )

        stmt = (
            update(Project)
            .where(Project.id == project_id)
            .values(deleted_at=datetime.now(UTC), updated_at=datetime.now(UTC))
        )
        await self.db.execute(stmt)
        await self.db.commit()

        return True

    # Helper methods
    async def can_user_view_project(self, user_id: UUID, project: Project) -> bool:
        """
        Check if user can view a project.
        :param user_id: UUID of the user.
        :param project: Project object.
        :return: True if user can view project.
        """
        org_member = await self._get_organization_member(
            project.organization_id, user_id
        )
        if not org_member or not org_member.is_active:
            return False

        return project.can_user_access(user_id, str(org_member.role))

    async def can_user_edit_project(self, user_id: UUID, project: Project) -> bool:
        """
        Check if user can edit a project.
        :param user_id: UUID of the user.
        :param project: Project object.
        :return: True if user can edit project.
        """
        org_member = await self._get_organization_member(
            project.organization_id, user_id
        )
        if not org_member or not org_member.is_active:
            return False

        return project.can_user_edit(user_id, str(org_member.role))

    async def can_user_manage_project_members(
        self, user_id: UUID, project: Project
    ) -> bool:
        """
        Check if user can manage project members.
        :param user_id: UUID of the user.
        :param project: Project object.
        :return: True if user can manage project members.
        """
        org_member = await self._get_organization_member(
            project.organization_id, user_id
        )
        if not org_member or not org_member.is_active:
            return False

        return project.can_user_manage_tasks(user_id, str(org_member.role))

    async def _get_organization_member(
        self, organization_id: UUID, user_id: UUID
    ) -> Optional[OrganizationMember]:
        """Get organization member for user"""
        stmt = select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
        return await self.db.scalar(stmt)

    async def _get_project_member(
        self, project_id: UUID, user_id: UUID
    ) -> Optional[ProjectMember]:
        """Get project member for user"""
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
        )
        return await self.db.scalar(stmt)

    def _can_create_projects(self, org_role: OrganizationRole) -> bool:
        """Check if organization role can create projects"""
        return org_role in [
            OrganizationRole.OWNER,
            OrganizationRole.ADMIN,
            OrganizationRole.MANAGER,
            OrganizationRole.MEMBER,
        ]
