from uuid import UUID

from pydantic import Field

from app.schemas.base import PlatformModel


class KnowledgeBaseCreateRequest(PlatformModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)


class KnowledgeBaseResponse(PlatformModel):
    knowledge_base_id: UUID
    user_id: UUID
    name: str
    description: str | None = None
    status: str = "active"

