import magic
import logging
from typing import Optional, Set
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.core.storage.factory import get_storage_provider
from app.models.task import TaskAttachment
from app.models.organization import Organization
from app.models.project import Project
from app.models.organization_member import OrganizationMember, OrganizationRole
from app.core.exceptions import (
    ValidationException,
    ForbiddenException,
    NotFoundException,
)
from app.models.task import Task
from app.services.project_service import ProjectService
from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Service for handling file uploads and storage operations"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage_provider = get_storage_provider()

        self.max_file_size_mb = settings.MAX_FILE_SIZE_MB
        self.max_logo_size_mb = settings.MAX_LOGO_SIZE_MB

        self.allowed_image_types = self._parse_allowed_types(
            getattr(
                settings,
                "ALLOWED_FILE_TYPES",
                "image/jpeg,image/png,image/gif,image/webp",
            )
        )
        self.allowed_document_types = self._parse_allowed_types(
            settings.ALLOWED_DOCUMENT_TYPES
        )
        self.allowed_archive_types = self._parse_allowed_types(
            settings.ALLOWED_ARCHIVE_TYPES
        )

        self.local_storage_path = settings.LOCAL_STORAGE_PATH

    def _parse_allowed_types(self, types_str: str) -> Set[str]:
        """Parse comma-separated string of allowed types"""
        return set(t.strip() for t in types_str.split(",") if t.strip())

    async def upload_organization_logo(
        self,
        organization_id: UUID,
        file: UploadFile,
        current_user_id: UUID,
        logo_type: str = "logo",
    ) -> str | None:
        """
        Upload organization logo/avatar/banner.

        :param organization_id: ID of organization
        :param file: Uploaded file
        :param current_user_id: ID of current user
        :param logo_type: Type of logo ('logo', 'avatar', 'banner')
        :return: Public URL of uploaded logo
        """
        if logo_type not in ["logo", "avatar", "banner"]:
            raise ValidationException(
                "Invalid logo type. Must be 'logo', 'avatar', or 'banner'"
            )

        if not await self._can_user_manage_organization(
            current_user_id, organization_id
        ):
            raise ForbiddenException(
                "Insufficient permissions to upload organization media"
            )

        stmt = select(Organization).where(Organization.id == organization_id)
        org = await self.db.scalar(stmt)
        if not org:
            raise NotFoundException("Organization", str(organization_id))

        max_size = (
            self.max_logo_size_mb if logo_type == "logo" else self.max_file_size_mb
        )
        await self._validate_file(
            file, allowed_types=self.allowed_image_types, max_size_mb=max_size
        )

        old_url = getattr(org, f"{logo_type}_url", None)
        if old_url:
            old_file_path = self._extract_file_path_from_url(old_url)
            if old_file_path:
                await self.storage_provider.delete(old_file_path)

        content = await file.read()

        metadata = await self.storage_provider.upload(
            file=content,
            filename=file.filename or f"{logo_type}.jpg",
            content_type=file.content_type or "image/jpeg",
            folder=f"organizations/{organization_id}/{logo_type}s",
            public=True,
        )

        update_data = {f"{logo_type}_url": metadata.public_url}
        stmt = (
            update(Organization)
            .where(Organization.id == organization_id)
            .values(**update_data)
        )
        await self.db.execute(stmt)
        await self.db.commit()

        return metadata.public_url

    async def upload_task_attachment(
        self, task_id: UUID, file: UploadFile, current_user_id: UUID
    ) -> TaskAttachment:
        """
        Upload task attachment.

        :param task_id: ID of task to attach file to
        :param file: Uploaded file
        :param current_user_id: ID of current user
        :return: Created TaskAttachment object
        """
        if not await self._can_user_access_task(current_user_id, task_id):
            raise ForbiddenException("Insufficient permissions to upload to this task")

        allowed_types = (
            self.allowed_image_types
            | self.allowed_document_types
            | self.allowed_archive_types
        )

        await self._validate_file(
            file, allowed_types=allowed_types, max_size_mb=self.max_file_size_mb
        )

        content = await file.read()

        metadata = await self.storage_provider.upload(
            file=content,
            filename=file.filename or "attachment",
            content_type=file.content_type or "application/octet-stream",
            folder=f"tasks/{task_id}/attachments",
            public=False,
        )

        attachment = TaskAttachment(
            task_id=task_id,
            uploaded_by=current_user_id,
            filename=file.filename or "attachment",
            file_path=metadata.file_path,
            file_size=metadata.file_size,
            content_type=metadata.content_type,
        )

        self.db.add(attachment)
        await self.db.commit()
        await self.db.refresh(attachment)

        return attachment

    async def delete_task_attachment(
        self, attachment_id: UUID, current_user_id: UUID
    ) -> bool:
        """
        Delete task attachment.

        :param attachment_id: ID of attachment to delete
        :param current_user_id: ID of current user
        :return: True if deletion was successful
        """
        stmt = select(TaskAttachment).where(TaskAttachment.id == attachment_id)
        attachment = await self.db.scalar(stmt)
        if not attachment:
            raise NotFoundException("Attachment", str(attachment_id))

        if attachment.uploaded_by != current_user_id:
            if not await self._can_user_edit_task(current_user_id, attachment.task_id):
                raise ForbiddenException(
                    "Insufficient permissions to delete this attachment"
                )

        deleted = await self.storage_provider.delete(attachment.file_path)
        if not deleted:
            logger.warning(
                f"Failed to delete file from storage: {attachment.file_path}"
            )

        await self.db.delete(attachment)
        await self.db.commit()

        logger.info(f"Task attachment deleted: {attachment_id}")
        return True

    async def get_file_download_url(
        self, attachment_id: UUID, current_user_id: UUID
    ) -> str:
        """
        Get download URL for task attachment.

        :param attachment_id: ID of attachment
        :param current_user_id: ID of current user
        :return: Download URL
        """
        stmt = select(TaskAttachment).where(TaskAttachment.id == attachment_id)
        attachment = await self.db.scalar(stmt)
        if not attachment:
            raise NotFoundException("Attachment", str(attachment_id))

        if not await self._can_user_access_task(current_user_id, attachment.task_id):
            raise ForbiddenException(
                "Insufficient permissions to access this attachment"
            )

        return await self.storage_provider.get_public_url(attachment.file_path)

    async def _validate_file(
        self, file: UploadFile, allowed_types: Set[str], max_size_mb: int
    ) -> None:
        """
        Validate uploaded file.

        :param file: Uploaded file
        :param allowed_types: Set of allowed MIME types
        :param max_size_mb: Maximum file size in MB
        """
        if not file:
            raise ValidationException("No file provided")

        if not file.filename:
            raise ValidationException("Filename is required")

        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)

        if file_size == 0:
            raise ValidationException("File is empty")

        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            raise ValidationException(
                f"File too large. Maximum size is {max_size_mb}MB"
            )

        # Check content type
        if file.content_type not in allowed_types:
            content_chunk = await file.read(2048)
            await file.seek(0)

            try:
                detected_type = magic.from_buffer(content_chunk, mime=True)
                if detected_type not in allowed_types:
                    raise ValidationException(
                        f"File type not allowed. Detected: {detected_type}. "
                        f"Allowed types: {', '.join(sorted(allowed_types))}"
                    )
            except Exception:
                raise ValidationException(
                    f"Could not validate file type. "
                    f"Allowed types: {', '.join(sorted(allowed_types))}"
                )

    async def _can_user_manage_organization(
        self, user_id: UUID, organization_id: UUID
    ) -> bool:
        """
        Check if user can manage organization (upload logos, etc.).

        :param user_id: ID of user
        :param organization_id: ID of organization
        :return: True if user can manage organization
        """
        stmt = select(OrganizationMember).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
        )
        member = await self.db.scalar(stmt)

        if not member:
            return False

        return member.role in [OrganizationRole.OWNER, OrganizationRole.ADMIN]

    async def _can_user_access_task(self, user_id: UUID, task_id: UUID) -> bool:
        """
        Check if user can access task.

        :param user_id: ID of user
        :param task_id: ID of task
        :return: True if user can access task
        """
        # Get task with project and organization loaded
        stmt = (
            select(Task)
            .where(Task.id == task_id)
            .options(
                selectinload(Task.project).selectinload(Project.organization),
                selectinload(Task.project).selectinload(Project.members),
            )
        )
        task = await self.db.scalar(stmt)

        if not task:
            return False

        project_service = ProjectService(self.db)

        return await project_service.can_user_view_project(user_id, task.project)

    async def _can_user_edit_task(self, user_id: UUID, task_id: UUID) -> bool:
        """
        Check if user can edit task.

        :param user_id: ID of user
        :param task_id: ID of task
        :return: True if user can edit task
        """
        # Get task with relationships
        stmt = (
            select(Task)
            .where(Task.id == task_id)
            .options(
                selectinload(Task.project).selectinload(Project.organization),
                selectinload(Task.project).selectinload(Project.members),
                selectinload(Task.assignees),
            )
        )
        task = await self.db.scalar(stmt)

        if not task:
            return False

        if task.reporter_id == user_id:
            return True

        for assignee in task.assignees:
            if assignee.user_id == user_id:
                return True

        project = task.project

        if project.lead_id == user_id:
            return True

        project_member = project.get_user_project_membership(user_id)
        if project_member and project_member.can_manage_tasks:
            return True

        org_member_stmt = select(OrganizationMember).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == project.organization_id,
        )
        org_member = await self.db.scalar(org_member_stmt)

        if org_member and org_member.is_active:
            if str(org_member.role) in ["owner", "admin"]:
                return True

            if str(org_member.role) == "manager" and project_member:
                return True

        return False

    def _extract_file_path_from_url(self, url: str) -> Optional[str]:
        """
        Extract file path from storage URL for deletion.

        :param url: Storage URL
        :return: File path or None if not extractable
        """
        if not url:
            return None

        if f"/{self.local_storage_path}/" in url:
            return url.split(f"/{self.local_storage_path}/", 1)[1]

        return None
