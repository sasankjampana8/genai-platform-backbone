from datetime import UTC, datetime

from pydantic import ValidationError as PydanticValidationError

from shared.api_response import error_response, success_response
from shared.ids import generate_memory_id
from shared.logger import get_logger
from shared.repositories.memory_repository import (
    get_chat_for_user,
    list_memories,
    list_recent_messages,
    put_memory,
    update_chat_memory_summary,
)
from shared.request_context import AuthError, build_request_context, get_request_id, parse_json_body
from shared.schemas import SummarizeMemoryRequest

logger = get_logger(__name__)


def lambda_handler(event, context):
    request_id = get_request_id(event)
    route_key = event.get("routeKey", "")

    try:
        body = parse_json_body(event)
        request_context = build_request_context(event, body)
        chat_id = (event.get("pathParameters") or {}).get("chat_id")
        if not chat_id:
            raise ValueError("chat_id path parameter is required")

        if route_key == "GET /v1/chats/{chat_id}/memory":
            data = get_memory(request_context.user_id, chat_id)
        elif route_key == "POST /v1/chats/{chat_id}/memory/summarize":
            data = summarize_memory(request_context.user_id, chat_id, body)
        else:
            return error_response(
                request_id=request_id,
                code="NOT_FOUND",
                message="Memory route not found.",
                status_code=404,
            )

        return success_response(data, request_id=request_context.request_id)
    except AuthError as exc:
        return error_response(request_id=request_id, code="UNAUTHORIZED", message=str(exc), status_code=401)
    except PydanticValidationError as exc:
        return error_response(
            request_id=request_id,
            code="VALIDATION_ERROR",
            message="Invalid request payload.",
            details={"errors": exc.errors()},
            status_code=422,
        )
    except ValueError as exc:
        return error_response(request_id=request_id, code="BAD_REQUEST", message=str(exc), status_code=400)
    except LookupError as exc:
        return error_response(request_id=request_id, code="NOT_FOUND", message=str(exc), status_code=404)
    except Exception:
        logger.exception("memory handler failed | request_id=%s", request_id)
        return error_response(
            request_id=request_id,
            code="INTERNAL_SERVER_ERROR",
            message="Internal server error.",
            status_code=500,
        )


def get_memory(user_id: str, chat_id: str) -> dict:
    chat = require_chat(user_id, chat_id)
    return {
        "chat_id": chat_id,
        "memory_summary": chat.get("memory_summary"),
        "memories": [memory_summary(item) for item in list_memories(chat_id)],
    }


def summarize_memory(user_id: str, chat_id: str, body: dict) -> dict:
    require_chat(user_id, chat_id)
    payload = SummarizeMemoryRequest.model_validate(body or {})
    messages = list_recent_messages(chat_id, payload.source_message_limit)
    summary = build_deterministic_summary(messages)
    memory_id = generate_memory_id()
    now = now_iso()
    item = {
        "memory_id": memory_id,
        "user_id": user_id,
        "chat_id": chat_id,
        "memory_type": "CONVERSATION_SUMMARY",
        "content": summary,
        "source_message_ids": [message["message_id"] for message in messages if message.get("message_id")],
        "importance": 0.5,
        "created_at": now,
        "updated_at": now,
    }
    put_memory(item)
    update_chat_memory_summary(chat_id, summary)
    return {
        "chat_id": chat_id,
        "memory_id": memory_id,
        "status": "CREATED",
        "memory_summary": summary,
    }


def require_chat(user_id: str, chat_id: str) -> dict:
    chat = get_chat_for_user(chat_id, user_id)
    if not chat:
        raise LookupError("Chat not found")
    return chat


def build_deterministic_summary(messages: list[dict]) -> str:
    if not messages:
        return "No conversation messages are available to summarize yet."

    lines = []
    for message in messages[-10:]:
        role = str(message.get("role", "UNKNOWN")).lower()
        content = str(message.get("content", "")).strip().replace("\n", " ")
        if content:
            lines.append(f"{role}: {content[:240]}")

    if not lines:
        return "No completed message content is available to summarize yet."

    return "Conversation summary based on recent messages: " + " | ".join(lines)


def memory_summary(item: dict) -> dict:
    return {
        "memory_id": item["memory_id"],
        "memory_type": item["memory_type"],
        "content": item["content"],
        "source_message_ids": item.get("source_message_ids", []),
        "importance": float(item.get("importance", 0.5)),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
    }


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
