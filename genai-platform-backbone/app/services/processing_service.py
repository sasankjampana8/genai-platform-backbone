from uuid import UUID, uuid4

from app.core.config import settings
from app.core.errors import NotFoundError
from app.providers.queue import MockQueueProvider
from app.repositories.memory import store
from app.schemas.processing import ProcessingJobCreateRequest, ProcessingJobResponse


class ProcessingService:
    def __init__(self) -> None:
        self.queue = MockQueueProvider()

    def create_job(self, user_id: UUID, request: ProcessingJobCreateRequest) -> ProcessingJobResponse:
        document = store.documents.get(request.document_id)
        if not document or document["user_id"] != user_id:
            raise NotFoundError("Document not found.")
        job = ProcessingJobResponse(
            processing_job_id=uuid4(),
            document_id=request.document_id,
            knowledge_base_id=request.knowledge_base_id,
            status="queued",
            stage="queued",
        )
        store.processing_jobs[job.processing_job_id] = {**job.model_dump(), "user_id": user_id}
        self.queue.send(settings.processing_queue_url or "mock-processing-queue", {"processing_job_id": str(job.processing_job_id)})
        return job

    def get_job(self, user_id: UUID, processing_job_id: UUID) -> ProcessingJobResponse:
        item = store.processing_jobs.get(processing_job_id)
        if not item or item["user_id"] != user_id:
            raise NotFoundError("Processing job not found.")
        return ProcessingJobResponse(**item)

