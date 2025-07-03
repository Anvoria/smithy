import os
import aiofiles  # type: ignore[import-untyped]
import logging
from pathlib import Path
from typing import BinaryIO, Optional
from urllib.parse import urljoin

from .base import StorageProvider, StorageMetadata
from app.core.config import settings

logger = logging.getLogger(__name__)


class LocalStorageProvider(StorageProvider):
    """Local filesystem storage provider."""

    def __init__(
        self,
        base_path: str = settings.LOCAL_STORAGE_PATH,
        base_url: Optional[str] = None,
        create_directories: bool = True,
        file_permissions: int = 0o644,
        dir_permissions: int = 0o755,
    ):
        """
        Initialize local storage provider.

        :param base_path: Base directory for file storage
        :param base_url: Base URL for serving files
        :param create_directories: Whether to create directories if they don't exist
        :param file_permissions: File permissions in octal format
        :param dir_permissions: Directory permissions in octal format
        """
        self.base_path = Path(base_path).resolve()
        self.base_url = (
            base_url
            or f"http://localhost:{getattr(settings, 'PORT', 8000)}/{self.base_path.name}/"
        )
        self.create_directories = create_directories
        self.file_permissions = file_permissions
        self.dir_permissions = dir_permissions

        if not self.base_path.is_absolute():
            raise ValueError("Base path must be an absolute path")

        if self.create_directories:
            self._ensure_directory_exists(self.base_path)

        logger.info(
            "Initialized LocalStorageProvider with base path: %s", self.base_path
        )

    async def upload(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str,
        folder: str = "",
        public: bool = True,
    ) -> StorageMetadata:
        """
        Upload file to local filesystem.

        :param file: File-like object to upload
        :param filename: Original filename
        :param content_type: MIME type of the file
        :param folder: Optional folder path to upload to
        :param public: Whether the file should be publicly accessible
        :return: StorageMetadata object with details about the uploaded file
        """
        try:
            secure_filename = self.generate_unique_filename(filename, folder)

            full_path = self._get_path(secure_filename)

            if self.create_directories:
                self._ensure_directory_exists(full_path.parent)

            if hasattr(file, "read"):
                content = await file.read()  # type: ignore
            else:
                content = file

            file_size = len(content)

            if file_size == 0:
                raise ValueError("Cannot upload an empty file")

            # Write file atomically
            temp_path = full_path.with_suffix(full_path.suffix + ".tmp")

            try:
                async with aiofiles.open(temp_path, "wb") as f:
                    await f.write(content)

                os.chmod(temp_path, self.file_permissions)
                temp_path.rename(full_path)

                # Public URL
                relative_path = full_path.relative_to(self.base_path)
                public_url = (
                    urljoin(
                        self.base_url.rstrip("/") + "/",
                        str(relative_path).replace("\\", "/"),
                    )
                    if public
                    else None
                )

                logger.info("Uploaded file: %s to %s", filename, full_path)

                return StorageMetadata(
                    file_path=str(full_path),
                    public_url=public_url,
                    file_size=file_size,
                    content_type=content_type,
                    original_filename=filename,
                    storage_provider=self.__class__.__name__,
                )
            except Exception as e:
                if temp_path.exists():
                    temp_path.unlink()
                raise e
        except Exception as e:
            logger.error("Failed to upload file %s: %s", filename, str(e))
            raise Exception(f"Failed to upload file {filename}: {str(e)}")

    async def delete(self, file_path: str) -> bool:
        """
        Delete file from local filesystem.

        :param file_path: Path to the file to delete
        :return: True if deletion was successful, False otherwise
        """
        try:
            full_path = self._get_path(file_path)

            if not full_path.exists():
                logger.warning("File not found for deletion: %s", full_path)
                return False

            if not full_path.is_file():
                logger.error("Path is not a file: %s", full_path)
                return False

            full_path.unlink()

            self._cleanup_empty_directories(full_path.parent)
            return True
        except Exception as e:
            logger.error("Failed to delete file %s: %s", file_path, str(e))
            return False

    async def get_public_url(self, file_path: str) -> str:
        """
        Get public URL for local file.

        :param file_path: Path to the file in the storage provider
        :return: Public URL for the file
        """
        normalized_path = file_path.replace("\\", "/")
        return urljoin(self.base_url.rstrip("/") + "/", normalized_path)

    async def exists(self, file_path: str) -> bool:
        """
        Check if local file exists.

        :param file_path: Path to the file in the storage provider
        :return: True if the file exists, False otherwise
        """
        try:
            full_path = self._get_path(file_path)
            return full_path.exists() and full_path.is_file()
        except Exception as e:
            logger.error(f"Error checking file existence {file_path}: {str(e)}")
            return False

    def _ensure_directory_exists(self, path: Path) -> None:
        """Ensure the directory exists, creating it if necessary."""
        try:
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                os.chmod(path, self.dir_permissions)
                logger.info("Created directory: %s", path)
        except Exception as e:
            raise ValueError(f"Failed to create directory {path}: {str(e)}")

    def _get_path(self, file_path: str) -> Path:
        """Get validated path within the base storage directory."""
        if not file_path:
            raise ValueError("File path cannot be empty")

        file_path = file_path.strip().replace("\\", "/")
        file_path = file_path.lstrip("/")

        full_path = (self.base_path / file_path).resolve()

        if not self._is_path_within_base(full_path):
            raise ValueError(
                f"File path {file_path} is outside the base storage directory"
            )

        return full_path

    def _is_path_within_base(self, path: Path) -> bool:
        """Check if path is within the base directory (security check)."""
        try:
            path.relative_to(self.base_path)
            return True
        except ValueError:
            return False

    def _cleanup_empty_directories(self, directory: Path) -> None:
        """Remove empty parent directories up to base_path."""
        try:
            if not self._is_path_within_base(directory):
                return

            if directory == self.base_path:
                return

            # Check if directory is empty
            if directory.exists() and directory.is_dir():
                try:
                    directory.rmdir()
                    logger.debug(f"Removed empty directory: {directory}")

                    # Recursively cleanup parent
                    self._cleanup_empty_directories(directory.parent)

                except OSError:
                    pass

        except Exception as e:
            logger.debug(f"Error during directory cleanup: {str(e)}")

    def get_storage_stats(self) -> dict:
        """
        Get storage statistics.

        :return: Dictionary with storage statistics
        """
        stats: dict = {
            "total_files": 0,
            "total_size_bytes": 0,
            "directories": 0,
            "base_path": str(self.base_path),
            "available_space_bytes": 0,
        }

        try:
            if self.base_path.exists():
                # Count files and calculate total size
                for item in self.base_path.rglob("*"):
                    if item.is_file():
                        stats["total_files"] += 1
                        stats["total_size_bytes"] += item.stat().st_size
                    elif item.is_dir():
                        stats["directories"] += 1

                # Get available disk space
                statvfs = os.statvfs(self.base_path)
                stats["available_space_bytes"] = statvfs.f_frsize * statvfs.f_bavail

        except Exception as e:
            logger.error(f"Error getting storage stats: {str(e)}")

        return stats

    def __str__(self) -> str:
        return f"LocalStorageProvider(base_path={self.base_path})"

    def __repr__(self) -> str:
        return (
            f"LocalStorageProvider("
            f"base_path='{self.base_path}', "
            f"base_url='{self.base_url}', "
            f"file_permissions={oct(self.file_permissions)}, "
            f"dir_permissions={oct(self.dir_permissions)}"
            f")"
        )
