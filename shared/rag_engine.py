from shared.prompt_builder import build_citations, build_context_from_chunks
from shared.retrieval_service import retrieve_relevant_chunks


def retrieve_context(
    *,
    user_id: str,
    query: str,
    document_ids: list[str] | None = None,
    top_k: int = 5,
    similarity_threshold: float | None = None,
    metadata_filters: dict | None = None,
) -> dict:
    chunks = retrieve_relevant_chunks(
        user_id=user_id,
        query=query,
        document_ids=document_ids,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        metadata_filters=metadata_filters,
        use_reranking=True,
        include_parent_context=True,
    )
    context_chunks = [
        {
            **chunk,
            "text": chunk.get("parent_context") or chunk.get("text") or "",
        }
        for chunk in chunks
    ]
    return {
        "chunks": chunks,
        "context": build_context_from_chunks(context_chunks),
        "citations": build_citations(chunks),
        "strategy": "vector_lexical_rerank_parent_context",
    }
