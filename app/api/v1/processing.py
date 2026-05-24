from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.responses import success_payload
from app.core.security import AuthContext, get_auth_context
from app.schemas.processing import ProcessingJobCreateRequest
from app.services.processing_service import ProcessingService

router = APIRouter()
service = ProcessingService()


@router.post("/jobs")
def create_processing_job(request: ProcessingJobCreateRequest, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.create_job(auth.user_id, request))


@router.get("/jobs/{processing_job_id}")
def get_processing_job(processing_job_id: UUID, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.get_job(auth.user_id, processing_job_id))

