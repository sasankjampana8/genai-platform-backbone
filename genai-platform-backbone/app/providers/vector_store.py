from dataclasses import dataclass
from uuid import UUID


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


class VectorStoreProvider:
    def upsert_chunks(self, chunks: list[VectorChunkRecord]) -> int:
        raise NotImplementedError

    def search(
        self,
        *,
        user_id: UUID,
        knowledge_base_id: UUID,
        query_embedding: list[float],
        top_k: int,
        filters: dict | None = None,
    ) -> list[dict]:
        raise NotImplementedError


class MockVectorStoreProvider(VectorStoreProvider):
    def __init__(self) -> None:
        self.records: list[VectorChunkRecord] = []

    def upsert_chunks(self, chunks: list[VectorChunkRecord]) -> int:
        self.records.extend(chunks)
        return len(chunks)

    def search(
        self,
        *,
        user_id: UUID,
        knowledge_base_id: UUID,
        query_embedding: list[float],
        top_k: int,
        filters: dict | None = None,
    ) -> list[dict]:
        matches = [
            record
            for record in self.records
            if record.user_id == user_id and record.knowledge_base_id == knowledge_base_id
        ]
        return [
            {
                "chunk_id": record.chunk_id,
                "document_id": record.document_id,
                "knowledge_base_id": record.knowledge_base_id,
                "text": record.text,
                "score": 0.75,
                "page_number": record.page_number,
                "metadata": {**record.metadata, "filters": filters or {}},
            }
            for record in matches[:top_k]
        ]

