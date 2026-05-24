from fastapi import APIRouter, Depends

from app.core.responses import success_payload
from app.core.security import AuthContext, get_auth_context
from app.schemas.retrieval import RetrievalAnswerRequest, RetrievalSearchRequest
from app.services.retrieval_service import RetrievalService

router = APIRouter()
service = RetrievalService()


@router.post("/search")
def search(request: RetrievalSearchRequest, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.search(auth.user_id, request))


@router.post("/answer")
def answer(request: RetrievalAnswerRequest, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.answer(auth.user_id, request))

