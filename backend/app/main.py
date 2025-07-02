import logging
from contextlib import asynccontextmanager

from fastapi.exceptions import RequestValidationError

from app import __version__
from app.api import api_router, init_routers, routers
from app.core.config import settings
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.exceptions import (
    APIException,
    api_exception_handler,
    http_exception_handler,
    not_found_exception_handler,
    method_not_allowed_exception_handler,
    generic_exception_handler,
    forbidden_exception_handler,
    request_validation_exception_handler,
    pydantic_validation_exception_handler,
)
from app.core.logger import setup_logging
from pydantic import ValidationError

from app.core.middleware.sanitization import SanitizationMiddleware
from app.db.redis_client import redis_client

setup_logging()


def print_banner() -> None:
    """
    Prints the banner for the application.
    :return: None
    """
    port = settings.PORT
    debug = "\033[38;5;226mON\033[0m" if settings.DEBUG else "\033[38;5;196mOFF\033[0m"
    router_count = len(routers)

    banner = f"""
    \033[38;5;208m
      ███████╗███╗   ███╗██╗████████╗██╗  ██╗██╗   ██╗
      ██╔════╝████╗ ████║██║╚══██╔══╝██║  ██║╚██╗ ██╔╝
      ███████╗██╔████╔██║██║   ██║   ███████║ ╚████╔╝ 
      ╚════██║██║╚██╔╝██║██║   ██║   ██╔══██║  ╚██╔╝  
      ███████║██║ ╚═╝ ██║██║   ██║   ██║  ██║   ██║   
      ╚══════╝╚═╝     ╚═╝╚═╝   ╚═╝   ╚═╝  ╚═╝   ╚═╝   
    \033[0m\033[38;5;244m
    ┌─────────────────────────────────────────────────┐
    │  \033[1mProject Management API\033[0m\033[38;5;244m                         │
    │  Built for developers, by developers            │
    │                                                 │
    │  \033[38;5;46m🔨 Version:\033[0m v{__version__:<30}\033[38;5;244m    │
    │  \033[38;5;46m🌐 Port:\033[0m    {port:<29}      \033[38;5;244m│
    │  \033[38;5;46m🐛 Debug:\033[0m   {debug:<29}      \033[38;5;244m               │
    │  \033[38;5;46m📚 Routers:\033[0m {router_count:<29}      \033[38;5;244m│
    └─────────────────────────────────────────────────┘
    \033[0m
    """
    print(banner)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    :param app: FastAPI application
    """
    logger = logging.getLogger(__name__)

    print_banner()
    logger.info("🚀 Smithy API starting up...")
    logger.info(f"📍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🎯 Debug mode: {settings.DEBUG}")

    # Connect to Redis
    await redis_client.connect()

    yield

    # Cleanup on shutdown
    await redis_client.disconnect()
    logger.info("⚡ Smithy API shutting down...")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    :return: FastAPI application
    """
    logging.getLogger("watchfiles.main").setLevel(logging.CRITICAL)

    app = FastAPI(
        title="Smithy API",
        description="Project management platform for developers",
        version=__version__,
        docs_url="/docs" if settings.DOCS_ENABLED else None,
        redoc_url="/redoc" if settings.DOCS_ENABLED else None,
        lifespan=lifespan,
    )
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        SanitizationMiddleware,
        enabled=True,
        skip_paths=[
            "/docs",
            "/redoc",
            "/openapi.json",
            "/v1/health",
        ],
        skip_content_types=[
            "application/octet-stream",
            "multipart/form-data",
            "image/",
            "video/",
            "audio/",
        ],
        log_sanitization=settings.DEBUG,
    )

    # Exception handlers
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(
        RequestValidationError, request_validation_exception_handler
    )  # <- FastAPI validation
    app.add_exception_handler(
        ValidationError, pydantic_validation_exception_handler
    )  # <- Pydantic validation
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(403, forbidden_exception_handler)
    app.add_exception_handler(404, not_found_exception_handler)
    app.add_exception_handler(405, method_not_allowed_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    init_routers()
    app.include_router(api_router)

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
