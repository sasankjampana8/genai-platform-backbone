import json
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from shared.config import settings
from shared.logger import get_logger
from shared.openai_service import client, embed_query as openai_embed_query, embed_texts as openai_embed_texts

logger = get_logger(__name__)


def _ensure_openai_key() -> None:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required for model calls")


def _usage_dict(response: Any) -> dict:
    usage = getattr(response, "usage", None)
    if not usage:
        return {"input_tokens": 0, "output_tokens": 0}
    return {
        "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
    }


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    # Conservative placeholder until provider pricing config is added.
    return round(((input_tokens / 1_000_000) * 0.20) + ((output_tokens / 1_000_000) * 0.80), 6)


def embed_texts(texts: list[str], model: str | None = None) -> list[list[float]]:
    _ensure_openai_key()
    return openai_embed_texts(texts, model or settings.OPENAI_EMBEDDING_MODEL)


def embed_query(query: str, model: str | None = None) -> list[float]:
    _ensure_openai_key()
    return openai_embed_query(query, model or settings.OPENAI_EMBEDDING_MODEL)


@retry(wait=wait_exponential(min=1, max=20), stop=stop_after_attempt(3), reraise=True)
def generate_answer(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.2,
) -> dict:
    _ensure_openai_key()
    model_name = model or settings.OPENAI_LLM_MODEL
    logger.info("Generating model answer with model=%s", model_name)
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
    )
    content = response.choices[0].message.content or ""
    usage = _usage_dict(response)
    return {
        "content": content,
        "model": model_name,
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "estimated_cost": _estimate_cost(usage["input_tokens"], usage["output_tokens"]),
        "raw": {},
    }


def generate_json(messages: list[dict], model: str | None = None) -> dict:
    result = generate_answer(messages, model=model, temperature=0.0)
    try:
        return json.loads(result["content"])
    except json.JSONDecodeError:
        return {"content": result["content"]}


def summarize_text(text: str, model: str | None = None) -> str:
    result = generate_answer(
        [
            {"role": "system", "content": "Summarize the text into concise, durable memory notes."},
            {"role": "user", "content": text},
        ],
        model=model,
        temperature=0.1,
    )
    return result["content"]
