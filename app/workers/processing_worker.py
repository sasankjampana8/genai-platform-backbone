from uuid import UUID, uuid4

from app.core.logging import get_logger
from app.providers.model_gateway import MockModelGateway
from app.providers.vector_store import MockVectorStoreProvider, VectorChunkRecord
from app.registries.chunking import chunking_registry
from app.services.extraction_service import ExtractionService

logger = get_logger(__name__)


class ProcessingWorker:
    def __init__(self) -> None:
        self.extractor = ExtractionService()
        self.model_gateway = MockModelGateway()
        self.vector_store = MockVectorStoreProvider()

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
    ) -> dict:
        logger.info("processing_document_started", extra={"document_id": str(document_id)})
        extracted = self.extractor.extract(file_bytes, file_name, content_type)
        chunks = chunking_registry.get(chunking_strategy).chunk(extracted.full_text)
        embeddings = self.model_gateway.embed_texts([chunk.text for chunk in chunks])
        records = [
            VectorChunkRecord(
                chunk_id=uuid4(),
                document_id=document_id,
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
                text=chunk.text,
                embedding=embedding,
                metadata={**(chunk.metadata or {}), "chunking_strategy": chunking_strategy},
                page_number=1,
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        inserted = self.vector_store.upsert_chunks(records)
        logger.info("processing_document_completed", extra={"document_id": str(document_id), "chunks": inserted})
        return {
            "document_id": str(document_id),
            "pages_extracted": len(extracted.pages),
            "chunks_created": len(chunks),
            "chunks_indexed": inserted,
        }


def main() -> None:
    logger.info("processing_worker_started")
    logger.info("SQS polling is intentionally not wired in local scaffold mode.")


if __name__ == "__main__":
    main()

