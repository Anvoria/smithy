import logging
from typing import Annotated, Optional, List, Dict
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
from app.core.exceptions import NotFoundException, ForbiddenException
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListItem,
    TaskStats,
    TaskStatusUpdate,
    TaskAssigneeCreate,
    TaskAssigneeResponse,
    TaskCommentCreate,
    TaskCommentResponse,
    TaskTimeLogCreate,
    TaskTimeLogResponse,
    TaskDependencyCreate,
    TaskDependencyResponse,
    TaskFilters,
    TaskBulkUpdate,
    TaskBulkResponse,
)
from app.schemas.auth import AuthUser
from app.services.task_service import TaskService
from app.core.auth import get_current_user
from app.models.task import TaskStatus, TaskPriority, TaskType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "/",
    response_model=DataResponse[TaskResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    task_data: TaskCreate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[TaskResponse]:
    """
    Create a new task.

    User must be a member of the project with task creation permissions.
    """
    task_service = TaskService(db)
    task = await task_service.create_task(task_data, UUID(current_user.id))

    return DataResponse(
        message="Task created successfully",
        data=TaskResponse.model_validate(task),
    )


@router.get("/{task_id}", response_model=DataResponse[TaskResponse])
async def get_task(
    task_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[TaskResponse]:
    """
    Get task details by ID.

    User must have view access to the task.
    """
    task_service = TaskService(db)
    task = await task_service.get_task_by_id(task_id)

    # Check permissions
    if not await task_service.can_user_view_task(UUID(current_user.id), task):
        raise ForbiddenException("Insufficient permissions to view this task")

    return DataResponse(
        message="Task retrieved successfully",
        data=TaskResponse.model_validate(task),
    )


@router.get(
    "/project/{project_id}/number/{task_number}",
    response_model=DataResponse[TaskResponse],
)
async def get_task_by_number(
    project_id: UUID,
    task_number: int,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[TaskResponse]:
    """
    Get task by project ID and task number (e.g., PROJECT-123).

    User must have view access to the task.
    """
    task_service = TaskService(db)
    task = await task_service.get_task_by_project_and_number(project_id, task_number)

    if not task:
        raise NotFoundException("Task", f"{project_id}-{task_number}")

    if not await task_service.can_user_view_task(UUID(current_user.id), task):
        raise ForbiddenException("Insufficient permissions to view this task")

    return DataResponse(
        message="Task retrieved successfully",
        data=TaskResponse.model_validate(task),
    )


@router.put("/{task_id}", response_model=DataResponse[TaskResponse])
async def update_task(
    task_id: UUID,
    update_data: TaskUpdate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[TaskResponse]:
    """
    Update task details.

    User must have edit permissions for the task.
    """
    task_service = TaskService(db)
    task = await task_service.update_task(task_id, update_data, UUID(current_user.id))

    return DataResponse(
        message="Task updated successfully",
        data=TaskResponse.model_validate(task),
    )


@router.put("/{task_id}/status", response_model=DataResponse[TaskResponse])
async def update_task_status(
    task_id: UUID,
    status_data: TaskStatusUpdate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[TaskResponse]:
    """
    Update task status with optional comment.

    User must have edit permissions for the task.
    """
    task_service = TaskService(db)
    task = await task_service.update_task_status(
        task_id, status_data, UUID(current_user.id)
    )

    return DataResponse(
        message="Task status updated successfully",
        data=TaskResponse.model_validate(task),
    )


@router.delete("/{task_id}", response_model=MessageResponse)
async def delete_task(
    task_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """
    Delete a task (soft delete).

    Only task reporter, assignees, or project leads can delete tasks.
    """
    task_service = TaskService(db)
    success = await task_service.delete_task(task_id, UUID(current_user.id))

    return MessageResponse(
        "Task deleted successfully" if success else "Failed to delete task"
    )


@router.get("/project/{project_id}", response_model=ListResponse)
async def get_project_tasks(
    project_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    status: Optional[List[TaskStatus]] = Query(None, description="Filter by status"),
    priority: Optional[List[TaskPriority]] = Query(
        None, description="Filter by priority"
    ),
    task_type: Optional[List[TaskType]] = Query(None, description="Filter by type"),
    assignee_ids: Optional[List[UUID]] = Query(None, description="Filter by assignees"),
    reporter_id: Optional[UUID] = Query(None, description="Filter by reporter"),
    labels: Optional[List[str]] = Query(None, description="Filter by labels"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    include_subtasks: bool = Query(True, description="Include subtasks in results"),
    parent_task_id: Optional[UUID] = Query(None, description="Filter by parent task"),
) -> ListResponse:
    """
    Get tasks for a project with filtering and pagination.

    User must be a member of the project.
    """
    task_service = TaskService(db)

    # Build filters
    filters = TaskFilters(
        status=status,
        priority=priority,
        task_type=task_type,
        assignee_ids=assignee_ids,
        reporter_id=reporter_id,
        labels=labels,
        search=search,
        include_subtasks=include_subtasks,
        parent_task_id=parent_task_id,
    )

    tasks, total = await task_service.get_project_tasks(
        project_id, UUID(current_user.id), filters, page, size
    )

    task_list = [TaskListItem.model_validate(task) for task in tasks]
    pages = (total + size - 1) // size

    return ListResponse(
        success=True,
        message="Tasks retrieved successfully",
        data=task_list,
        pagination=PaginationMeta(
            page=page,
            size=size,
            total=total,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        ),
    )


@router.get("/my-tasks", response_model=ListResponse)
async def get_my_tasks(
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    status: Optional[List[TaskStatus]] = Query(None, description="Filter by status"),
    priority: Optional[List[TaskPriority]] = Query(
        None, description="Filter by priority"
    ),
    task_type: Optional[List[TaskType]] = Query(None, description="Filter by type"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    include_subtasks: bool = Query(True, description="Include subtasks in results"),
) -> ListResponse:
    """
    Get tasks assigned to or reported by the current user.
    """
    task_service = TaskService(db)

    # Build filters
    filters = TaskFilters(
        status=status,
        priority=priority,
        task_type=task_type,
        search=search,
        include_subtasks=include_subtasks,
    )

    tasks, total = await task_service.get_user_tasks(
        UUID(current_user.id), filters, page, size
    )

    task_list = [TaskListItem.model_validate(task) for task in tasks]
    pages = (total + size - 1) // size

    return ListResponse(
        success=True,
        message="Your tasks retrieved successfully",
        data=task_list,
        pagination=PaginationMeta(
            page=page,
            size=size,
            total=total,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        ),
    )


@router.get("/project/{project_id}/stats", response_model=DataResponse[TaskStats])
async def get_project_task_stats(
    project_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[TaskStats]:
    """
    Get task statistics for a project.

    User must be a member of the project.
    """
    task_service = TaskService(db)
    stats = await task_service.get_task_stats(project_id, UUID(current_user.id))

    return DataResponse(
        message="Task statistics retrieved successfully",
        data=stats,
    )


@router.get("/{task_id}/subtasks", response_model=ListResponse)
async def get_task_subtasks(
    task_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ListResponse:
    """
    Get all subtasks for a task.

    User must have view access to the parent task.
    """
    task_service = TaskService(db)
    task = await task_service.get_task_by_id(task_id)

    if not await task_service.can_user_view_task(UUID(current_user.id), task):
        raise ForbiddenException("Insufficient permissions to view this task")

    # Get subtasks
    subtasks = [TaskListItem.model_validate(subtask) for subtask in task.subtasks]

    return ListResponse(
        success=True,
        message="Subtasks retrieved successfully",
        data=subtasks,
        pagination=PaginationMeta(
            page=1,
            size=len(subtasks),
            total=len(subtasks),
            pages=1,
            has_next=False,
            has_prev=False,
        ),
    )


@router.get(
    "/{task_id}/assignees", response_model=DataResponse[List[TaskAssigneeResponse]]
)
async def get_task_assignees(
    task_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[List[TaskAssigneeResponse]]:
    """
    Get all assignees for a task.

    User must have view access to the task.
    """
    task_service = TaskService(db)
    task = await task_service.get_task_by_id(task_id)

    if not await task_service.can_user_view_task(UUID(current_user.id), task):
        raise ForbiddenException("Insufficient permissions to view this task")

    assignees = [
        TaskAssigneeResponse.model_validate(assignee) for assignee in task.assignees
    ]

    return DataResponse(
        message="Task assignees retrieved successfully",
        data=assignees,
    )


@router.post(
    "/{task_id}/assignees", response_model=DataResponse[List[TaskAssigneeResponse]]
)
async def assign_users_to_task(
    task_id: UUID,
    assignee_data: TaskAssigneeCreate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[List[TaskAssigneeResponse]]:
    """
    Assign users to a task (replaces existing assignments).

    User must have edit permissions for the task.
    """
    task_service = TaskService(db)
    assignees = await task_service.assign_users_to_task(
        task_id, assignee_data, UUID(current_user.id)
    )

    assignee_list = [
        TaskAssigneeResponse.model_validate(assignee) for assignee in assignees
    ]

    return DataResponse(
        message="Users assigned to task successfully",
        data=assignee_list,
    )


@router.get("/{task_id}/comments", response_model=ListResponse)
async def get_task_comments(
    task_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
) -> ListResponse:
    """
    Get comments for a task.

    User must have view access to the task.
    """
    task_service = TaskService(db)
    comments, total = await task_service.get_task_comments(
        task_id, UUID(current_user.id), page, size
    )

    comment_list = [TaskCommentResponse.model_validate(comment) for comment in comments]
    pages = (total + size - 1) // size

    return ListResponse(
        success=True,
        message="Task comments retrieved successfully",
        data=comment_list,
        pagination=PaginationMeta(
            page=page,
            size=size,
            total=total,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        ),
    )


@router.post("/{task_id}/comments", response_model=DataResponse[TaskCommentResponse])
async def create_task_comment(
    task_id: UUID,
    comment_data: TaskCommentCreate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[TaskCommentResponse]:
    """
    Create a comment on a task.

    User must have view access to the task.
    """
    task_service = TaskService(db)
    comment = await task_service.create_task_comment(
        task_id, comment_data, UUID(current_user.id)
    )

    return DataResponse(
        message="Comment created successfully",
        data=TaskCommentResponse.model_validate(comment),
    )


@router.post("/{task_id}/time-logs", response_model=DataResponse[TaskTimeLogResponse])
async def log_time_to_task(
    task_id: UUID,
    time_log_data: TaskTimeLogCreate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[TaskTimeLogResponse]:
    """
    Log time spent on a task.

    User must have view access to the task.
    """
    task_service = TaskService(db)
    time_log = await task_service.log_time_to_task(
        task_id, time_log_data, UUID(current_user.id)
    )

    return DataResponse(
        message="Time logged successfully",
        data=TaskTimeLogResponse.model_validate(time_log),
    )


@router.get("/{task_id}/time-logs", response_model=ListResponse)
async def get_task_time_logs(
    task_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ListResponse:
    """
    Get time logs for a task.

    User must have view access to the task.
    """
    task_service = TaskService(db)
    task = await task_service.get_task_by_id(task_id)

    if not await task_service.can_user_view_task(UUID(current_user.id), task):
        raise ForbiddenException("Insufficient permissions to view this task")

    time_logs = [TaskTimeLogResponse.model_validate(log) for log in task.time_logs]

    return ListResponse(
        success=True,
        message="Time logs retrieved successfully",
        data=time_logs,
        pagination=PaginationMeta(
            page=1,
            size=len(time_logs),
            total=len(time_logs),
            pages=1,
            has_next=False,
            has_prev=False,
        ),
    )


@router.post("/dependencies", response_model=DataResponse[TaskDependencyResponse])
async def create_task_dependency(
    dependency_data: TaskDependencyCreate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[TaskDependencyResponse]:
    """
    Create a dependency between tasks.
    """
    task_service = TaskService(db)
    dependency = await task_service.create_task_dependency(
        dependency_data.blocking_task_id,
        dependency_data.blocked_task_id,
        UUID(current_user.id),
    )

    return DataResponse(
        message="Task dependency created successfully",
        data=TaskDependencyResponse.model_validate(dependency),
    )


@router.get(
    "/{task_id}/dependencies",
    response_model=DataResponse[Dict[str, List[TaskDependencyResponse]]],
)
async def get_task_dependencies(
    task_id: UUID,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[Dict[str, List[TaskDependencyResponse]]]:
    """
    Get dependencies for a task (both blocking and blocked by).

    User must have view access to the task.
    """
    task_service = TaskService(db)
    task = await task_service.get_task_by_id(task_id)

    if not await task_service.can_user_view_task(UUID(current_user.id), task):
        raise ForbiddenException("Insufficient permissions to view this task")

    blocking = [
        TaskDependencyResponse.model_validate(dep) for dep in task.blocking_tasks
    ]
    blocked_by = [
        TaskDependencyResponse.model_validate(dep) for dep in task.blocked_by_tasks
    ]

    return DataResponse(
        message="Task dependencies retrieved successfully",
        data={
            "blocking": blocking,
            "blocked_by": blocked_by,
        },
    )


@router.post("/bulk-update", response_model=DataResponse[TaskBulkResponse])
async def bulk_update_tasks(
    bulk_data: TaskBulkUpdate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataResponse[TaskBulkResponse]:
    """
    Perform bulk updates on multiple tasks.

    User must have edit permissions for each task.
    """
    task_service = TaskService(db)
    results = await task_service.bulk_update_tasks(bulk_data, UUID(current_user.id))

    return DataResponse(
        message=f"Bulk update completed: {results['success_count']} success, {results['error_count']} errors",
        data=TaskBulkResponse(**results),
    )
