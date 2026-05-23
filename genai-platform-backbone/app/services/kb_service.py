from uuid import UUID, uuid4

from app.core.errors import NotFoundError
from app.repositories.memory import store
from app.schemas.knowledge_bases import KnowledgeBaseCreateRequest, KnowledgeBaseResponse


class KnowledgeBaseService:
    def create(self, user_id: UUID, request: KnowledgeBaseCreateRequest) -> KnowledgeBaseResponse:
        item = KnowledgeBaseResponse(
            knowledge_base_id=uuid4(),
            user_id=user_id,
            name=request.name,
            description=request.description,
            status="active",
        )
        store.knowledge_bases[item.knowledge_base_id] = item.model_dump()
        return item

    def list(self, user_id: UUID) -> list[KnowledgeBaseResponse]:
        return [KnowledgeBaseResponse(**item) for item in store.knowledge_bases.values() if item["user_id"] == user_id]

    def get(self, user_id: UUID, knowledge_base_id: UUID) -> KnowledgeBaseResponse:
        item = store.knowledge_bases.get(knowledge_base_id)
        if not item or item["user_id"] != user_id:
            raise NotFoundError("Knowledge base not found.")
        return KnowledgeBaseResponse(**item)

