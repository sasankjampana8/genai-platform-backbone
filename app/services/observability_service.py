from uuid import UUID, uuid4

from app.repositories.memory import store
from app.schemas.observability import FeedbackRequest, TraceResponse


class ObservabilityService:
    def feedback(self, user_id: UUID, request: FeedbackRequest) -> dict:
        item = {**request.model_dump(), "user_id": user_id}
        store.feedback.append(item)
        return {"status": "recorded"}

    def trace(self, user_id: UUID, run_id: UUID) -> TraceResponse:
        return TraceResponse(
            run_id=run_id,
            trace_id=uuid4(),
            spans=[{"name": "mock_trace_loaded", "status": "success"}],
            metadata={"source": "mock"},
        )

