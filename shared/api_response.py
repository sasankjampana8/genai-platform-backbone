import json
from datetime import UTC, datetime
from typing import Any


DEFAULT_CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Methods": "OPTIONS,GET,POST,PUT,DELETE",
}


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def success_response(
    data: dict[str, Any] | list[Any] | None = None,
    *,
    request_id: str,
    status_code: int = 200,
    api_version: str = "v1",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = {
        "request_id": request_id,
        "status": "success",
        "data": data if data is not None else {},
        "metadata": {
            "timestamp": utc_now_iso(),
            "api_version": api_version,
            **(metadata or {}),
        },
    }
    return lambda_response(status_code, body)


def error_response(
    *,
    request_id: str,
    code: str,
    message: str,
    status_code: int = 400,
    details: dict[str, Any] | None = None,
    api_version: str = "v1",
) -> dict[str, Any]:
    body = {
        "request_id": request_id,
        "status": "error",
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
        "metadata": {
            "timestamp": utc_now_iso(),
            "api_version": api_version,
        },
    }
    return lambda_response(status_code, body)


def lambda_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": DEFAULT_CORS_HEADERS,
        "body": json.dumps(body, default=str),
    }


def build_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible Lambda response helper for gradual handler migration."""
    return lambda_response(status_code, body)
