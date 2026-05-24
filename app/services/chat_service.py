from uuid import UUID, uuid4

from app.core.errors import NotFoundError
from app.repositories.memory import store
from app.schemas.chats import ChatCreateRequest, ChatResponse, RunResponse, SendMessageRequest, SendMessageResponse


class ChatService:
    def create(self, user_id: UUID, request: ChatCreateRequest) -> ChatResponse:
        chat = ChatResponse(chat_id=uuid4(), user_id=user_id, title=request.title, status="active")
        store.chats[chat.chat_id] = chat.model_dump()
        return chat

    def list(self, user_id: UUID) -> list[ChatResponse]:
        return [ChatResponse(**item) for item in store.chats.values() if item["user_id"] == user_id]

    def send_message(self, user_id: UUID, chat_id: UUID, request: SendMessageRequest) -> SendMessageResponse:
        chat = store.chats.get(chat_id)
        if not chat or chat["user_id"] != user_id:
            raise NotFoundError("Chat not found.")
        message_id = uuid4()
        run_id = uuid4()
        store.messages[chat_id].append({"message_id": message_id, "role": "user", "content": request.content})
        store.runs[run_id] = {
            "run_id": run_id,
            "chat_id": chat_id,
            "user_id": user_id,
            "status": "queued",
            "route": "rag" if request.knowledge_base_id else "direct",
        }
        return SendMessageResponse(chat_id=chat_id, message_id=message_id, run_id=run_id, status="queued")

    def get_run(self, user_id: UUID, run_id: UUID) -> RunResponse:
        run = store.runs.get(run_id)
        if not run or run["user_id"] != user_id:
            raise NotFoundError("Run not found.")
        return RunResponse(**run)

