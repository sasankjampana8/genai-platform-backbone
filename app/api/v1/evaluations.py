from uuid import UUID

import json

from fastapi import APIRouter, Depends, File, UploadFile

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


@router.post("/datasets/{dataset_id}/cases/upload")
async def upload_cases(dataset_id: UUID, file: UploadFile = File(...), auth: AuthContext = Depends(get_auth_context)) -> dict:
    data = await file.read()
    if file.filename and file.filename.lower().endswith(".csv"):
        import io
        import pandas as pd

        rows = pd.read_csv(io.BytesIO(data)).fillna("").to_dict(orient="records")
    else:
        parsed = json.loads(data.decode("utf-8"))
        rows = parsed if isinstance(parsed, list) else parsed.get("cases", [])
    return success_payload(service.create_cases_bulk(auth.user_id, dataset_id, rows))


@router.post("/runs")
def create_evaluation_run(request: EvaluationRunCreateRequest, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.create_run(auth.user_id, request))


@router.get("/runs/{evaluation_run_id}")
def get_evaluation_run(evaluation_run_id: UUID, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.get_run(auth.user_id, evaluation_run_id))
