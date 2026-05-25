from uuid import UUID

from app.core.config import settings
from app.providers.model_gateway import get_model_gateway
from app.providers.reranker import get_reranker
from app.providers.vector_store import MockVectorStoreProvider, PgVectorStoreProvider
from app.repositories.sql import repository
from app.schemas.retrieval import Citation, RetrievedChunk, RetrievalAnswerRequest, RetrievalAnswerResponse, RetrievalSearchRequest, RetrievalSearchResponse
from app.services.context_builder import ContextBuilder


def reciprocal_rank_fusion(result_sets: list[list[dict]], k: int = 60) -> list[dict]:
    fused: dict[str, dict] = {}
    for results in result_sets:
        for rank, item in enumerate(results, 1):
            key = str(item["chunk_id"])
            if key not in fused:
                fused[key] = {**item, "score": 0.0}
            fused[key]["score"] += 1.0 / (k + rank)
    return sorted(fused.values(), key=lambda item: item["score"], reverse=True)


class RetrievalService:
    def __init__(self) -> None:
        self.context_builder = ContextBuilder()
        self.model_gateway = get_model_gateway()
        self.vector_store = MockVectorStoreProvider() if settings.mock_mode else PgVectorStoreProvider()
        self.reranker = get_reranker()

    def _query_for_strategy(self, request: RetrievalSearchRequest) -> tuple[str, str | None]:
        strategy = request.options.strategy
        if strategy in {"query_rewrite", "adaptive"} or request.options.query_rewrite:
            response = self.model_gateway.generate_answer(
                [
                    {"role": "system", "content": "Rewrite the user question as a concise search query. Return only the query."},
                    {"role": "user", "content": request.query},
                ]
            )
            rewritten = response["content"].strip() or request.query
            return rewritten, rewritten
        if strategy == "hyde":
            response = self.model_gateway.generate_answer(
                [
                    {"role": "system", "content": "Write a short hypothetical answer passage that would appear in a relevant document."},
                    {"role": "user", "content": request.query},
                ]
            )
            hypothetical = response["content"].strip() or request.query
            return hypothetical, hypothetical
        return request.query, None

    def search(self, user_id: UUID, request: RetrievalSearchRequest) -> RetrievalSearchResponse:
        search_query, rewritten_query = self._query_for_strategy(request)
        embedding = self.model_gateway.embed_texts([search_query])[0]
        candidate_k = request.options.candidate_k
        vector_results = self.vector_store.search(
            user_id=user_id,
            knowledge_base_id=request.knowledge_base_id,
            query_embedding=embedding,
            top_k=candidate_k,
            filters=request.filters,
        )
        if request.options.strategy in {"hybrid_rrf", "adaptive"} and not settings.mock_mode:
            keyword_results = repository.keyword_search(
                user_id=user_id,
                knowledge_base_id=request.knowledge_base_id,
                query=request.query,
                top_k=candidate_k,
                filters=request.filters,
            )
            raw_results = reciprocal_rank_fusion([vector_results, keyword_results])[:candidate_k]
        else:
            raw_results = vector_results[:candidate_k]

        if request.options.rerank and raw_results:
            reranked = self.reranker.rerank(request.query, [item["text"] for item in raw_results], request.options.top_k)
            ordered = [raw_results[item["index"]] | {"score": item["score"]} for item in reranked if item["index"] < len(raw_results)]
        else:
            ordered = raw_results[: request.options.top_k]

        results = [
            RetrievedChunk(
                chunk_id=item["chunk_id"],
                document_id=item["document_id"],
                knowledge_base_id=item["knowledge_base_id"],
                text=item["text"],
                score=float(item["score"]),
                page_number=item.get("page_number"),
                metadata=item.get("metadata") or {},
            )
            for item in ordered
        ]
        return RetrievalSearchResponse(
            query=request.query,
            rewritten_query=rewritten_query,
            strategy=request.options.strategy,
            results=results,
        )

    def answer(self, user_id: UUID, request: RetrievalAnswerRequest) -> RetrievalAnswerResponse:
        retrieval = self.search(user_id, request)
        context = self.context_builder.build(retrieval.results)
        response = self.model_gateway.generate_answer(
            [
                {"role": "system", "content": self.context_builder.system_prompt()},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {request.query}"},
            ]
        )
        citations = [
            Citation(
                chunk_id=item.chunk_id,
                document_id=item.document_id,
                page_number=item.page_number,
                score=item.score,
            )
            for item in retrieval.results
        ]
        run = repository.create_run(
            {
                "user_id": user_id,
                "chat_id": request.chat_id,
                "status": "completed",
                "route": request.options.strategy,
                "answer": response["content"],
                "citations": [item.model_dump(mode="json") for item in citations],
                "token_usage": {
                    "input_tokens": response.get("input_tokens", 0),
                    "output_tokens": response.get("output_tokens", 0),
                    "model": response.get("model"),
                },
            }
        )
        return RetrievalAnswerResponse(answer=response["content"], citations=citations, run_id=run["run_id"], retrieval=retrieval)
