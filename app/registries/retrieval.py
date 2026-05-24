from typing import Protocol
from uuid import UUID, uuid4

from app.schemas.retrieval import RetrievedChunk, RetrievalSearchRequest, RetrievalSearchResponse


class RetrievalStrategy(Protocol):
    name: str
    description: str

    def search(self, user_id: UUID, request: RetrievalSearchRequest) -> RetrievalSearchResponse: ...


def _mock_result(request: RetrievalSearchRequest, strategy: str) -> RetrievalSearchResponse:
    chunk = RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        knowledge_base_id=request.knowledge_base_id,
        text=f"Mock retrieved context for query: {request.query}",
        score=0.91,
        page_number=1,
        metadata={"strategy": strategy},
    )
    return RetrievalSearchResponse(query=request.query, strategy=strategy, results=[chunk])


class VectorRetrieval:
    name = "vector"
    description = "OpenAI query embedding plus pgvector cosine search."

    def search(self, user_id: UUID, request: RetrievalSearchRequest) -> RetrievalSearchResponse:
        return _mock_result(request, self.name)


class HybridRrfRetrieval(VectorRetrieval):
    name = "hybrid_rrf"
    description = "Vector retrieval plus keyword retrieval with reciprocal rank fusion."


class QueryRewriteRetrieval(VectorRetrieval):
    name = "query_rewrite"
    description = "Rewrites the query before retrieval and stores original plus rewritten query in trace."

    def search(self, user_id: UUID, request: RetrievalSearchRequest) -> RetrievalSearchResponse:
        response = _mock_result(request, self.name)
        response.rewritten_query = f"Rewritten: {request.query}"
        return response


class HyDERetrieval(VectorRetrieval):
    name = "hyde"
    description = "Uses a hypothetical answer passage embedding for retrieval, then reranks on original query."


class AdaptiveRetrieval(VectorRetrieval):
    name = "adaptive"
    description = "Chooses retrieval behavior based on query type and confidence."


class RetrievalRegistry:
    def __init__(self) -> None:
        self._strategies: dict[str, RetrievalStrategy] = {}

    def register(self, strategy: RetrievalStrategy) -> None:
        self._strategies[strategy.name] = strategy

    def get(self, name: str) -> RetrievalStrategy:
        if name not in self._strategies:
            raise KeyError(f"Unknown retrieval strategy: {name}")
        return self._strategies[name]

    def list(self) -> list[dict]:
        return [{"name": item.name, "description": item.description} for item in self._strategies.values()]


retrieval_registry = RetrievalRegistry()
for _strategy in [
    VectorRetrieval(),
    HybridRrfRetrieval(),
    QueryRewriteRetrieval(),
    HyDERetrieval(),
    AdaptiveRetrieval(),
]:
    retrieval_registry.register(_strategy)

