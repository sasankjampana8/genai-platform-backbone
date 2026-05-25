from uuid import UUID

from app.core.config import settings
from app.core.logging import get_logger
from app.providers.model_gateway import get_model_gateway
from app.providers.object_storage import MockObjectStorageProvider, S3ObjectStorageProvider
from app.providers.vector_store import MockVectorStoreProvider, PgVectorStoreProvider, VectorChunkRecord
from app.registries.chunking import chunking_registry
from app.repositories.sql import repository
from app.services.extraction_service import ExtractionService

logger = get_logger(__name__)


class ProcessingWorker:
    def __init__(self) -> None:
        self.extractor = ExtractionService()
        self.model_gateway = get_model_gateway()
        self.storage = MockObjectStorageProvider() if settings.mock_mode else S3ObjectStorageProvider()
        self.vector_store = MockVectorStoreProvider() if settings.mock_mode else PgVectorStoreProvider()

    def process_document(
        self,
        *,
        user_id: UUID,
        knowledge_base_id: UUID,
        document_id: UUID,
        file_name: str,
        content_type: str,
        file_bytes: bytes,
        chunking_strategy: str = "recursive",
        embedding_model: str | None = None,
    ) -> dict:
        logger.info("processing_document_started", extra={"document_id": str(document_id)})
        extracted = self.extractor.extract(file_bytes, file_name, content_type)
        chunks = chunking_registry.get(chunking_strategy).chunk(extracted.full_text)
        model = embedding_model or settings.openai_embedding_model
        embeddings = self.model_gateway.embed_texts([chunk.text for chunk in chunks], model=model)
        records = [
            VectorChunkRecord(
                chunk_id=UUID(str(chunk.chunk_id)),
                document_id=document_id,
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
                parent_chunk_id=UUID(str(chunk.parent_chunk_id)) if chunk.parent_chunk_id else None,
                text=chunk.text,
                embedding=embedding,
                metadata={**(chunk.metadata or {}), "chunking_strategy": chunking_strategy},
                page_number=1,
                chunk_index=index,
                embedding_model=model,
                chunking_strategy=chunking_strategy,
            )
            for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
        ]
        if not settings.mock_mode:
            repository.delete_chunks_for_document(user_id, document_id)
        inserted = self.vector_store.upsert_chunks(records)
        logger.info("processing_document_completed", extra={"document_id": str(document_id), "chunks": inserted})
        return {
            "document_id": str(document_id),
            "pages_extracted": len(extracted.pages),
            "chunks_created": len(chunks),
            "chunks_indexed": inserted,
        }

    def process_document_from_storage(
        self,
        *,
        user_id: UUID,
        knowledge_base_id: UUID,
        document_id: UUID,
        file_name: str,
        content_type: str,
        s3_key: str,
        chunking_strategy: str,
        embedding_model: str,
    ) -> dict:
        return self.process_document(
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            file_name=file_name,
            content_type=content_type,
            file_bytes=self.storage.get_bytes(s3_key),
            chunking_strategy=chunking_strategy,
            embedding_model=embedding_model,
        )


def main() -> None:
    logger.info("processing_worker_started")
    logger.info("Long-poll SQS worker loop can call ProcessingWorker.process_document_from_storage per message.")


if __name__ == "__main__":
    main()
