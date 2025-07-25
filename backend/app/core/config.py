from typing import List
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings
from time import time


class Settings(BaseSettings):
    """
    Application configuration settings.
    """

    # App settings
    APP_NAME: str = Field(default="Smithy API", description="Name of the application")
    VERSION: str = Field(default="0.1.0", description="Application version")
    ENVIRONMENT: str = Field(
        default="development", description="Application environment"
    )
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    DOCS_ENABLED: bool = Field(default=True, description="Enable API documentation")

    # Server settings
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")

    # Database settings
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://smithy:smithy@localhost/smithy",
        description="Database URL",
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql://smithy:smithy@localhost/smithy",
        description="Synchronous database URL for Alembic",
    )

    REDIS_URL: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )

    # Security settings
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production", description="Secret key"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Access token expiry"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, description="Refresh token expiry in days"
    )

    # CORS settings
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="CORS origins",
    )

    # Storage settings
    STORAGE_PROVIDER: str = Field(
        default="local",
        description="Storage provider (e.g., local, s3, etc.)",
    )

    LOCAL_STORAGE_PATH: str = Field(
        default="uploads",
        description="Local storage path for file uploads",
    )
    LOCAL_STORAGE_URL: str = Field(
        default=None,
        description="Base URL for accessing local storage files",
    )
    LOCAL_STORAGE_CREATE_DIRS: bool = Field(
        default=True,
        description="Create directories for local storage if they don't exist",
    )
    LOCAL_STORAGE_FILE_PERMISSIONS: int = Field(
        default=0o644,
        description="File permissions for uploaded files in local storage",
    )
    LOCAL_STORAGE_DIR_PERMISSIONS: int = Field(
        default=0o755,
        description="Directory permissions for local storage",
    )
    # File upload limits
    MAX_FILE_SIZE_MB: int = Field(
        default=10, description="Maximum file size for uploads in MB"
    )
    MAX_LOGO_SIZE_MB: int = Field(default=5, description="Maximum logo size in MB")
    # Allowed file types
    ALLOWED_FILE_TYPES: str = Field(
        default="image/jpeg,image/png,image/gif,application/pdf,text/plain",
        description="Comma-separated list of allowed file MIME types",
    )
    ALLOWED_DOCUMENT_TYPES: str = Field(
        default="application/pdf,text/plain,application/msword",
        description="Comma-separated list of allowed document MIME types",
    )
    ALLOWED_ARCHIVE_TYPES: str = Field(
        default="application/zip,application/x-rar-compressed",
        description="Comma-separated list of allowed archive MIME types",
    )

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Log level")

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value"""
        allowed_envs = ["development", "staging", "production"]
        if v.lower() not in allowed_envs:
            raise ValueError(f"Environment must be one of: {allowed_envs}")
        return v.lower()

    @field_validator("STORAGE_PROVIDER")
    @classmethod
    def validate_storage_provider(cls, v: str) -> str:
        """Validate storage provider"""
        allowed_providers = ["local"]
        if v.lower() not in allowed_providers:
            raise ValueError(f"Storage provider must be one of: {allowed_providers}")
        return v.lower()

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of: {allowed_levels}")
        return v.upper()

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key strength"""
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v

    @field_validator("PORT")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port range"""
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v

    @model_validator(mode="after")
    def validate_docs_settings(self) -> "Settings":
        """Validate docs settings based on debug mode"""
        if self.DEBUG:
            # Force docs enabled in debug mode
            self.DOCS_ENABLED = True
        # In production, docs can be explicitly disabled
        return self

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
startup_time = time()
settings = Settings()
