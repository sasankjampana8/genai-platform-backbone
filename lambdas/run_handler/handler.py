import json

from shared.api_response import error_response, success_response
from shared.config import settings
from shared.logger import get_logger
from shared.repositories import run_repository
from shared.request_context import AuthError, build_request_context, parse_json_body
from shared.s3_service import download_file_bytes

logger = get_logger(__name__)


def _route_key(event: dict) -> str:
    return event.get("routeKey") or f"{event.get('requestContext', {}).get('http', {}).get('method')} {event.get('rawPath')}"


def lambda_handler(event, context):
    request_id = "req_unknown"
    try:
        body = parse_json_body(event)
        ctx = build_request_context(event, body)
        request_id = ctx.request_id
        route_key = _route_key(event)
        params = event.get("pathParameters") or {}
        logger.info("run handler route=%s request_id=%s user_id=%s", route_key, request_id, ctx.user_id)

        if route_key == "GET /v1/runs":
            return success_response({"runs": run_repository.list_runs_for_user(ctx.user_id)}, request_id=request_id)

        if route_key == "GET /v1/runs/{run_id}":
            run = run_repository.get_run_for_user(params["run_id"], ctx.user_id)
            if not run:
                return error_response(request_id=request_id, code="NOT_FOUND", message="Run not found.", status_code=404)
            return success_response(run, request_id=request_id)

        if route_key == "GET /v1/runs/{run_id}/trace":
            run = run_repository.get_run_for_user(params["run_id"], ctx.user_id)
            if not run:
                return error_response(request_id=request_id, code="NOT_FOUND", message="Run not found.", status_code=404)
            trace_key = run.get("trace_s3_key")
            if not trace_key:
                return success_response({"trace": None, "message": "Trace is not available yet."}, request_id=request_id)
            trace = json.loads(download_file_bytes(settings.RAW_BUCKET, trace_key).decode("utf-8"))
            return success_response({"trace": trace}, request_id=request_id)

        if route_key == "GET /v1/observability/summary":
            runs = run_repository.list_runs_for_user(ctx.user_id, limit=100)
            completed = [item for item in runs if item.get("status") == "COMPLETED"]
            failed = [item for item in runs if item.get("status") == "FAILED"]
            latency_values = [int(item.get("latency_ms") or 0) for item in completed]
            routes: dict[str, int] = {}
            for item in runs:
                route = item.get("route") or "UNKNOWN"
                routes[route] = routes.get(route, 0) + 1
            return success_response(
                {
                    "window": "latest_100_runs",
                    "total_runs": len(runs),
                    "completed_runs": len(completed),
                    "failed_runs": len(failed),
                    "avg_latency_ms": int(sum(latency_values) / len(latency_values)) if latency_values else 0,
                    "total_input_tokens": sum(int(item.get("input_tokens") or 0) for item in runs),
                    "total_output_tokens": sum(int(item.get("output_tokens") or 0) for item in runs),
                    "estimated_cost": sum(float(item.get("estimated_cost") or 0) for item in runs),
                    "routes": routes,
                },
                request_id=request_id,
            )

        if route_key == "GET /v1/observability/errors":
            runs = run_repository.list_runs_for_user(ctx.user_id, limit=100)
            return success_response(
                {"errors": [item for item in runs if item.get("status") == "FAILED"]},
                request_id=request_id,
            )

        return error_response(request_id=request_id, code="NOT_FOUND", message="Route not found.", status_code=404)
    except AuthError as exc:
        return error_response(request_id=request_id, code="UNAUTHORIZED", message=str(exc), status_code=401)
    except Exception:
        logger.exception("run handler failed")
        return error_response(request_id=request_id, code="INTERNAL_ERROR", message="Internal server error.", status_code=500)
