from typing import Any


class AppException(Exception):
    """Base exception for application errors."""

    def __init__(self, message: str, details: Any = None):
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundError(AppException):
    """Resource not found."""

    pass


class ValidationError(AppException):
    """Validation failed."""

    pass


class ConflictError(AppException):
    """Resource conflict (e.g., duplicate, optimistic lock)."""

    pass


class AuthenticationError(AppException):
    """Authentication failed."""

    pass


class AuthorizationError(AppException):
    """Insufficient permissions."""

    pass
