import json
from typing import Protocol

import boto3

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RerankerProvider(Protocol):
    def rerank(self, query: str, documents: list[str], top_n: int) -> list[dict]: ...


class BedrockCohereReranker:
    def __init__(self) -> None:
        self.client = boto3.client("bedrock-runtime", region_name=settings.bedrock_region)

    def rerank(self, query: str, documents: list[str], top_n: int) -> list[dict]:
        if not documents:
            return []
        payload = {
            "query": query,
            "documents": documents,
            "top_n": min(top_n, len(documents)),
            "api_version": 2,
        }
        response = self.client.invoke_model(
            modelId=settings.bedrock_rerank_model_id,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json",
        )
        body = json.loads(response["body"].read())
        results = body.get("results", [])
        return [
            {
                "index": int(item.get("index", 0)),
                "score": float(item.get("relevance_score", item.get("score", 0.0))),
                "document": documents[int(item.get("index", 0))],
            }
            for item in results
        ]


class LocalScoreReranker:
    def rerank(self, query: str, documents: list[str], top_n: int) -> list[dict]:
        query_terms = {term.lower() for term in query.split() if term.strip()}
        scored: list[dict] = []
        for index, document in enumerate(documents):
            terms = {term.lower().strip(".,:;()[]{}") for term in document.split()}
            overlap = len(query_terms & terms)
            scored.append({"index": index, "score": float(overlap), "document": document})
        return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_n]


def get_reranker() -> RerankerProvider:
    if settings.mock_mode or not settings.enable_bedrock_rerank:
        return LocalScoreReranker()
    return BedrockCohereReranker()
