from typing import Any


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found.", details: dict[str, Any] | None = None) -> None:
        super().__init__("NOT_FOUND", message, 404, details)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized.") -> None:
        super().__init__("UNAUTHORIZED", message, 401)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict.", details: dict[str, Any] | None = None) -> None:
        super().__init__("CONFLICT", message, 409, details)

