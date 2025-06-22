from datetime import datetime, UTC
from typing import Optional, Dict, Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from enum import Enum
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError


class ErrorCode(str, Enum):
    """
    Enum for error codes used in API exceptions.
    Provides a consistent set of error codes for different types of errors.
    """

    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    BAD_REQUEST = "bad_request"
    CONFLICT = "conflict"
    HTTP_ERROR = "http_error"
    VALIDATION_ERROR = "validation_error"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INTERNAL_SERVER_ERROR = "internal_server_error"


class APIException(HTTPException):
    """
    Base class for all API exceptions.
    Inherits from HTTPException to provide a consistent error response format.
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(status_code=status_code, detail=message)


class NotFoundException(APIException):
    """
    Exception raised when a resource is not found.
    """

    def __init__(self, resource: str, identifier: Optional[str] = None):
        message = f"{resource} not found"
        if identifier:
            message += f" (ID: {identifier})"

        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.NOT_FOUND,
            details={"resource": resource, "identifier": identifier},
        )


class ValidationException(APIException):
    """
    Exception raised for validation errors.
    """

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code=ErrorCode.BAD_REQUEST,
            details={"field": field} if field else {},
        )


class AuthenticationException(APIException):
    """
    Exception raised for authentication errors.
    """

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.UNAUTHORIZED,
        )


class ForbiddenException(APIException):
    """
    Exception raised for forbidden access.
    """

    def __init__(self, message: str = "Forbidden access"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
        )


class InternalServerErrorException(APIException):
    """
    Exception raised for internal server errors.
    """

    def __init__(
        self,
        message: str = "Internal server error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=details,
        )


class ConflictError(APIException):
    """Resource conflict exception"""

    def __init__(self, message: str, resource: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.CONFLICT,
            details={"resource": resource} if resource else {},
        )


class RateLimitException(APIException):
    """Rate limit exceeded exception"""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
        )


def format_error_response(
    message: str,
    code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
) -> Dict[str, Any]:
    """Format standardized error response"""
    return {
        "error": True,
        "message": message,
        "code": code.value,
        "status_code": status_code,
        "timestamp": datetime.now(UTC).isoformat(),
        "details": details or {},
    }


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """
    Global exception handler for API exceptions.
    Converts APIException to a standardized JSON response.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            message=exc.message,
            code=exc.code,
            details=exc.details,
            status_code=exc.status_code,
        ),
    )


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Global exception handler for FastAPI request validation errors.
    Converts RequestValidationError to a standardized JSON response.
    """
    errors = []
    for error in exc.errors():
        # Build the field path from the error location
        field_path = []
        for loc in error["loc"]:
            if loc != "body":
                field_path.append(str(loc))

        field = ".".join(field_path) if field_path else "unknown"

        msg = error["msg"]
        error_type = error["type"]

        if error_type == "missing":
            msg = "This field is required"
        elif error_type == "string_too_short":
            msg = f"Text is too short (minimum {error.get('ctx', {}).get('min_length', 'unknown')} characters)"
        elif error_type == "string_too_long":
            msg = f"Text is too long (maximum {error.get('ctx', {}).get('max_length', 'unknown')} characters)"
        elif error_type == "value_error":
            msg = error.get("ctx", {}).get("reason", msg)

        errors.append(
            {
                "field": field,
                "message": msg,
                "type": error_type,
                "input": error.get("input"),
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=format_error_response(
            message="Validation failed",
            code=ErrorCode.VALIDATION_ERROR,
            details={"errors": errors},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ),
    )


async def pydantic_validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """
    Global exception handler for Pydantic validation errors.
    """
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({"field": field, "message": error["msg"], "type": error["type"]})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=format_error_response(
            message="Data validation failed",
            code=ErrorCode.VALIDATION_ERROR,
            details={"errors": errors},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Global exception handler for HTTP exceptions.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            message=exc.detail, code=ErrorCode.HTTP_ERROR, status_code=exc.status_code
        ),
    )


async def forbidden_exception_handler(
    request: Request, exc: ForbiddenException
) -> JSONResponse:
    """
    Handle 403 Forbidden errors with consistent format.
    """
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=format_error_response(
            message=getattr(exc, "message", "Forbidden access"),
            code=ErrorCode.FORBIDDEN,
            status_code=status.HTTP_403_FORBIDDEN,
        ),
    )


async def not_found_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle 404 Not Found errors with consistent format.
    """
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=format_error_response(
            message="The requested resource was not found",
            code=ErrorCode.NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
        ),
    )


async def method_not_allowed_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Handle 405 Method Not Allowed errors with consistent format.
    """
    return JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content=format_error_response(
            message="The requested HTTP method is not allowed for this endpoint",
            code=ErrorCode.HTTP_ERROR,
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        ),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=format_error_response(
            message="Internal server error",
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            details={"type": type(exc).__name__},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ),
    )
