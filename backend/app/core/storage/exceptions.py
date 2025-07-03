class StorageException(Exception):
    """Base exception for storage operations"""

    pass


class StorageUploadException(StorageException):
    """Exception raised during file upload"""

    pass


class StorageDeleteException(StorageException):
    """Exception raised during file deletion"""

    pass


class StorageValidationException(StorageException):
    """Exception raised during file validation"""

    pass


class StoragePermissionException(StorageException):
    """Exception raised due to insufficient permissions"""

    pass


class StorageQuotaException(StorageException):
    """Exception raised when storage quota is exceeded"""

    pass
