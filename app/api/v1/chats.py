from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.responses import success_payload
from app.core.security import AuthContext, get_auth_context
from app.schemas.chats import ChatCreateRequest, SendMessageRequest
from app.services.chat_service import ChatService

router = APIRouter()
service = ChatService()


@router.post("/chats")
def create_chat(request: ChatCreateRequest, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.create(auth.user_id, request))


@router.get("/chats")
def list_chats(auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload({"chats": service.list(auth.user_id)})


@router.post("/chats/{chat_id}/messages")
def send_message(chat_id: UUID, request: SendMessageRequest, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.send_message(auth.user_id, chat_id, request))


@router.get("/runs/{run_id}")
def get_run(run_id: UUID, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.get_run(auth.user_id, run_id))

