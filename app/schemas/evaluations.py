from uuid import UUID

from pydantic import Field

from app.schemas.base import PlatformModel


class DatasetCreateRequest(PlatformModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None


class EvaluationCaseCreateRequest(PlatformModel):
    query: str = Field(min_length=1)
    expected_answer: str | None = None
    expected_citations: list[UUID] = Field(default_factory=list)


class EvaluationRunCreateRequest(PlatformModel):
    dataset_id: UUID
    knowledge_base_id: UUID
    retrieval_strategy: str = "hybrid_rrf"


class EvaluationRunResponse(PlatformModel):
    evaluation_run_id: UUID
    dataset_id: UUID
    status: str
    metrics: dict = Field(default_factory=dict)
