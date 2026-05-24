from datetime import UTC, datetime
from uuid import UUID, uuid4


class Trace:
    def __init__(self, run_id: UUID, user_id: UUID) -> None:
        self.trace_id = uuid4()
        self.run_id = run_id
        self.user_id = user_id
        self.spans: list[dict] = []
        self.metadata: dict = {}

    def span(self, name: str, **attributes) -> None:
        self.spans.append(
            {
                "span_id": str(uuid4()),
                "name": name,
                "timestamp": datetime.now(UTC).isoformat(),
                "attributes": attributes,
            }
        )

    def as_dict(self) -> dict:
        return {
            "trace_id": str(self.trace_id),
            "run_id": str(self.run_id),
            "user_id": str(self.user_id),
            "spans": self.spans,
            "metadata": self.metadata,
        }


class ObservabilityProvider:
    def start_trace(self, run_id: UUID, user_id: UUID) -> Trace:
        return Trace(run_id=run_id, user_id=user_id)

    def flush(self, trace: Trace) -> None:
        # External Langfuse emission should be best-effort and never block APIs.
        return None

