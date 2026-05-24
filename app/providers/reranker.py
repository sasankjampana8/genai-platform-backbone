from typing import Protocol

import boto3

from app.core.config import settings


class RerankerProvider(Protocol):
    def rerank(self, query: str, documents: list[str], top_n: int) -> list[dict]: ...


class BedrockCohereReranker:
    def __init__(self) -> None:
        self.client = boto3.client("bedrock-runtime", region_name=settings.bedrock_region)

    def rerank(self, query: str, documents: list[str], top_n: int) -> list[dict]:
        # Bedrock Cohere Rerank payloads differ by model/version. Keep this
        # method isolated so the exact payload can be adjusted without touching
        # retrieval services.
        raise NotImplementedError("Bedrock Cohere rerank provider needs account-specific payload validation.")


class MockReranker:
    def rerank(self, query: str, documents: list[str], top_n: int) -> list[dict]:
        return [
            {"index": index, "score": 1.0 / (index + 1), "document": document}
            for index, document in enumerate(documents[:top_n])
        ]

