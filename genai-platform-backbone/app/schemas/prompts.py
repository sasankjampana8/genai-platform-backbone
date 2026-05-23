from uuid import UUID

from pydantic import Field

from app.schemas.base import PlatformModel


class PromptCreateRequest(PlatformModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None


class PromptVersionCreateRequest(PlatformModel):
    template: str = Field(min_length=1)
    variables: list[str] = Field(default_factory=list)


class PromptResponse(PlatformModel):
    prompt_id: UUID
    name: str
    description: str | None = None

