import logging
from datetime import datetime, UTC
from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.organization import Organization
from app.models.organization_member import (
    OrganizationMember,
    OrganizationRole,
    MemberStatus,
)
from app.models.user import User
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    MemberInvite,
    MemberUpdate,
)
from app.core.exceptions import (
    NotFoundException,
    ConflictError,
    ValidationException,
    ForbiddenException,
)
from app.services.common import CommonService

logger = logging.getLogger(__name__)


class OrganizationService:
    """Organization management service with member operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_organization_by_id(
        self, org_id: UUID, include_deleted: bool = False
    ) -> Organization:
        """
        Retrieve an organization by its ID.
        :param org_id: UUID of the organization to retrieve.
        :param include_deleted: Whether to include deleted organizations.
        :return: Organization object if found, otherwise raises NotFoundException.
        """
        stmt = select(Organization).where(Organization.id == org_id)

        if not include_deleted:
            stmt = stmt.where(Organization.deleted_at.is_(None))

        # Load relationships
        stmt = stmt.options(
            selectinload(Organization.members).selectinload(OrganizationMember.user),
            selectinload(Organization.projects),
        )

        org = await self.db.scalar(stmt)
        if not org:
            raise NotFoundException("Organization", str(org_id))

        return org

    async def get_organization_by_slug(
        self, slug: str, include_deleted: bool = False
    ) -> Optional[Organization]:
        """
        Retrieve an organization by its slug.
        :param slug: Slug of the organization to retrieve.
        :param include_deleted: Whether to include deleted organizations.
        :return: Organization object if found, otherwise None.
        """
        stmt = select(Organization).where(Organization.slug == slug)

        if not include_deleted:
            stmt = stmt.where(Organization.deleted_at.is_(None))

        stmt = stmt.options(
            selectinload(Organization.members).selectinload(OrganizationMember.user),
            selectinload(Organization.projects),
        )

        return await self.db.scalar(stmt)

    async def create_organization(
        self, org_data: OrganizationCreate, creator_id: UUID
    ) -> tuple[Organization, int, int]:
        """
        Create a new organization with the given data and assign the creator as an owner.
        :param org_data: OrganizationCreate schema containing organization details.
        :param creator_id: UUID of the user creating the organization.
        :return: Tuple of (Created Organization object, member_count, project_count).
        """
        # Check slug uniqueness
        existing_org = await self.get_organization_by_slug(org_data.slug)
        if existing_org:
            raise ConflictError(
                f"Organization with slug '{org_data.slug}' already exists"
            )

        settings_dict = CommonService.serialize_pydantic_to_dict(org_data.settings)
        features_dict = CommonService.serialize_pydantic_to_dict(org_data.features)

        # Create organization
        org = Organization(
            name=org_data.name,
            slug=org_data.slug,
            display_name=org_data.display_name,
            description=org_data.description,
            org_type=org_data.org_type,
            company_size=org_data.company_size,
            website_url=org_data.website_url,
            contact_email=org_data.contact_email,
            timezone=org_data.timezone,
            brand_color=org_data.brand_color,
            max_members=org_data.max_members,
            max_projects=org_data.max_projects,
            max_storage_gb=org_data.max_storage_gb,
            require_2fa=org_data.require_2fa,
            public_projects=org_data.public_projects,
            settings=settings_dict or {},
            features=features_dict or {},
        )

        self.db.add(org)
        await self.db.flush()  # Get org.id

        # Add creator as owner
        owner_membership = OrganizationMember(
            user_id=creator_id,
            organization_id=org.id,
            role=OrganizationRole.OWNER,
            status=MemberStatus.ACTIVE,
            joined_at=datetime.now(UTC),
        )

        self.db.add(owner_membership)
        await self.db.commit()
        await self.db.refresh(org)

        return org, 1, 0

    async def update_organization(
        self, org_id: UUID, update_data: OrganizationUpdate, user_id: UUID
    ) -> Organization:
        """
        Update an existing organization with the provided data.
        :param org_id: UUID of the organization to update.
        :param update_data: OrganizationUpdate schema containing fields to update.
        :param user_id: UUID of the user performing the update.
        :return: Updated Organization object.
        """
        org = await self.get_organization_by_id(org_id)

        # Check permissions
        if not await self.can_user_manage_organization(user_id, org):
            raise ForbiddenException("Insufficient permissions to update organization")

        # Check slug uniqueness if being updated
        if update_data.slug and update_data.slug != org.slug:
            existing_org = await self.get_organization_by_slug(update_data.slug)
            if existing_org and existing_org.id != org_id:
                raise ConflictError(
                    f"Organization with slug '{update_data.slug}' already exists"
                )

        # Update fields
        update_values: dict = {}
        for field, value in update_data.model_dump(exclude_unset=True).items():
            if hasattr(org, field) and value is not None:
                if field in ["settings", "features"]:
                    update_values[field] = CommonService.serialize_pydantic_to_dict(
                        value
                    )
                else:
                    update_values[field] = value

        if update_values:
            update_values["updated_at"] = datetime.now(UTC)

            stmt = (
                update(Organization)
                .where(Organization.id == org_id)
                .values(**update_values)
            )
            await self.db.execute(stmt)
            await self.db.commit()
            await self.db.refresh(org)

        return org

    async def get_user_organizations(
        self, user_id: UUID, include_pending: bool = False
    ) -> List[Organization]:
        """
        Retrieve all organizations that a user is a member of.
        :param user_id: UUID of the user to retrieve organizations for.
        :param include_pending: Whether to include organizations with pending membership status.
        :return: List of Organization objects the user is a member of.
        """
        stmt = (
            select(Organization)
            .join(OrganizationMember)
            .where(
                OrganizationMember.user_id == user_id, Organization.deleted_at.is_(None)
            )
        )

        if not include_pending:
            stmt = stmt.where(OrganizationMember.status == MemberStatus.ACTIVE)

        stmt = stmt.options(
            selectinload(Organization.members).selectinload(OrganizationMember.user)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_organization_member(
        self, org_id: UUID, user_id: UUID
    ) -> Optional[OrganizationMember]:
        """
        Retrieve an organization member by organization ID and user ID.
        :param org_id: UUID of the organization.
        :param user_id: UUID of the user.
        :return: OrganizationMember object if found, otherwise None.
        """
        stmt = (
            select(OrganizationMember)
            .where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id,
            )
            .options(selectinload(OrganizationMember.user))
        )
        return await self.db.scalar(stmt)

    async def get_organization_members(
        self, org_id: UUID, include_inactive: bool = False
    ) -> List[OrganizationMember]:
        """
        Retrieve all members of an organization.
        :param org_id: UUID of the organization to retrieve members for.
        :param include_inactive: Whether to include inactive members.
        :return: List of OrganizationMember objects.
        """
        stmt = (
            select(OrganizationMember)
            .where(OrganizationMember.organization_id == org_id)
            .options(selectinload(OrganizationMember.user))
        )

        if not include_inactive:
            stmt = stmt.where(OrganizationMember.status == MemberStatus.ACTIVE)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # Member management operations
    async def update_member_role(
        self, org_id: UUID, user_id: UUID, update_data: MemberUpdate, updater_id: UUID
    ) -> OrganizationMember:
        """
        Update the role of a member in an organization.
        :param org_id: UUID of the organization.
        :param user_id: UUID of the user whose role is being updated.
        :param update_data: MemberUpdate schema containing new role and status.
        :param updater_id: UUID of the user performing the update.
        :return: Updated OrganizationMember object.
        """
        org = await self.get_organization_by_id(org_id)

        # Check permissions
        if not await self.can_user_manager_members(updater_id, org):
            raise ForbiddenException("Insufficient permissions to update member roles")

        member = await self.get_organization_member(org_id, user_id)
        if not member:
            raise NotFoundException(
                "Member", f"User {user_id} not found in organization {org_id}"
            )

        # Prevent role downgrade for last owner
        if (
            member.role == OrganizationRole.OWNER
            and update_data.role != OrganizationRole.OWNER
        ):
            owner_count = len(
                [m for m in org.members if m.role == OrganizationRole.OWNER]
            )
            if owner_count <= 1:
                raise ValidationException(
                    "Cannot downgrade last owner of the organization"
                )

        member.role = update_data.role
        await self.db.commit()
        await self.db.refresh(member)

        return member

    async def remove_member(
        self, org_id: UUID, user_id: UUID, remover_id: UUID
    ) -> OrganizationMember:
        """
        Remove a member from an organization.
        :param org_id: UUID of the organization.
        :param user_id: UUID of the user to remove.
        :param remover_id: UUID of the user performing the removal.
        :return: Removed OrganizationMember object.
        """
        org = await self.get_organization_by_id(org_id)

        # Check permissions
        if not await self.can_user_manager_members(remover_id, org):
            raise ForbiddenException("Insufficient permissions to remove members")

        member = await self.get_organization_member(org_id, user_id)
        if not member:
            raise NotFoundException(
                "Member", f"User {user_id} not found in organization {org_id}"
            )

        # Prevent removing last owner
        if member.role == OrganizationRole.OWNER:
            owner_count = len(
                [m for m in org.members if m.role == OrganizationRole.OWNER]
            )
            if owner_count <= 1:
                raise ValidationException("Cannot remove the last owner")

        await self.db.delete(member)
        await self.db.commit()

        return member

    async def leave_organization(
        self, org_id: UUID, user_id: UUID
    ) -> OrganizationMember:
        """
        Allow a user to leave an organization.
        :param org_id: UUID of the organization to leave.
        :param user_id: UUID of the user leaving the organization.
        :return: OrganizationMember object representing the left membership.
        """
        org = await self.get_organization_by_id(org_id)

        member = await self.get_organization_member(org_id, user_id)
        if not member:
            raise NotFoundException(
                "Member", f"User {user_id} not found in organization {org_id}"
            )

        # Prevent leaving if user is the last owner
        if member.role == OrganizationRole.OWNER:
            owner_count = len(
                [m for m in org.members if m.role == OrganizationRole.OWNER]
            )
            if owner_count <= 1:
                raise ValidationException("Cannot leave as the last owner")

        member.status = MemberStatus.LEFT
        await self.db.commit()

        return member

    # Invites
    async def invite_member(
        self, org_id: UUID, invite_data: MemberInvite, inviter_id: UUID
    ) -> OrganizationMember:
        """
        Invite a new member to the organization.
        :param org_id: UUID of the organization to invite the member to.
        :param invite_data: MemberInvite schema containing user details and role.
        :param inviter_id: UUID of the user sending the invitation.
        :return: OrganizationMember object representing the invited member.
        """
        org = await self.get_organization_by_id(org_id)

        # CHeck permissions
        if not await self.can_user_manager_members(inviter_id, org):
            raise ForbiddenException("Insufficient permissions to invite members")

        if not org.can_add_member():
            raise ValidationException("Organization has reached its member limit")

        user_stmt = select(User).where(User.email == invite_data.email)
        user = await self.db.scalar(user_stmt)
        if not user:
            raise NotFoundException("User", str(invite_data.email))

        # Check if user is already a member
        existing_member = await self.get_organization_member(org_id, user.id)
        if existing_member:
            if existing_member.status == MemberStatus.PENDING:
                raise ConflictError("User is already invited to this organization")
            else:
                raise ConflictError("User is already a member of this organization")

        membership = OrganizationMember(
            user_id=user.id,
            organization_id=org_id,
            role=invite_data.role,
            status=MemberStatus.PENDING,
            invited_by=inviter_id,
            joined_at=datetime.now(UTC),
        )

        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(membership)

        return membership

    async def accept_invitation(
        self, org_id: UUID, user_id: UUID
    ) -> OrganizationMember:
        """
        Accept an invitation to join an organization.
        :param org_id: UUID of the organization to accept the invitation for.
        :param user_id: UUID of the user accepting the invitation.
        :return: OrganizationMember object representing the accepted membership.
        """
        membership = await self.get_organization_member(org_id, user_id)
        if not membership:
            raise NotFoundException(
                "Invitation", f"User {user_id} not invited to organization {org_id}"
            )

        if membership.status != MemberStatus.PENDING:
            raise ValidationException("Invitation is not pending")

        # Update membership status to active
        membership.status = MemberStatus.ACTIVE
        membership.joined_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(membership)

        return membership

    # Helper functions
    async def can_user_manage_organization(
        self, user_id: UUID, org: Organization
    ) -> bool:
        """
        Check if a user can manage the organization.
        :param user_id: UUID of the user to check.
        :param org: Organization object to check permissions against.
        :return: True if the user can manage the organization, False otherwise.
        """
        member = await self.get_organization_member(org.id, user_id)
        if not member or not member.is_active:
            return False

        return member.role in [
            OrganizationRole.OWNER,
            OrganizationRole.ADMIN,
        ]  # TODO https://github.com/Anvoria/smithy/issues/6

    async def can_user_manager_members(self, user_id: UUID, org: Organization) -> bool:
        """
        Check if a user can manage members of the organization.
        :param user_id: UUID of the user to check.
        :param org: Organization object to check permissions against.
        :return: True if the user can manage members, False otherwise.
        """
        member = await self.get_organization_member(org.id, user_id)
        if not member or not member.is_active:
            return False

        return (
            member.can_manage_members
        )  # TODO https://github.com/Anvoria/smithy/issues/6

    async def get_user_role_in_organization(
        self, user_id: UUID, org_id: UUID
    ) -> Optional[OrganizationRole]:
        """
        Get the role of a user in a specific organization.
        :param user_id: UUID of the user.
        :param org_id: UUID of the organization.
        :return: OrganizationRole if the user is a member, otherwise None.
        """
        member = await self.get_organization_member(org_id, user_id)
        return member.role if member else None

    # Organization deletion
    async def delete_organization(self, org_id: UUID, user_id: UUID) -> bool:
        """
        Soft delete an organization.
        :param org_id: UUID of the organization to delete.
        :param user_id: UUID of the user performing the deletion.
        :return: True if deletion was successful, otherwise raises an exception.
        """
        org = await self.get_organization_by_id(org_id)
        if not org:
            raise NotFoundException("Organization", str(org_id))

        # Check if user is owner
        member = await self.get_organization_member(org_id, user_id)
        if not member or member.role != OrganizationRole.OWNER:
            raise ForbiddenException(
                "Only organization owners can delete organizations"
            )

        # Soft delete
        stmt = (
            update(Organization)
            .where(Organization.id == org_id)
            .values(deleted_at=datetime.now(UTC), updated_at=datetime.now(UTC))
        )
        await self.db.execute(stmt)
        await self.db.commit()

        return True
