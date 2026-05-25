from dataclasses import dataclass
from uuid import UUID

from app.repositories.sql import repository


@dataclass
class VectorChunkRecord:
    chunk_id: UUID
    document_id: UUID
    knowledge_base_id: UUID
    user_id: UUID
    text: str
    embedding: list[float]
    metadata: dict
    page_number: int | None = None
    parent_chunk_id: UUID | None = None
    chunk_index: int = 0
    embedding_model: str = "text-embedding-3-small"
    chunking_strategy: str = "recursive"


class PgVectorStoreProvider:
    def upsert_chunks(self, chunks: list[VectorChunkRecord]) -> int:
        return repository.insert_chunks(
            [
                {
                    "chunk_id": record.chunk_id,
                    "document_id": record.document_id,
                    "knowledge_base_id": record.knowledge_base_id,
                    "user_id": record.user_id,
                    "parent_chunk_id": record.parent_chunk_id,
                    "chunk_index": record.chunk_index,
                    "chunk_text": record.text,
                    "page_number": record.page_number,
                    "embedding": record.embedding,
                    "embedding_model": record.embedding_model,
                    "chunking_strategy": record.chunking_strategy,
                    "metadata": record.metadata,
                }
                for record in chunks
            ]
        )

    def search(
        self,
        *,
        user_id: UUID,
        knowledge_base_id: UUID,
        query_embedding: list[float],
        top_k: int,
        filters: dict | None = None,
    ) -> list[dict]:
        return repository.vector_search(
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            query_embedding=query_embedding,
            top_k=top_k,
            filters=filters,
        )


class MockVectorStoreProvider:
    def __init__(self) -> None:
        self.records: list[VectorChunkRecord] = []

    def upsert_chunks(self, chunks: list[VectorChunkRecord]) -> int:
        self.records.extend(chunks)
        return len(chunks)

    def search(self, *, user_id: UUID, knowledge_base_id: UUID, query_embedding: list[float], top_k: int, filters: dict | None = None) -> list[dict]:
        return [
            {
                "chunk_id": record.chunk_id,
                "document_id": record.document_id,
                "knowledge_base_id": record.knowledge_base_id,
                "text": record.text,
                "score": 0.75,
                "page_number": record.page_number,
                "metadata": record.metadata,
            }
            for record in self.records
            if record.user_id == user_id and record.knowledge_base_id == knowledge_base_id
        ][:top_k]
