import os
from abc import ABC, abstractmethod
from typing import BinaryIO, Optional
import uuid
from datetime import datetime, UTC

from app.core.sanitizers import SlugSanitizer, FilenameSanitizer


class StorageMetadata:
    """Metadata about uploaded file"""

    def __init__(
        self,
        file_path: str,
        public_url: str | None,
        file_size: int,
        content_type: str,
        original_filename: str,
        storage_provider: str,
    ):
        self.file_path = file_path
        self.public_url = public_url
        self.file_size = file_size
        self.content_type = content_type
        self.original_filename = original_filename
        self.storage_provider = storage_provider


class StorageProvider(ABC):
    """Abstract base class for storage providers"""

    @abstractmethod
    async def upload(
        self,
        file: BinaryIO | bytes,
        filename: str,
        content_type: str,
        folder: str = "",
        public: bool = True,
    ) -> StorageMetadata:
        """
        Upload a file to the storage provider.
        :param file: File-like object to upload
        :param filename: Original filename
        :param content_type: MIME type of the file
        :param folder: Optional folder path to upload to
        :param public: Whether the file should be publicly accessible
        :return: StorageMetadata object with details about the uploaded file
        """
        pass

    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """
        Delete a file from the storage provider.
        :param file_path: Path to the file in the storage provider
        :return: True if deletion was successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_public_url(self, file_path: str) -> str:
        """
        Get the public URL for a file in the storage provider.
        :param file_path: Path to the file in the storage provider
        :return: Public URL for the file
        """
        pass

    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        """
        Check if a file exists in the storage provider.
        :param file_path: Path to the file in the storage provider
        :return: True if the file exists, False otherwise
        """
        pass

    @abstractmethod
    def get_storage_stats(self) -> dict:
        """
        Get storage statistics such as total space, used space, etc.
        :return: Dictionary with storage stats
        """
        pass

    @staticmethod
    def generate_unique_filename(
        original_filename: str, folder: Optional[str] = ""
    ) -> str:
        """
        Generate a secure, unique filename based on the original filename and current timestamp.
        :param original_filename: Original filename from user
        :param folder: Optional folder to prefix
        :return: Safe, namespaced filename
        """
        safe_filename = FilenameSanitizer.sanitize_filename(original_filename)

        name, ext = os.path.splitext(safe_filename)
        ext = ext.lower().lstrip(".")

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:12]

        final_name = (
            f"{timestamp}_{unique_id}_{SlugSanitizer.create_slug_from_text(name)}"
        )
        if ext:
            final_name = f"{final_name}.{ext}"

        if folder:
            safe_folder = SlugSanitizer.create_slug_from_text(folder.strip("/"))
            return f"{safe_folder}/{final_name}"
        return final_name
