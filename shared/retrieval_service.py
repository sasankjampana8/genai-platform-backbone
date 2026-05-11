from shared.config import settings
from shared.openai_service import embed_query
from shared.pgvector_service import fetch_neighbor_chunks, search_chunk_candidates, search_chunks


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in text.replace("\n", " ").split() if len(token) > 2}


def _lexical_score(query: str, text: str) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    text_tokens = _tokens(text)
    return len(query_tokens & text_tokens) / len(query_tokens)


def _rerank_candidates(query: str, candidates: list[dict]) -> list[dict]:
    reranked = []
    for candidate in candidates:
        vector_score = float(candidate.get("score") or 0)
        lexical_score = _lexical_score(query, candidate.get("text") or "")
        combined_score = (0.82 * vector_score) + (0.18 * lexical_score)
        reranked.append(
            {
                **candidate,
                "vector_score": vector_score,
                "lexical_score": lexical_score,
                "score": combined_score,
                "retrieval_strategy": "vector_lexical_rerank",
            }
        )
    return sorted(reranked, key=lambda item: item["score"], reverse=True)


def _select_diverse(candidates: list[dict], top_k: int, per_document_limit: int = 4) -> list[dict]:
    selected = []
    document_counts: dict[str, int] = {}
    seen_chunks = set()
    for candidate in candidates:
        chunk_id = candidate.get("chunk_id")
        document_id = candidate.get("document_id") or ""
        if chunk_id in seen_chunks:
            continue
        if document_counts.get(document_id, 0) >= per_document_limit:
            continue
        selected.append(candidate)
        seen_chunks.add(chunk_id)
        document_counts[document_id] = document_counts.get(document_id, 0) + 1
        if len(selected) >= top_k:
            break
    return selected


def _attach_parent_context(user_id: str, chunks: list[dict], window: int = 1) -> list[dict]:
    enriched = []
    for chunk in chunks:
        try:
            neighbors = fetch_neighbor_chunks(
                user_id=user_id,
                document_id=chunk["document_id"],
                chunk_index=int(chunk.get("chunk_index") or 0),
                window=window,
            )
        except Exception:
            neighbors = []
        parent_text = "\n".join(item.get("text") or "" for item in neighbors).strip()
        enriched.append(
            {
                **chunk,
                "parent_context": parent_text or chunk.get("text", ""),
                "parent_context_chunk_ids": [item.get("chunk_id") for item in neighbors],
            }
        )
    return enriched


def retrieve_relevant_chunks(
    user_id: str,
    query: str,
    document_ids: list[str] | None = None,
    top_k: int = settings.DEFAULT_TOP_K,
    similarity_threshold: float | None = settings.DEFAULT_SIMILARITY_THRESHOLD,
    metadata_filters: dict | None = None,
    use_reranking: bool = True,
    include_parent_context: bool = True,
) -> list[dict]:
    query_embedding = embed_query(query, settings.OPENAI_EMBEDDING_MODEL)
    if use_reranking:
        candidates = search_chunk_candidates(
            user_id=user_id,
            query_embedding=query_embedding,
            document_ids=document_ids,
            candidate_k=max(top_k * 6, top_k),
            similarity_threshold=similarity_threshold,
            metadata_filters=metadata_filters,
        )
        reranked = _rerank_candidates(query, candidates)
        selected = _select_diverse(reranked, top_k=top_k)
        if include_parent_context:
            return _attach_parent_context(user_id, selected)
        return selected

    return search_chunks(
        user_id=user_id,
        query_embedding=query_embedding,
        document_ids=document_ids,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
    )
