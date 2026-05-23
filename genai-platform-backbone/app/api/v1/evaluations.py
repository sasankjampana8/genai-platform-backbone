from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.responses import success_payload
from app.core.security import AuthContext, get_auth_context
from app.schemas.evaluations import DatasetCreateRequest, EvaluationCaseCreateRequest, EvaluationRunCreateRequest
from app.services.evaluation_service import EvaluationService

router = APIRouter()
service = EvaluationService()


@router.post("/datasets")
def create_dataset(request: DatasetCreateRequest, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.create_dataset(auth.user_id, request))


@router.post("/datasets/{dataset_id}/cases")
def create_case(dataset_id: UUID, request: EvaluationCaseCreateRequest, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.create_case(auth.user_id, dataset_id, request))


@router.post("/runs")
def create_evaluation_run(request: EvaluationRunCreateRequest, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.create_run(auth.user_id, request))


@router.get("/runs/{evaluation_run_id}")
def get_evaluation_run(evaluation_run_id: UUID, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.get_run(auth.user_id, evaluation_run_id))

