import logging
from typing import Optional

from .base import StorageProvider
from .local import LocalStorageProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageFactory:
    """Factory class for creating storage providers"""

    _instance: Optional[StorageProvider] = None

    @classmethod
    def get_storage_provider(cls, force_new: bool = False) -> StorageProvider:
        """
        Get configured storage provider.

        :param force_new: Force creation of new instance
        :return: Configured storage provider
        """
        if cls._instance is None or force_new:
            cls._instance = cls._create_storage_provider()

        return cls._instance

    @classmethod
    def _create_storage_provider(cls) -> StorageProvider:
        """
        Create storage provider based on configuration.

        :return: Configured storage provider
        """
        storage_type = getattr(settings, "STORAGE_PROVIDER", "local").lower()

        if storage_type == "local":
            return cls._create_local_storage()
        else:
            raise ValueError(f"Unsupported storage provider: {storage_type}")

    @classmethod
    def _create_local_storage(cls) -> LocalStorageProvider:
        """
        Create local storage provider.

        :return: Configured LocalStorageProvider
        """
        base_path = getattr(settings, "LOCAL_STORAGE_PATH", "uploads")
        base_url = getattr(settings, "LOCAL_STORAGE_URL", None)

        if not base_url:
            host = getattr(settings, "HOST", "localhost")
            port = getattr(settings, "PORT", 8000)
            base_url = f"http://{host}:{port}/uploads"

        create_directories = getattr(settings, "LOCAL_STORAGE_CREATE_DIRS", True)
        file_permissions = getattr(settings, "LOCAL_STORAGE_FILE_PERMISSIONS", 0o644)
        dir_permissions = getattr(settings, "LOCAL_STORAGE_DIR_PERMISSIONS", 0o755)

        logger.info(f"Creating local storage provider: {base_path}")

        return LocalStorageProvider(
            base_path=base_path,
            base_url=base_url,
            create_directories=create_directories,
            file_permissions=file_permissions,
            dir_permissions=dir_permissions,
        )


def get_storage_provider() -> StorageProvider:
    """Get the configured storage provider"""
    return StorageFactory.get_storage_provider()
