from boto3.dynamodb.conditions import Key

from shared.config import settings
from shared.repositories.base import clean_for_dynamodb, now_iso, table


def documents_table():
    return table(settings.DOCUMENT_TABLE)


def process_jobs_table():
    return table(settings.PROCESS_JOB_TABLE)


def put_document(item: dict) -> None:
    documents_table().put_item(Item=clean_for_dynamodb(item))


def get_document_for_user(document_id: str, user_id: str) -> dict | None:
    response = documents_table().get_item(Key={"document_id": document_id})
    item = response.get("Item")
    if not item or item.get("user_id") != user_id or item.get("status") == "DELETED":
        return None
    return item


def list_documents_for_user(user_id: str, limit: int = 50) -> list[dict]:
    response = documents_table().query(
        IndexName="user_id-created_at-index",
        KeyConditionExpression=Key("user_id").eq(user_id),
        ScanIndexForward=False,
        Limit=limit,
    )
    return [item for item in response.get("Items", []) if item.get("status") != "DELETED"]


def update_document_status(
    document_id: str,
    upload_status: str | None = None,
    processing_status: str | None = None,
    latest_process_id: str | None = None,
    chunk_count: int | None = None,
) -> None:
    names = {"#updated_at": "updated_at"}
    values = {":updated_at": now_iso()}
    parts = ["#updated_at = :updated_at"]
    for field, value in {
        "upload_status": upload_status,
        "processing_status": processing_status,
        "latest_process_id": latest_process_id,
        "chunk_count": chunk_count,
    }.items():
        if value is not None:
            names[f"#{field}"] = field
            values[f":{field}"] = clean_for_dynamodb(value)
            parts.append(f"#{field} = :{field}")

    documents_table().update_item(
        Key={"document_id": document_id},
        UpdateExpression="SET " + ", ".join(parts),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )


def mark_document_deleted(document_id: str) -> None:
    documents_table().update_item(
        Key={"document_id": document_id},
        UpdateExpression="SET #status = :status, #updated_at = :updated_at",
        ExpressionAttributeNames={"#status": "status", "#updated_at": "updated_at"},
        ExpressionAttributeValues={":status": "DELETED", ":updated_at": now_iso()},
    )


def put_process_job(item: dict) -> None:
    process_jobs_table().put_item(Item=clean_for_dynamodb(item))


def get_process_job_for_user(process_id: str, document_id: str, user_id: str) -> dict | None:
    response = process_jobs_table().get_item(Key={"process_id": process_id})
    item = response.get("Item")
    if not item or item.get("document_id") != document_id or item.get("user_id") != user_id:
        return None
    return item
