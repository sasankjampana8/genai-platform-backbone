from uuid import UUID

from app.core.config import settings
from app.core.errors import NotFoundError
from app.repositories.memory import store
from app.repositories.sql import repository
from app.schemas.chats import ChatCreateRequest, ChatResponse, RunResponse, SendMessageRequest, SendMessageResponse
from app.schemas.retrieval import RetrievalAnswerRequest, RetrievalOptions
from app.services.retrieval_service import RetrievalService


class ChatService:
    def __init__(self) -> None:
        self.retrieval = RetrievalService()

    def create(self, user_id: UUID, request: ChatCreateRequest) -> ChatResponse:
        if settings.mock_mode:
            from uuid import uuid4

            chat = ChatResponse(chat_id=uuid4(), user_id=user_id, title=request.title, status="active")
            store.chats[chat.chat_id] = chat.model_dump()
            return chat
        if request.knowledge_base_id:
            repository.get_knowledge_base(user_id, request.knowledge_base_id)
        return ChatResponse(**repository.create_chat(user_id=user_id, title=request.title, knowledge_base_id=request.knowledge_base_id))

    def list(self, user_id: UUID) -> list[ChatResponse]:
        if settings.mock_mode:
            return [ChatResponse(**item) for item in store.chats.values() if item["user_id"] == user_id]
        return [ChatResponse(**item) for item in repository.list_chats(user_id)]

    def send_message(self, user_id: UUID, chat_id: UUID, request: SendMessageRequest) -> SendMessageResponse:
        if settings.mock_mode:
            from uuid import uuid4

            chat = store.chats.get(chat_id)
            if not chat or chat["user_id"] != user_id:
                raise NotFoundError("Chat not found.")
            message_id = uuid4()
            run_id = uuid4()
            store.messages[chat_id].append({"message_id": message_id, "role": "user", "content": request.content})
            store.runs[run_id] = {"run_id": run_id, "chat_id": chat_id, "user_id": user_id, "status": "queued", "route": "mock"}
            return SendMessageResponse(chat_id=chat_id, message_id=message_id, run_id=run_id, status="queued")

        chat = repository.get_chat(user_id, chat_id)
        knowledge_base_id = request.knowledge_base_id or chat.get("knowledge_base_id")
        user_message = repository.create_message(user_id=user_id, chat_id=chat_id, role="user", content=request.content)
        if not knowledge_base_id:
            from app.providers.model_gateway import get_model_gateway

            response = get_model_gateway().generate_answer([{"role": "user", "content": request.content}])
            assistant = repository.create_message(
                user_id=user_id,
                chat_id=chat_id,
                role="assistant",
                content=response["content"],
                metadata={"source": "direct"},
            )
            run = repository.create_run(
                {
                    "user_id": user_id,
                    "chat_id": chat_id,
                    "message_id": user_message["message_id"],
                    "status": "completed",
                    "route": "direct",
                    "answer": response["content"],
                    "token_usage": {
                        "input_tokens": response.get("input_tokens", 0),
                        "output_tokens": response.get("output_tokens", 0),
                        "model": response.get("model"),
                    },
                }
            )
            return SendMessageResponse(chat_id=chat_id, message_id=assistant["message_id"], run_id=run["run_id"], status="completed")

        answer = self.retrieval.answer(
            user_id,
            RetrievalAnswerRequest(
                chat_id=chat_id,
                knowledge_base_id=knowledge_base_id,
                query=request.content,
                options=RetrievalOptions(strategy=request.retrieval_strategy),
            ),
        )
        assistant = repository.create_message(
            user_id=user_id,
            chat_id=chat_id,
            role="assistant",
            content=answer.answer,
            metadata={"citations": [citation.model_dump(mode="json") for citation in answer.citations]},
        )
        return SendMessageResponse(chat_id=chat_id, message_id=assistant["message_id"], run_id=answer.run_id, status="completed")

    def get_run(self, user_id: UUID, run_id: UUID) -> RunResponse:
        if settings.mock_mode:
            run = store.runs.get(run_id)
            if not run or run["user_id"] != user_id:
                raise NotFoundError("Run not found.")
            return RunResponse(**run)
        return RunResponse(**repository.get_run(user_id, run_id))
