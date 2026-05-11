import json

from pydantic import ValidationError as PydanticValidationError

from shared.api_response import error_response, success_response
from shared.ids import generate_chat_id, generate_message_id, generate_run_id
from shared.logger import get_logger
from shared.repositories import chat_repository, run_repository
from shared.repositories.base import now_iso
from shared.request_context import AuthError, build_request_context, parse_json_body
from shared.schemas import CreateChatRequest, SendMessageRequest
from shared.sqs_service import send_runtime_message

logger = get_logger(__name__)


def _path_params(event: dict) -> dict:
    return event.get("pathParameters") or {}


def _route_key(event: dict) -> str:
    return event.get("routeKey") or f"{event.get('requestContext', {}).get('http', {}).get('method')} {event.get('rawPath')}"


def _preview(text: str) -> str:
    return " ".join(text.split())[:240]


def lambda_handler(event, context):
    body = {}
    request_id = "req_unknown"
    try:
        body = parse_json_body(event)
        ctx = build_request_context(event, body)
        request_id = ctx.request_id
        route_key = _route_key(event)
        params = _path_params(event)
        logger.info("chat handler route=%s request_id=%s user_id=%s", route_key, request_id, ctx.user_id)

        if route_key == "POST /v1/chats":
            payload = CreateChatRequest.model_validate(body)
            now = now_iso()
            chat = {
                "chat_id": generate_chat_id(),
                "user_id": ctx.user_id,
                "title": payload.title,
                "status": "ACTIVE",
                "message_count": 0,
                "last_message_preview": None,
                "memory_summary": "",
                "created_at": now,
                "updated_at": now,
            }
            chat_repository.put_chat(chat)
            return success_response(chat, request_id=request_id, status_code=201)

        if route_key == "GET /v1/chats":
            return success_response({"chats": chat_repository.list_chats_for_user(ctx.user_id)}, request_id=request_id)

        if route_key == "GET /v1/chats/{chat_id}":
            chat = chat_repository.get_chat_for_user(params["chat_id"], ctx.user_id)
            if not chat:
                return error_response(
                    request_id=request_id,
                    code="NOT_FOUND",
                    message="Chat not found.",
                    status_code=404,
                )
            return success_response(chat, request_id=request_id)

        if route_key == "GET /v1/chats/{chat_id}/messages":
            chat = chat_repository.get_chat_for_user(params["chat_id"], ctx.user_id)
            if not chat:
                return error_response(request_id=request_id, code="NOT_FOUND", message="Chat not found.", status_code=404)
            messages = chat_repository.list_messages_for_chat(params["chat_id"], ctx.user_id)
            return success_response({"messages": messages}, request_id=request_id)

        if route_key == "POST /v1/chats/{chat_id}/messages":
            chat = chat_repository.get_chat_for_user(params["chat_id"], ctx.user_id)
            if not chat:
                return error_response(request_id=request_id, code="NOT_FOUND", message="Chat not found.", status_code=404)
            payload = SendMessageRequest.model_validate(body)
            now = now_iso()
            message_id = generate_message_id()
            run_id = generate_run_id()
            user_message = {
                "chat_id": params["chat_id"],
                "message_id": message_id,
                "user_id": ctx.user_id,
                "role": "USER",
                "content": payload.input,
                "status": "QUEUED",
                "run_id": run_id,
                "citations": [],
                "artifacts": [],
                "created_at": now,
                "updated_at": now,
            }
            run = {
                "run_id": run_id,
                "user_id": ctx.user_id,
                "chat_id": params["chat_id"],
                "message_id": message_id,
                "status": "QUEUED",
                "query_preview": _preview(payload.input),
                "answer_preview": None,
                "route": None,
                "latency_ms": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "estimated_cost": 0,
                "trace_id": None,
                "trace_s3_key": None,
                "error_message": None,
                "created_at": now,
                "updated_at": now,
            }
            chat_repository.put_message(user_message)
            chat_repository.update_chat_after_message(params["chat_id"], _preview(payload.input))
            run_repository.put_run(run)
            send_runtime_message(
                {
                    "user_id": ctx.user_id,
                    "chat_id": params["chat_id"],
                    "message_id": message_id,
                    "run_id": run_id,
                    "input": payload.input,
                    "document_ids": payload.document_ids,
                    "runtime_options": payload.runtime_options.model_dump(),
                }
            )
            return success_response(
                {
                    "chat_id": params["chat_id"],
                    "message_id": message_id,
                    "run_id": run_id,
                    "status": "QUEUED",
                },
                request_id=request_id,
                status_code=202,
            )

        if route_key == "GET /v1/chats/{chat_id}/messages/{message_id}/response":
            chat = chat_repository.get_chat_for_user(params["chat_id"], ctx.user_id)
            if not chat:
                return error_response(request_id=request_id, code="NOT_FOUND", message="Chat not found.", status_code=404)
            message = chat_repository.get_message_for_user(params["chat_id"], params["message_id"], ctx.user_id)
            if not message:
                return error_response(request_id=request_id, code="NOT_FOUND", message="Message not found.", status_code=404)
            assistant = chat_repository.get_message_for_user(
                params["chat_id"],
                f"{params['message_id']}_assistant",
                ctx.user_id,
            )
            return success_response(
                {
                    "message_id": params["message_id"],
                    "status": message.get("status"),
                    "answer": assistant.get("content") if assistant else None,
                    "citations": assistant.get("citations", []) if assistant else [],
                    "artifacts": assistant.get("artifacts", []) if assistant else [],
                    "run_id": message.get("run_id"),
                    "error_message": message.get("error_message"),
                },
                request_id=request_id,
            )

        return error_response(request_id=request_id, code="NOT_FOUND", message="Route not found.", status_code=404)
    except AuthError as exc:
        return error_response(request_id=request_id, code="UNAUTHORIZED", message=str(exc), status_code=401)
    except (PydanticValidationError, ValueError) as exc:
        return error_response(request_id=request_id, code="VALIDATION_ERROR", message="Invalid request.", status_code=422, details={"errors": json.loads(exc.json()) if hasattr(exc, "json") else str(exc)})
    except Exception:
        logger.exception("chat handler failed")
        return error_response(request_id=request_id, code="INTERNAL_ERROR", message="Internal server error.", status_code=500)
