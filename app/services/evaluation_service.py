from uuid import UUID

from app.core.config import settings
from app.repositories.memory import store
from app.repositories.sql import repository
from app.schemas.evaluations import DatasetCreateRequest, EvaluationCaseCreateRequest, EvaluationRunCreateRequest, EvaluationRunResponse
from app.schemas.retrieval import RetrievalAnswerRequest, RetrievalOptions
from app.services.retrieval_service import RetrievalService


class EvaluationService:
    def __init__(self) -> None:
        self.retrieval = RetrievalService()

    def create_dataset(self, user_id: UUID, request: DatasetCreateRequest) -> dict:
        if settings.mock_mode:
            from uuid import uuid4

            dataset_id = uuid4()
            item = {"dataset_id": dataset_id, "user_id": user_id, "name": request.name, "description": request.description}
            store.evaluation_datasets[dataset_id] = item
            return item
        return repository.create_evaluation_dataset(user_id=user_id, name=request.name, description=request.description)

    def create_case(self, user_id: UUID, dataset_id: UUID, request: EvaluationCaseCreateRequest) -> dict:
        if settings.mock_mode:
            from uuid import uuid4

            case = {"case_id": uuid4(), "dataset_id": dataset_id, **request.model_dump()}
            store.evaluation_cases[dataset_id].append(case)
            return case
        return repository.create_evaluation_case(
            dataset_id=dataset_id,
            query=request.query,
            expected_answer=request.expected_answer,
            expected_citations=[str(item) for item in request.expected_citations],
        )

    def create_cases_bulk(self, user_id: UUID, dataset_id: UUID, rows: list[dict]) -> dict:
        created = []
        for row in rows:
            case = EvaluationCaseCreateRequest(
                query=row["query"],
                expected_answer=row.get("expected_answer") or row.get("reference_answer"),
                expected_citations=row.get("expected_citations") or [],
            )
            created.append(self.create_case(user_id, dataset_id, case))
        return {"dataset_id": dataset_id, "cases_created": len(created), "cases": created}

    def create_run(self, user_id: UUID, request: EvaluationRunCreateRequest) -> EvaluationRunResponse:
        if settings.mock_mode:
            from uuid import uuid4

            run = EvaluationRunResponse(evaluation_run_id=uuid4(), dataset_id=request.dataset_id, status="queued")
            store.evaluation_runs[run.evaluation_run_id] = {**run.model_dump(), "user_id": user_id}
            return run

        cases = repository.list_evaluation_cases(request.dataset_id)
        scores = []
        for case in cases:
            answer = self.retrieval.answer(
                user_id,
                RetrievalAnswerRequest(
                    knowledge_base_id=request.knowledge_base_id,
                    query=case["query"],
                    options=RetrievalOptions(strategy=request.retrieval_strategy),
                ),
            )
            expected = (case.get("expected_answer") or "").lower()
            actual = answer.answer.lower()
            terms = {term for term in expected.split() if len(term) > 3}
            overlap = len([term for term in terms if term in actual])
            scores.append(overlap / max(len(terms), 1) if expected else 0.0)
        metrics = {
            "case_count": len(cases),
            "answer_term_recall": sum(scores) / max(len(scores), 1),
            "framework": "lightweight_builtin",
            "deepeval_ragas_ready": True,
        }
        run = repository.create_evaluation_run(
            user_id=user_id,
            dataset_id=request.dataset_id,
            knowledge_base_id=request.knowledge_base_id,
            status="completed",
            metrics=metrics,
        )
        return EvaluationRunResponse(**run)

    def get_run(self, user_id: UUID, evaluation_run_id: UUID) -> EvaluationRunResponse:
        if settings.mock_mode:
            return EvaluationRunResponse(**store.evaluation_runs[evaluation_run_id])
        return EvaluationRunResponse(**repository.get_evaluation_run(user_id, evaluation_run_id))
