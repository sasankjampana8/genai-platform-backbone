from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID, NAMESPACE_URL, uuid5

import httpx
from fastapi import Header

from app.core.config import settings
from app.core.errors import UnauthorizedError
from app.repositories.sql import repository, user_id_from_cognito_sub


@dataclass(frozen=True)
class AuthContext:
    user_id: UUID
    cognito_sub: str
    email: str | None = None


def stable_mock_user_id(value: str = "local-dev-user") -> UUID:
    return uuid5(NAMESPACE_URL, value)


@lru_cache(maxsize=1)
def cognito_jwks() -> dict:
    issuer = settings.cognito_issuer or (
        f"https://cognito-idp.{settings.aws_region}.amazonaws.com/{settings.cognito_user_pool_id}"
    )
    response = httpx.get(f"{issuer}/.well-known/jwks.json", timeout=10)
    response.raise_for_status()
    return response.json()


def decode_cognito_token(token: str) -> dict:
    try:
        from jose import jwt
    except ImportError as exc:
        raise UnauthorizedError("python-jose is required for Cognito token validation.") from exc
    if not settings.cognito_user_pool_id:
        raise UnauthorizedError("COGNITO_USER_POOL_ID is not configured.")
    issuer = settings.cognito_issuer or (
        f"https://cognito-idp.{settings.aws_region}.amazonaws.com/{settings.cognito_user_pool_id}"
    )
    try:
        return jwt.decode(
            token,
            cognito_jwks(),
            algorithms=["RS256"],
            issuer=issuer,
            options={"verify_aud": False},
        )
    except Exception as exc:
        raise UnauthorizedError("Invalid bearer token.") from exc


def get_auth_context(authorization: str | None = Header(default=None)) -> AuthContext:
    if settings.auth_disabled or settings.mock_mode:
        return AuthContext(
            user_id=stable_mock_user_id(),
            cognito_sub="local-dev-user",
            email="local@example.com",
        )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing bearer token.")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise UnauthorizedError("Empty bearer token.")
    claims = decode_cognito_token(token)
    cognito_sub = claims.get("sub")
    if not cognito_sub:
        raise UnauthorizedError("Token is missing subject claim.")
    email = claims.get("email") or claims.get("username") or claims.get("cognito:username")
    user = repository.ensure_user(cognito_sub=cognito_sub, email=email, display_name=email, status="active")
    return AuthContext(user_id=user["user_id"], cognito_sub=cognito_sub, email=email)
