from uuid import UUID, uuid4

from app.repositories.memory import store
from app.schemas.evaluations import DatasetCreateRequest, EvaluationCaseCreateRequest, EvaluationRunCreateRequest, EvaluationRunResponse


class EvaluationService:
    def create_dataset(self, user_id: UUID, request: DatasetCreateRequest) -> dict:
        dataset_id = uuid4()
        item = {"dataset_id": dataset_id, "user_id": user_id, "name": request.name, "description": request.description}
        store.evaluation_datasets[dataset_id] = item
        return item

    def create_case(self, user_id: UUID, dataset_id: UUID, request: EvaluationCaseCreateRequest) -> dict:
        case = {"case_id": uuid4(), "dataset_id": dataset_id, **request.model_dump()}
        store.evaluation_cases[dataset_id].append(case)
        return case

    def create_run(self, user_id: UUID, request: EvaluationRunCreateRequest) -> EvaluationRunResponse:
        run = EvaluationRunResponse(evaluation_run_id=uuid4(), dataset_id=request.dataset_id, status="queued")
        store.evaluation_runs[run.evaluation_run_id] = {**run.model_dump(), "user_id": user_id}
        return run

    def get_run(self, user_id: UUID, evaluation_run_id: UUID) -> EvaluationRunResponse:
        return EvaluationRunResponse(**store.evaluation_runs[evaluation_run_id])

