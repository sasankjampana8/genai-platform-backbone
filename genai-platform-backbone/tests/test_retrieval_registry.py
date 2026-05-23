from uuid import uuid4

from app.registries.retrieval import retrieval_registry
from app.schemas.retrieval import RetrievalSearchRequest


def test_retrieval_registry_lists_expected_strategies() -> None:
    names = {item["name"] for item in retrieval_registry.list()}
    assert {"vector", "hybrid_rrf", "query_rewrite", "hyde", "adaptive"} <= names


def test_query_rewrite_strategy_returns_rewritten_query() -> None:
    request = RetrievalSearchRequest(knowledge_base_id=uuid4(), query="What did the document say?")
    response = retrieval_registry.get("query_rewrite").search(uuid4(), request)
    assert response.rewritten_query
    assert response.results

