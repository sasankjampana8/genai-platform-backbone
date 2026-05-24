from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.responses import success_payload
from app.core.security import AuthContext, get_auth_context
from app.schemas.knowledge_bases import KnowledgeBaseCreateRequest
from app.services.kb_service import KnowledgeBaseService

router = APIRouter()
service = KnowledgeBaseService()


@router.post("")
def create_knowledge_base(request: KnowledgeBaseCreateRequest, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.create(auth.user_id, request))


@router.get("")
def list_knowledge_bases(auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload({"knowledge_bases": service.list(auth.user_id)})


@router.get("/{knowledge_base_id}")
def get_knowledge_base(knowledge_base_id: UUID, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.get(auth.user_id, knowledge_base_id))

