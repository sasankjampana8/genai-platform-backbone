from typing import Protocol

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class ModelGateway(Protocol):
    def embed_texts(self, texts: list[str], model: str | None = None) -> list[list[float]]: ...

    def generate_answer(self, messages: list[dict], model: str | None = None) -> dict: ...


class LiteLLMModelGateway:
    """LiteLLM-backed model gateway for generation and embeddings."""

    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required.")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def embed_texts(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        if not texts:
            return []
        from litellm import embedding

        response = embedding(
            model=model or settings.openai_embedding_model,
            input=texts,
            api_key=settings.openai_api_key,
        )
        return [item["embedding"] for item in response.data]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def generate_answer(self, messages: list[dict], model: str | None = None) -> dict:
        from litellm import completion

        response = completion(
            model=model or settings.openai_chat_model,
            messages=messages,
            api_key=settings.openai_api_key,
            temperature=0.2,
        )
        usage = getattr(response, "usage", None)
        message = response.choices[0].message
        return {
            "content": message.content or "",
            "model": response.model,
            "input_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
            "output_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
            "raw": response.model_dump() if hasattr(response, "model_dump") else dict(response),
        }


class MockModelGateway:
    """Test-only deterministic model gateway. Production services do not use this unless MOCK_MODE=true."""

    def embed_texts(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        return [[float((hash(text) + i) % 997) / 997 for i in range(settings.pgvector_dimension)] for text in texts]

    def generate_answer(self, messages: list[dict], model: str | None = None) -> dict:
        user_text = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        return {
            "content": f"Mock grounded answer for: {user_text[:240]}",
            "model": model or settings.openai_chat_model,
            "input_tokens": 0,
            "output_tokens": 0,
            "raw": {},
        }


def get_model_gateway() -> ModelGateway:
    if settings.mock_mode or not settings.openai_api_key:
        return MockModelGateway()
    return LiteLLMModelGateway()
