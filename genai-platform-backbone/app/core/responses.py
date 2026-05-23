from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.core.config import settings


def new_request_id() -> str:
    return str(uuid4())


def timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def success_payload(data: Any, request_id: str | None = None) -> dict[str, Any]:
    return {
        "request_id": request_id or new_request_id(),
        "status": "success",
        "data": data,
        "metadata": {
            "timestamp": timestamp(),
            "api_version": settings.api_version,
        },
    }


def error_payload(
    code: str,
    message: str,
    request_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "request_id": request_id or new_request_id(),
        "status": "error",
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
        "metadata": {
            "timestamp": timestamp(),
            "api_version": settings.api_version,
        },
    }

