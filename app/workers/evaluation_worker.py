from app.core.logging import get_logger
from app.services.evaluation_service import EvaluationService

logger = get_logger(__name__)


class EvaluationWorker:
    def __init__(self, evaluation_service: EvaluationService | None = None) -> None:
        self.evaluation_service = evaluation_service or EvaluationService()

    def run_evaluation(self, evaluation_run_id: str) -> dict:
        logger.info("evaluation_run_started", extra={"evaluation_run_id": evaluation_run_id})
        return {
            "evaluation_run_id": evaluation_run_id,
            "status": "QUEUED",
            "metrics": {
                "message": "Evaluation runs are executed through the API service in the current deployment.",
            },
        }


def main() -> None:
    logger.info("evaluation_worker_started")
    logger.info("Evaluation worker entrypoint is reserved for async queue mode. Current deployment runs evaluations through the API service.")


if __name__ == "__main__":
    main()
