from uuid import UUID

from pydantic import Field

from app.schemas.base import PlatformModel
from app.schemas.retrieval import Citation


class ChatCreateRequest(PlatformModel):
    title: str = Field(default="New chat", min_length=1, max_length=160)
    knowledge_base_id: UUID | None = None


class ChatResponse(PlatformModel):
    chat_id: UUID
    user_id: UUID
    title: str
    status: str = "active"


class SendMessageRequest(PlatformModel):
    content: str = Field(min_length=1, max_length=12000)
    knowledge_base_id: UUID | None = None
    retrieval_strategy: str = "hybrid_rrf"


class SendMessageResponse(PlatformModel):
    chat_id: UUID
    message_id: UUID
    run_id: UUID
    status: str


class RunResponse(PlatformModel):
    run_id: UUID
    chat_id: UUID | None = None
    status: str
    route: str | None = None
    answer: str | None = None
    citations: list[Citation] = Field(default_factory=list)

