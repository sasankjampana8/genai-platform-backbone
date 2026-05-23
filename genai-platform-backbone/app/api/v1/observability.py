from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.responses import success_payload
from app.core.security import AuthContext, get_auth_context
from app.schemas.observability import FeedbackRequest
from app.services.observability_service import ObservabilityService

router = APIRouter()
service = ObservabilityService()


@router.post("/feedback")
def feedback(request: FeedbackRequest, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.feedback(auth.user_id, request))


@router.get("/runs/{run_id}/trace")
def trace(run_id: UUID, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.trace(auth.user_id, run_id))

