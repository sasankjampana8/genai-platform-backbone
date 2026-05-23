from uuid import UUID

from pydantic import Field

from app.schemas.base import PlatformModel


class FeedbackRequest(PlatformModel):
    run_id: UUID
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class TraceResponse(PlatformModel):
    run_id: UUID
    trace_id: UUID
    spans: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

