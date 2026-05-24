from uuid import UUID

from pydantic import Field

from app.schemas.base import PlatformModel
from app.schemas.auth import EMAIL_PATTERN


class ProfileCreateRequest(PlatformModel):
    display_name: str = Field(min_length=1, max_length=120)
    email: str | None = Field(default=None, pattern=EMAIL_PATTERN)


class ProfileResponse(PlatformModel):
    user_id: UUID
    cognito_sub: str
    email: str | None = None
    display_name: str
    status: str = "active"
