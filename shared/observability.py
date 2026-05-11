from time import perf_counter

from shared.api_response import utc_now_iso
from shared.config import settings
from shared.ids import generate_span_id, generate_trace_id
from shared.s3_service import put_json


def start_trace(run_id: str, user_id: str, chat_id: str, message_id: str) -> dict:
    return {
        "trace_id": generate_trace_id(),
        "run_id": run_id,
        "user_id": user_id,
        "chat_id": chat_id,
        "message_id": message_id,
        "status": "RUNNING",
        "spans": [],
        "retrieved_chunks": [],
        "tool_calls": [],
        "artifacts": [],
        "errors": [],
        "created_at": utc_now_iso(),
    }


def start_span(trace: dict, name: str, attributes: dict | None = None, parent_span_id: str | None = None) -> str:
    span_id = generate_span_id()
    trace.setdefault("spans", []).append(
        {
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "name": name,
            "start_time": utc_now_iso(),
            "_start_perf": perf_counter(),
            "end_time": None,
            "latency_ms": None,
            "status": "running",
            "attributes": attributes or {},
        }
    )
    return span_id


def _find_span(trace: dict, span_id: str) -> dict | None:
    return next((span for span in trace.get("spans", []) if span.get("span_id") == span_id), None)


def end_span(trace: dict, span_id: str, status: str = "success", attributes: dict | None = None) -> None:
    span = _find_span(trace, span_id)
    if not span:
        return
    start_perf = span.pop("_start_perf", None)
    span["end_time"] = utc_now_iso()
    span["status"] = status
    if start_perf is not None:
        span["latency_ms"] = int((perf_counter() - start_perf) * 1000)
    if attributes:
        span.setdefault("attributes", {}).update(attributes)


def record_error(trace: dict, span_id: str | None, error: Exception | str) -> None:
    message = str(error)
    trace.setdefault("errors", []).append({"message": message, "timestamp": utc_now_iso(), "span_id": span_id})
    if span_id:
        end_span(trace, span_id, status="error", attributes={"error": message})


def save_trace_to_s3(trace: dict, user_id: str, run_id: str) -> str:
    s3_key = f"traces/{user_id}/{run_id}/trace.json"
    sanitized = {
        **trace,
        "spans": [{k: v for k, v in span.items() if not k.startswith("_")} for span in trace.get("spans", [])],
    }
    put_json(settings.RAW_BUCKET, s3_key, sanitized)
    return s3_key


def summarize_trace(trace: dict) -> dict:
    spans = [{k: v for k, v in span.items() if not k.startswith("_")} for span in trace.get("spans", [])]
    total_latency = sum(int(span.get("latency_ms") or 0) for span in spans)
    return {
        "trace_id": trace.get("trace_id"),
        "status": trace.get("status"),
        "latency_ms": total_latency,
        "span_count": len(spans),
        "error_count": len(trace.get("errors", [])),
    }
