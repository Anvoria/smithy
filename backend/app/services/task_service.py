import logging
from datetime import datetime, UTC
from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, or_, delete
from sqlalchemy.orm import selectinload

from app.models.task import (
    Task,
    TaskStatus,
    TaskAssignee,
    TaskDependency,
    TaskComment,
    TaskTimeLog,
)
from app.models.project import Project
from app.models.project_member import ProjectMember, ProjectRole
from app.models.organization_member import OrganizationMember, OrganizationRole
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskStatusUpdate,
    TaskAssigneeCreate,
    TaskCommentCreate,
    TaskTimeLogCreate,
    TaskFilters,
    TaskBulkUpdate,
    TaskStats,
)
from app.core.exceptions import (
    NotFoundException,
    ConflictError,
    ValidationException,
    ForbiddenException,
)

logger = logging.getLogger(__name__)


class TaskService:
    """Task management service with comprehensive CRUD operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_task_by_id(
        self, task_id: UUID, include_deleted: bool = False
    ) -> Task:
        """
        Retrieve a task by its ID with optional loading of related entities.
        :param task_id: UUID of the task to retrieve.
        :param include_deleted: Whether to include soft-deleted tasks.
        :return: Task object with related entities loaded.
        """
        stmt = select(Task).where(Task.id == task_id)

        if not include_deleted:
            stmt = stmt.where(Task.deleted_at.is_(None))

        stmt = stmt.options(
            selectinload(Task.project),
            selectinload(Task.reporter),
            selectinload(Task.assignees).selectinload(TaskAssignee.user),
            selectinload(Task.parent_task),
            selectinload(Task.subtasks),
            selectinload(Task.comments).selectinload(TaskComment.author),
            selectinload(Task.time_logs).selectinload(TaskTimeLog.user),
        )

        task = await self.db.scalar(stmt)
        if not task:
            raise NotFoundException("Task", str(task_id))

        return task

    async def get_task_by_project_and_number(
        self, project_id: UUID, task_number: int, include_deleted: bool = False
    ) -> Optional[Task]:
        """
        Retrieve a task by project ID and task number (e.g., PROJECT-123).
        :param project_id: UUID of the project.
        :param task_number: Task number within the project.
        :param include_deleted: Whether to include soft-deleted tasks.
        :return: Task object if found, otherwise None.
        """
        stmt = select(Task).where(
            Task.project_id == project_id, Task.task_number == task_number
        )

        if not include_deleted:
            stmt = stmt.where(Task.deleted_at.is_(None))

        stmt = stmt.options(
            selectinload(Task.project),
            selectinload(Task.reporter),
            selectinload(Task.assignees).selectinload(TaskAssignee.user),
        )

        return await self.db.scalar(stmt)

    async def create_task(self, task_data: TaskCreate, creator_id: UUID) -> Task:
        """
        Create a new task with assignments and proper numbering.
        :param task_data: TaskCreate schema containing task details.
        :param creator_id: UUID of the user creating the task.
        :return: Created Task object with relationships loaded.
        """
        await self._get_project_with_permissions(task_data.project_id, creator_id)

        if task_data.parent_task_id:
            parent_task = await self.get_task_by_id(task_data.parent_task_id)
            if parent_task.project_id != task_data.project_id:
                raise ValidationException("Parent task must be in the same project")

        next_number_stmt = select(
            func.coalesce(func.max(Task.task_number), 0) + 1
        ).where(Task.project_id == task_data.project_id)
        task_number = await self.db.scalar(next_number_stmt)

        # Validate assignees are project members
        valid_assignees = []
        if task_data.assignee_ids:
            valid_assignees = await self._validate_assignees(
                task_data.assignee_ids, task_data.project_id
            )

        # Create task
        task = Task(
            title=task_data.title,
            description=task_data.description,
            project_id=task_data.project_id,
            task_number=task_number,
            parent_task_id=task_data.parent_task_id,
            reporter_id=creator_id,
            priority=task_data.priority,
            task_type=task_data.task_type,
            due_date=task_data.due_date,
            start_date=task_data.start_date,
            estimated_hours=task_data.estimated_hours,
            story_points=task_data.story_points,
            labels=task_data.labels or [],
            custom_fields=task_data.custom_fields or {},
        )

        self.db.add(task)
        await self.db.flush()

        # Create task assignments
        for assignee_id in valid_assignees:
            assignment = TaskAssignee(
                task_id=task.id,
                user_id=assignee_id,
                assigned_by=creator_id,
            )
            self.db.add(assignment)

        await self.db.commit()

        return await self.get_task_by_id(task.id)

    async def update_task(
        self, task_id: UUID, update_data: TaskUpdate, user_id: UUID
    ) -> Task:
        """
        Update an existing task with permission checks.
        :param task_id: UUID of the task to update.
        :param update_data: TaskUpdate schema containing fields to update.
        :param user_id: UUID of the user performing the update.
        :return: Updated Task object with relationships loaded.
        """
        task = await self.get_task_by_id(task_id)

        # Check permissions
        if not await self._can_user_edit_task(user_id, task):
            raise ForbiddenException("Insufficient permissions to update this task")

        # Handle assignee updates
        if update_data.assignee_ids is not None:
            await self._update_task_assignees(
                task_id, update_data.assignee_ids, user_id
            )

        # Prepare update values
        update_values: Dict[str, Any] = {}
        for field, value in update_data.model_dump(
            exclude_unset=True, exclude={"assignee_ids"}
        ).items():
            if hasattr(task, field) and value is not None:
                update_values[field] = value

        if update_data.status and update_data.status != task.status:
            update_values["status"] = update_data.status
            if update_data.status == TaskStatus.DONE and not task.completed_at:
                update_values["completed_at"] = datetime.now(UTC)
            elif update_data.status != TaskStatus.DONE and task.completed_at:
                update_values["completed_at"] = None

        if update_values:
            update_values["updated_at"] = datetime.now(UTC)

            stmt = update(Task).where(Task.id == task_id).values(**update_values)
            await self.db.execute(stmt)
            await self.db.commit()

        return await self.get_task_by_id(task_id)

    async def update_task_status(
        self, task_id: UUID, status_data: TaskStatusUpdate, user_id: UUID
    ) -> Task:
        """
        Update task status with optional comment.
        :param task_id: UUID of the task to update.
        :param status_data: TaskStatusUpdate schema containing new status and optional comment.
        :param user_id: UUID of the user performing the update.
        :return: Updated Task object with relationships loaded.
        """
        task = await self.get_task_by_id(task_id)

        if not await self._can_user_edit_task(user_id, task):
            raise ForbiddenException("Insufficient permissions to update task status")

        old_status = task.status
        update_values: Dict[str, Any] = {
            "status": status_data.status,
            "updated_at": datetime.now(UTC),
        }

        # Handle completion
        if status_data.status == TaskStatus.DONE and not task.completed_at:
            update_values["completed_at"] = datetime.now(UTC)
        elif status_data.status != TaskStatus.DONE and task.completed_at:
            update_values["completed_at"] = None

        stmt = update(Task).where(Task.id == task_id).values(**update_values)
        await self.db.execute(stmt)

        # Add comment if provided
        if status_data.comment:
            comment_content = f"Status changed from {old_status.value} to {status_data.status.value}\n\n{status_data.comment}"
            await self.create_task_comment(
                task_id,
                TaskCommentCreate(content=comment_content, parent_comment_id=None),
                user_id,
            )

        await self.db.commit()
        return await self.get_task_by_id(task_id)

    async def delete_task(self, task_id: UUID, user_id: UUID) -> bool:
        """
        Soft delete a task with permission checks.
        :param task_id: UUID of the task to delete.
        :param user_id: UUID of the user performing the delete.
        :return: True if deletion was successful, otherwise raises an exception.
        """
        task = await self.get_task_by_id(task_id)

        if not await self._can_user_delete_task(user_id, task):
            raise ForbiddenException("Insufficient permissions to delete this task")

        # Soft delete
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .values(deleted_at=datetime.now(UTC), updated_at=datetime.now(UTC))
        )
        await self.db.execute(stmt)
        await self.db.commit()

        return True

    async def get_project_tasks(
        self,
        project_id: UUID,
        user_id: UUID,
        filters: TaskFilters,
        page: int = 1,
        size: int = 50,
    ) -> Tuple[List[Task], int]:
        """
        Get tasks for a project with filtering and pagination.
        :param project_id: UUID of the project to retrieve tasks for.
        :param user_id: UUID of the user requesting the tasks.
        :param filters: TaskFilters schema containing filter criteria.
        :param page: Page number for pagination.
        :param size: Number of tasks per page.
        :return: Tuple containing list of Task objects and total count of tasks.
        """
        await self._get_project_with_permissions(project_id, user_id)

        # Build base query
        stmt = select(Task).where(
            Task.project_id == project_id, Task.deleted_at.is_(None)
        )

        stmt = self._apply_task_filters(stmt, filters)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = await self.db.scalar(count_stmt)

        offset = (page - 1) * size
        stmt = (
            stmt.offset(offset)
            .limit(size)
            .order_by(Task.created_at.desc())
            .options(
                selectinload(Task.project),
                selectinload(Task.reporter),
                selectinload(Task.assignees).selectinload(TaskAssignee.user),
            )
        )

        result = await self.db.execute(stmt)
        tasks = result.scalars().all()

        return list(tasks), total_count or 0

    async def get_user_tasks(
        self, user_id: UUID, filters: TaskFilters, page: int = 1, size: int = 50
    ) -> Tuple[List[Task], int]:
        """
        Get tasks assigned to or reported by a user.
        :param user_id: UUID of the user to retrieve tasks for.
        :param filters: TaskFilters schema containing filter criteria.
        :param page: Page number for pagination.
        :param size: Number of tasks per page.
        :return: Tuple containing list of Task objects and total count of tasks.
        """
        stmt = select(Task).where(
            Task.deleted_at.is_(None),
            or_(
                Task.reporter_id == user_id,
                Task.assignees.any(TaskAssignee.user_id == user_id),
            ),
        )

        # Apply filters
        stmt = self._apply_task_filters(stmt, filters)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = await self.db.scalar(count_stmt)

        # Apply pagination
        offset = (page - 1) * size
        stmt = (
            stmt.offset(offset)
            .limit(size)
            .order_by(Task.updated_at.desc())
            .options(
                selectinload(Task.project),
                selectinload(Task.reporter),
                selectinload(Task.assignees).selectinload(TaskAssignee.user),
            )
        )

        result = await self.db.execute(stmt)
        tasks = result.scalars().all()

        return list(tasks), total_count or 0

    async def assign_users_to_task(
        self, task_id: UUID, assignee_data: TaskAssigneeCreate, assigner_id: UUID
    ) -> List[TaskAssignee]:
        """
        Assign users to a task, replacing existing assignments.
        :param task_id: UUID of the task to assign users
        :param assignee_data: TaskAssigneeCreate schema containing user IDs and optional comment.
        :param assigner_id: UUID of the user performing the assignment.
        :return: List of TaskAssignee objects representing current assignments.
        """
        task = await self.get_task_by_id(task_id)

        if not await self._can_user_edit_task(assigner_id, task):
            raise ForbiddenException(
                "Insufficient permissions to assign users to this task"
            )

        valid_assignees = await self._validate_assignees(
            assignee_data.user_ids, task.project_id
        )

        await self._update_task_assignees(task_id, valid_assignees, assigner_id)

        if assignee_data.comment:
            await self.create_task_comment(
                task_id,
                TaskCommentCreate(
                    content=f"Assignment updated: {assignee_data.comment}"
                ),
                assigner_id,
            )

        await self.db.commit()

        stmt = (
            select(TaskAssignee)
            .where(TaskAssignee.task_id == task_id)
            .options(
                selectinload(TaskAssignee.user), selectinload(TaskAssignee.assigner)
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_task_comment(
        self, task_id: UUID, comment_data: TaskCommentCreate, author_id: UUID
    ) -> TaskComment:
        """
        Create a comment on a task.
        :param task_id: UUID of the task to comment on.
        :param comment_data: TaskCommentCreate schema containing comment content and optional parent comment ID.
        :param author_id: UUID of the user creating the comment.
        :return: Created TaskComment object with relationships loaded.
        """
        task = await self.get_task_by_id(task_id)

        if not await self.can_user_view_task(author_id, task):
            raise ForbiddenException("Insufficient permissions to comment on this task")

        if comment_data.parent_comment_id:
            parent_stmt = select(TaskComment).where(
                TaskComment.id == comment_data.parent_comment_id,
                TaskComment.task_id == task_id,
                TaskComment.deleted_at.is_(None),
            )
            parent_comment = await self.db.scalar(parent_stmt)
            if not parent_comment:
                raise NotFoundException(
                    "Parent comment", str(comment_data.parent_comment_id)
                )

        comment = TaskComment(
            task_id=task_id,
            author_id=author_id,
            content=comment_data.content,
            parent_comment_id=comment_data.parent_comment_id,
        )

        self.db.add(comment)
        await self.db.commit()
        await self.db.refresh(comment)

        stmt = (
            select(TaskComment)
            .where(TaskComment.id == comment.id)
            .options(selectinload(TaskComment.author))
        )
        return await self.db.scalar(stmt)

    async def get_task_comments(
        self, task_id: UUID, user_id: UUID, page: int = 1, size: int = 50
    ) -> Tuple[List[TaskComment], int]:
        """
        Get comments for a task.
        :param task_id: UUID of the task to retrieve comments for.
        :param user_id: UUID of the user requesting the comments.
        :param page: Page number for pagination.
        :param size: Number of comments per page.
        :return: Tuple containing list of TaskComment objects and total count of comments.
        """
        task = await self.get_task_by_id(task_id)

        if not await self.can_user_view_task(user_id, task):
            raise ForbiddenException("Insufficient permissions to view task comments")

        stmt = select(TaskComment).where(
            TaskComment.task_id == task_id, TaskComment.deleted_at.is_(None)
        )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = await self.db.scalar(count_stmt)

        # Apply pagination
        offset = (page - 1) * size
        stmt = (
            stmt.offset(offset)
            .limit(size)
            .order_by(TaskComment.created_at.desc())
            .options(selectinload(TaskComment.author))
        )

        result = await self.db.execute(stmt)
        comments = result.scalars().all()

        return list(comments), total_count or 0

    async def log_time_to_task(
        self, task_id: UUID, time_log_data: TaskTimeLogCreate, user_id: UUID
    ) -> TaskTimeLog:
        """
        Log time spent on a task.
        :param task_id: UUID of the task to log time for.
        :param time_log_data: TaskTimeLogCreate schema containing hours, description, and optional date worked.
        :param user_id: UUID of the user logging time.
        :return: Created TaskTimeLog object with relationships loaded.
        """
        task = await self.get_task_by_id(task_id)

        if not await self.can_user_view_task(user_id, task):
            raise ForbiddenException(
                "Insufficient permissions to log time on this task"
            )

        time_log = TaskTimeLog(
            task_id=task_id,
            user_id=user_id,
            hours=time_log_data.hours,
            description=time_log_data.description,
            date_worked=time_log_data.date_worked or datetime.now(UTC),
        )

        self.db.add(time_log)

        total_hours_stmt = select(func.sum(TaskTimeLog.hours)).where(
            TaskTimeLog.task_id == task_id
        )
        current_total = await self.db.scalar(total_hours_stmt) or 0
        new_total = current_total + time_log_data.hours

        update_stmt = (
            update(Task)
            .where(Task.id == task_id)
            .values(logged_hours=new_total, updated_at=datetime.now(UTC))
        )
        await self.db.execute(update_stmt)

        await self.db.commit()
        await self.db.refresh(time_log)

        # Load relationships
        stmt = (
            select(TaskTimeLog)
            .where(TaskTimeLog.id == time_log.id)
            .options(selectinload(TaskTimeLog.user))
        )
        return await self.db.scalar(stmt)

    async def create_task_dependency(
        self, blocking_task_id: UUID, blocked_task_id: UUID, creator_id: UUID
    ) -> TaskDependency:
        """
        Create a dependency between tasks.
        :param blocking_task_id: UUID of the task that blocks another.
        :param blocked_task_id: UUID of the task that is blocked.
        :param creator_id: UUID of the user creating the dependency.
        :return: Created TaskDependency object.
        """
        blocking_task = await self.get_task_by_id(blocking_task_id)
        await self.get_task_by_id(blocked_task_id)

        if not await self._can_user_edit_task(creator_id, blocking_task):
            raise ForbiddenException("Insufficient permissions to create dependencies")

        if blocking_task_id == blocked_task_id:
            raise ValidationException("Task cannot depend on itself")

        existing_stmt = select(TaskDependency).where(
            TaskDependency.blocking_task_id == blocking_task_id,
            TaskDependency.blocked_task_id == blocked_task_id,
        )
        if await self.db.scalar(existing_stmt):
            raise ConflictError("Dependency already exists")

        if await self._would_create_circular_dependency(
            blocking_task_id, blocked_task_id
        ):
            raise ValidationException(
                "This dependency would create a circular reference"
            )

        dependency = TaskDependency(
            blocking_task_id=blocking_task_id,
            blocked_task_id=blocked_task_id,
            created_by=creator_id,
        )

        self.db.add(dependency)
        await self.db.commit()
        await self.db.refresh(dependency)

        return dependency

    async def get_task_stats(self, project_id: UUID, user_id: UUID) -> TaskStats:
        """
        Get task statistics for a project.
        :param project_id: UUID of the project to retrieve stats for.
        :param user_id: UUID of the user requesting the stats.
        :return: TaskStats object containing various task metrics.
        """
        await self._get_project_with_permissions(project_id, user_id)

        base_stmt = select(Task).where(
            Task.project_id == project_id, Task.deleted_at.is_(None)
        )

        total_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_tasks = await self.db.scalar(total_stmt) or 0

        # Tasks by status
        status_stmt = (
            select(Task.status, func.count(Task.id))
            .where(Task.project_id == project_id, Task.deleted_at.is_(None))
            .group_by(Task.status)
        )
        status_result = await self.db.execute(status_stmt)
        tasks_by_status = {status: count for status, count in status_result.fetchall()}

        # Tasks by priority
        priority_stmt = (
            select(Task.priority, func.count(Task.id))
            .where(Task.project_id == project_id, Task.deleted_at.is_(None))
            .group_by(Task.priority)
        )
        priority_result = await self.db.execute(priority_stmt)
        tasks_by_priority = {
            priority: count for priority, count in priority_result.fetchall()
        }

        # Tasks by type
        type_stmt = (
            select(Task.task_type, func.count(Task.id))
            .where(Task.project_id == project_id, Task.deleted_at.is_(None))
            .group_by(Task.task_type)
        )
        type_result = await self.db.execute(type_stmt)
        tasks_by_type = {
            task_type: count for task_type, count in type_result.fetchall()
        }

        # Calculate specific counts
        open_tasks = sum(
            count
            for status, count in tasks_by_status.items()
            if status not in [TaskStatus.DONE, TaskStatus.CANCELLED]
        )

        in_progress_tasks = tasks_by_status.get(TaskStatus.IN_PROGRESS, 0)
        completed_tasks = tasks_by_status.get(TaskStatus.DONE, 0)

        # Overdue tasks
        overdue_stmt = select(func.count()).select_from(
            base_stmt.where(
                Task.due_date < datetime.now(UTC),
                Task.status.not_in([TaskStatus.DONE, TaskStatus.CANCELLED]),
            ).subquery()
        )
        overdue_tasks = await self.db.scalar(overdue_stmt) or 0

        return TaskStats(
            total_tasks=total_tasks,
            open_tasks=open_tasks,
            in_progress_tasks=in_progress_tasks,
            completed_tasks=completed_tasks,
            overdue_tasks=overdue_tasks,
            tasks_by_status=tasks_by_status,
            tasks_by_priority=tasks_by_priority,
            tasks_by_type=tasks_by_type,
            avg_completion_time_days=None,  # TODO: Calculate when we have more data
            avg_time_to_first_response_hours=None,  # TODO: Calculate from comments
        )

    async def bulk_update_tasks(
        self, bulk_data: TaskBulkUpdate, user_id: UUID
    ) -> Dict[str, Any]:
        """
        Perform bulk updates on multiple tasks.
        :param bulk_data: TaskBulkUpdate schema containing task IDs and fields to update.
        :param user_id: UUID of the user performing the bulk update.
        :return: Dictionary containing results of the bulk update operation.
        """
        results: Dict[str, Any] = {
            "success_count": 0,
            "error_count": 0,
            "errors": [],
            "updated_tasks": [],
        }

        for task_id in bulk_data.task_ids:
            try:
                task = await self.get_task_by_id(task_id)

                if not await self._can_user_edit_task(user_id, task):
                    results["errors"].append(
                        {"task_id": str(task_id), "error": "Insufficient permissions"}
                    )
                    results["error_count"] += 1
                    continue

                # Prepare update values
                update_values: Dict[str, Any] = {}
                if bulk_data.status:
                    update_values["status"] = bulk_data.status
                    if bulk_data.status == TaskStatus.DONE and not task.completed_at:
                        update_values["completed_at"] = datetime.now(UTC)

                if bulk_data.priority:
                    update_values["priority"] = bulk_data.priority

                if bulk_data.labels is not None:
                    update_values["labels"] = bulk_data.labels

                if bulk_data.due_date:
                    update_values["due_date"] = bulk_data.due_date

                if update_values:
                    update_values["updated_at"] = datetime.now(UTC)

                    stmt = (
                        update(Task).where(Task.id == task_id).values(**update_values)
                    )
                    await self.db.execute(stmt)

                # Handle assignee updates
                if bulk_data.assignee_ids is not None:
                    await self._update_task_assignees(
                        task_id, bulk_data.assignee_ids, user_id
                    )

                results["success_count"] += 1
                results["updated_tasks"].append(str(task_id))

            except Exception as e:
                results["errors"].append({"task_id": str(task_id), "error": str(e)})
                results["error_count"] += 1

        await self.db.commit()
        return results

        await self.db.commit()
        return results

    async def _get_project_with_permissions(
        self, project_id: UUID, user_id: UUID
    ) -> Project:
        """Get project and verify user has access"""
        stmt = select(Project).where(
            Project.id == project_id, Project.deleted_at.is_(None)
        )
        project = await self.db.scalar(stmt)

        if not project:
            raise NotFoundException("Project", str(project_id))

        project_member_stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
        )
        project_member = await self.db.scalar(project_member_stmt)

        if not project_member:
            org_member_stmt = select(OrganizationMember).where(
                OrganizationMember.organization_id == project.organization_id,
                OrganizationMember.user_id == user_id,
            )
            org_member = await self.db.scalar(org_member_stmt)

            if not org_member or not org_member.is_active:
                raise ForbiddenException(
                    "You are not a member of this project or organization"
                )

        return project

    async def _validate_assignees(
        self, user_ids: List[UUID], project_id: UUID
    ) -> List[UUID]:
        """Validate that all users are project members"""
        if not user_ids:
            return []

        members_stmt = select(ProjectMember.user_id).where(
            ProjectMember.project_id == project_id
        )
        project_members = set(await self.db.scalars(members_stmt))

        invalid_users = [
            user_id for user_id in user_ids if user_id not in project_members
        ]
        if invalid_users:
            raise ValidationException(f"Users not in project: {invalid_users}")

        return user_ids

    async def can_user_view_task(self, user_id: UUID, task: Task) -> bool:
        """Check if user can view a task"""
        if task.reporter_id == user_id:
            return True

        if any(assignment.user_id == user_id for assignment in task.assignees):
            return True

        project_member_stmt = select(ProjectMember).where(
            ProjectMember.project_id == task.project_id,
            ProjectMember.user_id == user_id,
        )
        project_member = await self.db.scalar(project_member_stmt)

        if project_member:
            return True

        org_member_stmt = select(OrganizationMember).where(
            OrganizationMember.organization_id == task.project.organization_id,
            OrganizationMember.user_id == user_id,
        )
        org_member = await self.db.scalar(org_member_stmt)

        return org_member and org_member.is_active

    async def _can_user_edit_task(self, user_id: UUID, task: Task) -> bool:
        """Check if user can edit a task"""
        if task.reporter_id == user_id:
            return True

        if any(assignment.user_id == user_id for assignment in task.assignees):
            return True

        project_member_stmt = select(ProjectMember).where(
            ProjectMember.project_id == task.project_id,
            ProjectMember.user_id == user_id,
            ProjectMember.role == ProjectRole.LEAD,
        )
        if await self.db.scalar(project_member_stmt):
            return True

        org_member_stmt = select(OrganizationMember).where(
            OrganizationMember.organization_id == task.project.organization_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.role.in_(
                [OrganizationRole.OWNER, OrganizationRole.ADMIN]
            ),
        )
        return bool(await self.db.scalar(org_member_stmt))

    async def _can_user_delete_task(self, user_id: UUID, task: Task) -> bool:
        """Check if user can delete a task"""
        return await self._can_user_edit_task(user_id, task)

    async def _update_task_assignees(
        self, task_id: UUID, assignee_ids: List[UUID], assigner_id: UUID
    ) -> None:
        """Update task assignees"""
        delete_stmt = delete(TaskAssignee).where(TaskAssignee.task_id == task_id)
        await self.db.execute(delete_stmt)

        for user_id in assignee_ids:
            assignment = TaskAssignee(
                task_id=task_id,
                user_id=user_id,
                assigned_by=assigner_id,
            )
            self.db.add(assignment)

    def _apply_task_filters(self, stmt, filters: TaskFilters):
        """Apply filters to task query"""
        if filters.status:
            stmt = stmt.where(Task.status.in_(filters.status))

        if filters.priority:
            stmt = stmt.where(Task.priority.in_(filters.priority))

        if filters.task_type:
            stmt = stmt.where(Task.task_type.in_(filters.task_type))

        if filters.assignee_ids:
            stmt = stmt.where(
                Task.assignees.any(TaskAssignee.user_id.in_(filters.assignee_ids))
            )

        if filters.reporter_id:
            stmt = stmt.where(Task.reporter_id == filters.reporter_id)

        if filters.labels:
            for label in filters.labels:
                stmt = stmt.where(Task.labels.contains([label]))

        if filters.due_date_from:
            stmt = stmt.where(Task.due_date >= filters.due_date_from)

        if filters.due_date_to:
            stmt = stmt.where(Task.due_date <= filters.due_date_to)

        if filters.search:
            search_term = f"%{filters.search}%"
            stmt = stmt.where(
                or_(Task.title.ilike(search_term), Task.description.ilike(search_term))
            )

        if not filters.include_subtasks:
            stmt = stmt.where(Task.parent_task_id.is_(None))

        if filters.parent_task_id:
            stmt = stmt.where(Task.parent_task_id == filters.parent_task_id)

        return stmt

    async def _would_create_circular_dependency(
        self, blocking_task_id: UUID, blocked_task_id: UUID
    ) -> bool:
        """Check if creating this dependency would create a circular reference"""
        # Simple check: see if blocked_task_id already blocks blocking_task_id
        existing_stmt = select(TaskDependency).where(
            TaskDependency.blocking_task_id == blocked_task_id,
            TaskDependency.blocked_task_id == blocking_task_id,
        )
        return bool(await self.db.scalar(existing_stmt))
