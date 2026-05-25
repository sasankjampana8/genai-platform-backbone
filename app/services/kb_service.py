from uuid import UUID

from app.core.config import settings
from app.repositories.memory import store
from app.repositories.sql import repository
from app.schemas.knowledge_bases import KnowledgeBaseCreateRequest, KnowledgeBaseResponse


class KnowledgeBaseService:
    def create(self, user_id: UUID, request: KnowledgeBaseCreateRequest) -> KnowledgeBaseResponse:
        if settings.mock_mode:
            from uuid import uuid4

            item = KnowledgeBaseResponse(
                knowledge_base_id=uuid4(),
                user_id=user_id,
                name=request.name,
                description=request.description,
                status="active",
            )
            store.knowledge_bases[item.knowledge_base_id] = item.model_dump()
            return item
        return KnowledgeBaseResponse(**repository.create_knowledge_base(user_id=user_id, name=request.name, description=request.description))

    def list(self, user_id: UUID) -> list[KnowledgeBaseResponse]:
        if settings.mock_mode:
            return [KnowledgeBaseResponse(**item) for item in store.knowledge_bases.values() if item["user_id"] == user_id]
        return [KnowledgeBaseResponse(**item) for item in repository.list_knowledge_bases(user_id)]

    def get(self, user_id: UUID, knowledge_base_id: UUID) -> KnowledgeBaseResponse:
        if settings.mock_mode:
            from app.core.errors import NotFoundError

            item = store.knowledge_bases.get(knowledge_base_id)
            if not item or item["user_id"] != user_id:
                raise NotFoundError("Knowledge base not found.")
            return KnowledgeBaseResponse(**item)
        return KnowledgeBaseResponse(**repository.get_knowledge_base(user_id, knowledge_base_id))
