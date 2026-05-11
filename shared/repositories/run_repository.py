from boto3.dynamodb.conditions import Key

from shared.config import settings
from shared.repositories.base import clean_for_dynamodb, now_iso, table


def runs_table():
    return table(settings.RUNS_TABLE)


def put_run(item: dict) -> None:
    runs_table().put_item(Item=clean_for_dynamodb(item))


def get_run_for_user(run_id: str, user_id: str) -> dict | None:
    response = runs_table().get_item(Key={"run_id": run_id})
    item = response.get("Item")
    if not item or item.get("user_id") != user_id:
        return None
    return item


def list_runs_for_user(user_id: str, limit: int = 50) -> list[dict]:
    response = runs_table().query(
        IndexName="user_id-created_at-index",
        KeyConditionExpression=Key("user_id").eq(user_id),
        ScanIndexForward=False,
        Limit=limit,
    )
    return response.get("Items", [])


def update_run(
    run_id: str,
    *,
    status: str | None = None,
    route: str | None = None,
    answer_preview: str | None = None,
    latency_ms: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    estimated_cost: float | None = None,
    trace_id: str | None = None,
    trace_s3_key: str | None = None,
    error_message: str | None = None,
) -> None:
    names = {"#updated_at": "updated_at"}
    values = {":updated_at": now_iso()}
    assignments = ["#updated_at = :updated_at"]
    for field_name, field_value in {
        "status": status,
        "route": route,
        "answer_preview": answer_preview,
        "latency_ms": latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost": estimated_cost,
        "trace_id": trace_id,
        "trace_s3_key": trace_s3_key,
        "error_message": error_message,
    }.items():
        if field_value is not None:
            names[f"#{field_name}"] = field_name
            values[f":{field_name}"] = field_value
            assignments.append(f"#{field_name} = :{field_name}")

    runs_table().update_item(
        Key={"run_id": run_id},
        UpdateExpression="SET " + ", ".join(assignments),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=clean_for_dynamodb(values),
    )
