from uuid import UUID

from pydantic import Field

from app.schemas.base import PlatformModel

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegisterRequest(PlatformModel):
    email: str = Field(pattern=EMAIL_PATTERN)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)


class RegisterResponse(PlatformModel):
    user_id: UUID
    email: str
    status: str


class ConfirmRequest(PlatformModel):
    email: str = Field(pattern=EMAIL_PATTERN)
    confirmation_code: str = Field(min_length=4, max_length=20)


class LoginRequest(PlatformModel):
    email: str = Field(pattern=EMAIL_PATTERN)
    password: str = Field(min_length=8, max_length=128)


class LoginResponse(PlatformModel):
    access_token: str
    id_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int = 900


class RefreshRequest(PlatformModel):
    refresh_token: str


class LogoutRequest(PlatformModel):
    access_token: str
