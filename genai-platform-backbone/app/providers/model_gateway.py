from typing import Protocol

from openai import OpenAI

from app.core.config import settings


class ModelGateway(Protocol):
    def embed_texts(self, texts: list[str], model: str | None = None) -> list[list[float]]: ...

    def generate_answer(self, messages: list[dict], model: str | None = None) -> dict: ...


class OpenAIModelGateway:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when MOCK_MODE=false")
        self.client = OpenAI(api_key=settings.openai_api_key)

    def embed_texts(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        response = self.client.embeddings.create(model=model or settings.openai_embedding_model, input=texts)
        return [item.embedding for item in response.data]

    def generate_answer(self, messages: list[dict], model: str | None = None) -> dict:
        response = self.client.chat.completions.create(
            model=model or settings.openai_chat_model,
            messages=messages,
            temperature=0.2,
        )
        usage = response.usage
        return {
            "content": response.choices[0].message.content or "",
            "model": response.model,
            "input_tokens": usage.prompt_tokens if usage else 0,
            "output_tokens": usage.completion_tokens if usage else 0,
            "raw": response.model_dump(),
        }


class MockModelGateway:
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

