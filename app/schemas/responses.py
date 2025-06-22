from datetime import datetime, UTC
from typing import Any, List, Optional, Union, TypeVar, Generic

from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel):
    """Base response model for all API endpoints"""

    success: bool = Field(True, description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Any] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MessageResponse(BaseModel):
    """Simple message response without data"""

    success: bool = Field(True)
    message: str = Field(...)
    data: None = Field(None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def __init__(self, message: str, **kwargs):
        super().__init__(message=message, data=None, **kwargs)


class DataResponse(BaseModel, Generic[T]):
    """Response with data payload"""

    success: bool = Field(True)
    message: str = Field(...)
    data: T = Field(...)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def __init__(
        self, data: T, message: str = "Operation completed successfully", **kwargs
    ):
        super().__init__(message=message, data=data, **kwargs)


class PaginationMeta(BaseModel):
    """Pagination metadata"""

    page: int = Field(..., ge=1)
    size: int = Field(..., ge=0)
    total: int = Field(..., ge=0)
    pages: int = Field(..., ge=0)
    has_next: bool = Field(...)
    has_prev: bool = Field(...)

    @classmethod
    def create(cls, page: int, size: int, total: int) -> "PaginationMeta":
        pages = (total + size - 1) // size if total > 0 else 0
        return cls(
            page=page,
            size=size,
            total=total,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        )


class ListResponse(BaseModel):
    """Paginated list response"""

    success: bool = Field(True)
    message: str = Field("Data retrieved successfully")
    data: List[Any] = Field(...)
    pagination: PaginationMeta = Field(...)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


# Helper functions
def success_response(
    data: Optional[Any] = None, message: str = "Success"
) -> Union[DataResponse, MessageResponse]:
    if data is not None:
        return DataResponse(data=data, message=message)
    return MessageResponse(message=message)


def list_response(
    success: bool,
    items: List[Any],
    page: int,
    size: int,
    total: int,
    message: str = "Data retrieved",
) -> ListResponse:
    pagination = PaginationMeta.create(page, size, total)
    return ListResponse(
        data=items, pagination=pagination, message=message, success=success
    )


__all__ = [
    "BaseResponse",
    "MessageResponse",
    "DataResponse",
    "PaginationMeta",
    "ListResponse",
    "success_response",
    "list_response",
]
