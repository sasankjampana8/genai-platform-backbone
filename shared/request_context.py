import json
import os
import uuid
from dataclasses import dataclass
from typing import Any


class AuthError(ValueError):
    pass


@dataclass(frozen=True)
class RequestContext:
    request_id: str
    user_id: str
    email: str | None = None
    claims: dict[str, Any] | None = None
    auth_disabled: bool = False


def generate_request_id() -> str:
    return f"req_{uuid.uuid4().hex}"


def is_auth_disabled() -> bool:
    return os.getenv("AUTH_DISABLED", "false").lower() in {"1", "true", "yes", "on"}


def get_request_id(event: dict[str, Any] | None) -> str:
    event = event or {}
    request_context = event.get("requestContext") or {}
    api_request_id = request_context.get("requestId")
    if api_request_id:
        return f"req_{api_request_id}"
    headers = normalize_headers(event.get("headers") or {})
    return headers.get("x-request-id") or generate_request_id()


def normalize_headers(headers: dict[str, Any]) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in headers.items() if value is not None}


def parse_json_body(event: dict[str, Any] | None) -> dict[str, Any]:
    if not event:
        return {}
    body = event.get("body")
    if not body:
        return {}
    if isinstance(body, dict):
        return body
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Request body must be a JSON object")
    return parsed


def get_claims_from_event(event: dict[str, Any] | None) -> dict[str, Any]:
    event = event or {}
    request_context = event.get("requestContext") or {}
    authorizer = request_context.get("authorizer") or {}

    jwt_claims = (authorizer.get("jwt") or {}).get("claims")
    if isinstance(jwt_claims, dict):
        return jwt_claims

    lambda_claims = authorizer.get("claims")
    if isinstance(lambda_claims, dict):
        return lambda_claims

    return {}


def get_user_id(event: dict[str, Any] | None, body: dict[str, Any] | None = None) -> str | None:
    claims = get_claims_from_event(event)
    user_id = claims.get("sub") or claims.get("cognito:username") or claims.get("username")
    if user_id:
        return str(user_id)

    if is_auth_disabled():
        body = body or {}
        return str(body.get("user_id") or os.getenv("LOCAL_USER_ID", "user_123"))

    return None


def get_user_email(event: dict[str, Any] | None) -> str | None:
    claims = get_claims_from_event(event)
    email = claims.get("email")
    return str(email) if email else None


def require_user_id(event: dict[str, Any] | None, body: dict[str, Any] | None = None) -> str:
    user_id = get_user_id(event, body)
    if not user_id:
        raise AuthError("Authenticated user is required")
    return user_id


def build_request_context(event: dict[str, Any] | None, body: dict[str, Any] | None = None) -> RequestContext:
    claims = get_claims_from_event(event)
    return RequestContext(
        request_id=get_request_id(event),
        user_id=require_user_id(event, body),
        email=get_user_email(event),
        claims=claims,
        auth_disabled=is_auth_disabled(),
    )
