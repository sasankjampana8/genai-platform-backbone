from uuid import UUID

from pydantic import Field

from app.schemas.base import PlatformModel


class ProcessingJobCreateRequest(PlatformModel):
    document_id: UUID
    knowledge_base_id: UUID
    chunking_strategy: str = "recursive"
    embedding_model: str = "text-embedding-3-small"


class ProcessingJobResponse(PlatformModel):
    processing_job_id: UUID
    document_id: UUID
    knowledge_base_id: UUID
    status: str
    stage: str = "queued"
    total_chunks: int = 0
    error_message: str | None = None


class ChunkingStrategyInfo(PlatformModel):
    name: str
    description: str
    supports_tables: bool = False
    supports_parent_child: bool = False
    default_options: dict = Field(default_factory=dict)

