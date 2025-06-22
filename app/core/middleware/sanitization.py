import json
import logging
from typing import Any, List, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from urllib.parse import parse_qs, urlencode
from app.core.sanitizers import ComprehensiveSanitizer

logger = logging.getLogger(__name__)


class SanitizationMiddleware(BaseHTTPMiddleware):
    """Middleware that automatically sanitizes incoming request data."""

    def __init__(
        self,
        app: ASGIApp,
        enabled: bool = True,
        skip_paths: Optional[List[str]] = None,
        skip_content_types: Optional[List[str]] = None,
        log_sanitization: bool = False,
    ):
        """
        Initialize sanitization middleware.

        :param app: ASGI application
        :param enabled: Whether sanitization is enabled
        :param skip_paths: Paths to skip sanitization (e.g., ['/docs', '/health'])
        :param skip_content_types: Content types to skip (e.g., ['application/octet-stream'])
        :param log_sanitization: Whether to log sanitization actions
        """
        super().__init__(app)
        self.enabled = enabled
        self.skip_paths = skip_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
        ]
        self.skip_content_types = skip_content_types or [
            "application/octet-stream",
            "multipart/form-data",
            "image/",
            "video/",
            "audio/",
        ]
        self.log_sanitization = log_sanitization

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request and sanitize data if necessary.
        :param request: Request object
        :param call_next: Next middleware or endpoint to call
        :return: Response object
        """

        if not self.enabled:
            return await call_next(request)

        # Skip sanitization for certain paths
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)

        # Skip sanitization for certain content types
        content_type = request.headers.get("content-type", "").lower()
        if any(skip_type in content_type for skip_type in self.skip_content_types):
            return await call_next(request)

        # Only sanitize for specific HTTP methods
        if request.method not in ["POST", "PUT", "PATCH"]:
            return await call_next(request)

        try:
            # Sanitize request data
            request = await self._sanitize_request(request)
        except Exception as e:
            if self.log_sanitization:
                logger.warning(f"Sanitization error for {request.url.path}: {e}")

        return await call_next(request)

    async def _sanitize_request(self, request: Request) -> Request:
        """
        Sanitize the request body based on content type.
        :param request: Request object to sanitize
        :return: Sanitized request object
        """

        # Get request body
        body = await request.body()
        if not body:
            return request

        content_type = request.headers.get("content-type", "").lower()

        try:
            if "application/json" in content_type:
                # Parse and sanitize JSON data
                data = json.loads(body.decode("utf-8"))
                sanitized_data = self._sanitize_data(data)

                # Create new request with sanitized data
                sanitized_body = json.dumps(sanitized_data).encode("utf-8")
                request._body = sanitized_body

                if self.log_sanitization and data != sanitized_data:
                    logger.info(f"Sanitized JSON data for {request.url.path}")

            elif "application/x-www-form-urlencoded" in content_type:
                data = parse_qs(body.decode("utf-8"))
                # Convert single-item lists to strings for sanitization
                form_data = {k: v[0] if len(v) == 1 else v for k, v in data.items()}
                sanitized_data = self._sanitize_data(form_data)

                # Convert back to form format
                sanitized_body = urlencode(sanitized_data).encode("utf-8")
                request._body = sanitized_body

                if self.log_sanitization and form_data != sanitized_data:
                    logger.info(f"Sanitized form data for {request.url.path}")

        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
            if self.log_sanitization:
                logger.warning(f"Could not parse request body for sanitization: {e}")

        return request

    def _sanitize_data(self, data: Any) -> Any:
        """
        Recursively sanitize data, handling dicts, lists, and strings.
        :param data: Data to sanitize, can be dict, list, or string
        :return: Sanitized data
        """

        if isinstance(data, dict):
            return ComprehensiveSanitizer.sanitize_user_input(data)
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        elif isinstance(data, str):
            from app.core.sanitizers import TextSanitizer

            return TextSanitizer.sanitize_basic_text(data)
        else:
            return data
