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

    # Security settings
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production", description="Secret key"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Access token expiry"
    )

    # CORS settings
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="CORS origins",
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
