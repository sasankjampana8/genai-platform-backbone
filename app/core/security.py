from dataclasses import dataclass
from uuid import UUID, uuid5, NAMESPACE_URL

from fastapi import Depends, Header

from app.core.config import settings
from app.core.errors import UnauthorizedError


@dataclass(frozen=True)
class AuthContext:
    user_id: UUID
    cognito_sub: str
    email: str | None = None


def stable_mock_user_id(value: str = "local-dev-user") -> UUID:
    return uuid5(NAMESPACE_URL, value)


def get_auth_context(authorization: str | None = Header(default=None)) -> AuthContext:
    if settings.auth_disabled or settings.mock_mode:
        return AuthContext(
            user_id=stable_mock_user_id(),
            cognito_sub="local-dev-user",
            email="local@example.com",
        )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing bearer token.")

    # Full Cognito JWKS validation is intentionally kept behind this dependency.
    # The deployment-ready interface is stable; production wiring should validate
    # issuer, audience, expiration, and signature before returning AuthContext.
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise UnauthorizedError("Empty bearer token.")
    raise UnauthorizedError("Cognito JWT validation is not configured yet.")

