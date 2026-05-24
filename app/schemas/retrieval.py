from uuid import UUID

from pydantic import Field

from app.schemas.base import PlatformModel


class RetrievalOptions(PlatformModel):
    strategy: str = "hybrid_rrf"
    top_k: int = Field(default=5, ge=1, le=20)
    candidate_k: int = Field(default=30, ge=1, le=200)
    rerank: bool = True
    query_rewrite: bool = False
    include_parent_context: bool = True


class RetrievalSearchRequest(PlatformModel):
    knowledge_base_id: UUID
    query: str = Field(min_length=1, max_length=4000)
    filters: dict = Field(default_factory=dict)
    options: RetrievalOptions = Field(default_factory=RetrievalOptions)


class RetrievedChunk(PlatformModel):
    chunk_id: UUID
    document_id: UUID
    knowledge_base_id: UUID
    text: str
    score: float
    page_number: int | None = None
    metadata: dict = Field(default_factory=dict)


class RetrievalSearchResponse(PlatformModel):
    query: str
    rewritten_query: str | None = None
    strategy: str
    results: list[RetrievedChunk]


class RetrievalAnswerRequest(RetrievalSearchRequest):
    chat_id: UUID | None = None


class Citation(PlatformModel):
    chunk_id: UUID
    document_id: UUID
    page_number: int | None = None
    score: float


class RetrievalAnswerResponse(PlatformModel):
    answer: str
    citations: list[Citation]
    run_id: UUID
    retrieval: RetrievalSearchResponse

