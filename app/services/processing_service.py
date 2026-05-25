from uuid import UUID

from app.core.config import settings
from app.providers.queue import MockQueueProvider, SqsQueueProvider
from app.repositories.memory import store
from app.repositories.sql import repository
from app.schemas.processing import ProcessingJobCreateRequest, ProcessingJobResponse
from app.workers.processing_worker import ProcessingWorker


class ProcessingService:
    def __init__(self) -> None:
        self.queue = MockQueueProvider() if settings.mock_mode else SqsQueueProvider()
        self.worker = ProcessingWorker()

    def create_job(self, user_id: UUID, request: ProcessingJobCreateRequest) -> ProcessingJobResponse:
        if settings.mock_mode:
            from app.core.errors import NotFoundError
            from uuid import uuid4

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
            return job

        document = repository.get_document(user_id, request.document_id)
        repository.get_knowledge_base(user_id, request.knowledge_base_id)
        job = repository.create_processing_job(
            user_id=user_id,
            document_id=request.document_id,
            knowledge_base_id=request.knowledge_base_id,
            chunking_strategy=request.chunking_strategy,
            embedding_model=request.embedding_model,
        )
        repository.update_document_status(user_id, request.document_id, "queued")
        if settings.inline_processing:
            try:
                repository.update_processing_job(job["processing_job_id"], status="processing", stage="extract_chunk_embed_index")
                result = self.worker.process_document_from_storage(
                    user_id=user_id,
                    knowledge_base_id=request.knowledge_base_id,
                    document_id=request.document_id,
                    file_name=document["file_name"],
                    content_type=document["content_type"],
                    s3_key=document["s3_key"],
                    chunking_strategy=request.chunking_strategy,
                    embedding_model=request.embedding_model,
                )
                repository.update_processing_job(
                    job["processing_job_id"],
                    status="completed",
                    stage="completed",
                    total_chunks=result["chunks_indexed"],
                )
                repository.update_document_status(user_id, request.document_id, "processed")
                job = repository.get_processing_job(user_id, job["processing_job_id"])
            except Exception as exc:
                repository.update_processing_job(
                    job["processing_job_id"],
                    status="failed",
                    stage="failed",
                    error_message=str(exc),
                )
                repository.update_document_status(user_id, request.document_id, "failed")
                raise
        else:
            self.queue.send(settings.processing_queue_url or "", {"processing_job_id": str(job["processing_job_id"])})
        return ProcessingJobResponse(**job)

    def get_job(self, user_id: UUID, processing_job_id: UUID) -> ProcessingJobResponse:
        if settings.mock_mode:
            from app.core.errors import NotFoundError

            item = store.processing_jobs.get(processing_job_id)
            if not item or item["user_id"] != user_id:
                raise NotFoundError("Processing job not found.")
            return ProcessingJobResponse(**item)
        return ProcessingJobResponse(**repository.get_processing_job(user_id, processing_job_id))
