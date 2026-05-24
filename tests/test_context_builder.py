from uuid import uuid4

from app.schemas.retrieval import RetrievedChunk
from app.services.context_builder import ContextBuilder


def test_context_builder_formats_citations() -> None:
    chunk = RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        knowledge_base_id=uuid4(),
        text="Important source text",
        score=0.88,
        page_number=3,
    )
    context = ContextBuilder().build([chunk])
    assert "[1]" in context
    assert "page 3" in context
    assert "Important source text" in context

