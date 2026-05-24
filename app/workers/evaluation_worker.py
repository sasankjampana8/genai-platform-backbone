from app.core.logging import get_logger

logger = get_logger(__name__)


class EvaluationWorker:
    def run_evaluation(self, evaluation_run_id: str) -> dict:
        logger.info("evaluation_run_started", extra={"evaluation_run_id": evaluation_run_id})
        return {
            "evaluation_run_id": evaluation_run_id,
            "status": "COMPLETED",
            "metrics": {
                "faithfulness": 1.0,
                "context_precision": 1.0,
                "answer_relevance": 1.0,
            },
        }


def main() -> None:
    logger.info("evaluation_worker_started")
    logger.info("SQS polling is intentionally not wired in local scaffold mode.")


if __name__ == "__main__":
    main()

