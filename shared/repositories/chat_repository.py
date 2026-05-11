from boto3.dynamodb.conditions import Key

from shared.config import settings
from shared.repositories.base import clean_for_dynamodb, int_value, now_iso, table


def chats_table():
    return table(settings.CHAT_TABLE)


def messages_table():
    return table(settings.MESSAGE_TABLE)


def put_chat(item: dict) -> None:
    chats_table().put_item(Item=clean_for_dynamodb(item))


def get_chat_for_user(chat_id: str, user_id: str) -> dict | None:
    response = chats_table().get_item(Key={"chat_id": chat_id})
    item = response.get("Item")
    if not item or item.get("user_id") != user_id or item.get("status") == "DELETED":
        return None
    return item


def list_chats_for_user(user_id: str, limit: int = 50) -> list[dict]:
    response = chats_table().query(
        IndexName="user_id-updated_at-index",
        KeyConditionExpression=Key("user_id").eq(user_id),
        ScanIndexForward=False,
        Limit=limit,
    )
    return [item for item in response.get("Items", []) if item.get("status") != "DELETED"]


def update_chat_after_message(chat_id: str, preview: str, increment: int = 1) -> None:
    chats_table().update_item(
        Key={"chat_id": chat_id},
        UpdateExpression=(
            "SET #last_message_preview = :preview, #updated_at = :updated_at "
            "ADD #message_count :increment"
        ),
        ExpressionAttributeNames={
            "#last_message_preview": "last_message_preview",
            "#updated_at": "updated_at",
            "#message_count": "message_count",
        },
        ExpressionAttributeValues=clean_for_dynamodb(
            {":preview": preview[:240], ":updated_at": now_iso(), ":increment": increment}
        ),
    )


def put_message(item: dict) -> None:
    messages_table().put_item(Item=clean_for_dynamodb(item))


def get_message_for_user(chat_id: str, message_id: str, user_id: str) -> dict | None:
    response = messages_table().get_item(Key={"chat_id": chat_id, "message_id": message_id})
    item = response.get("Item")
    if not item or item.get("user_id") != user_id:
        return None
    return item


def list_messages_for_chat(chat_id: str, user_id: str, limit: int = 100) -> list[dict]:
    response = messages_table().query(
        KeyConditionExpression=Key("chat_id").eq(chat_id),
        ScanIndexForward=True,
        Limit=limit,
    )
    return [item for item in response.get("Items", []) if item.get("user_id") == user_id]


def update_message_status(
    chat_id: str,
    message_id: str,
    status: str,
    *,
    content: str | None = None,
    citations: list[dict] | None = None,
    artifacts: list[dict] | None = None,
    error_message: str | None = None,
) -> None:
    names = {"#status": "status", "#updated_at": "updated_at"}
    values = {":status": status, ":updated_at": now_iso()}
    assignments = ["#status = :status", "#updated_at = :updated_at"]
    if content is not None:
        names["#content"] = "content"
        values[":content"] = content
        assignments.append("#content = :content")
    if citations is not None:
        names["#citations"] = "citations"
        values[":citations"] = citations
        assignments.append("#citations = :citations")
    if artifacts is not None:
        names["#artifacts"] = "artifacts"
        values[":artifacts"] = artifacts
        assignments.append("#artifacts = :artifacts")
    if error_message is not None:
        names["#error_message"] = "error_message"
        values[":error_message"] = error_message
        assignments.append("#error_message = :error_message")

    messages_table().update_item(
        Key={"chat_id": chat_id, "message_id": message_id},
        UpdateExpression="SET " + ", ".join(assignments),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=clean_for_dynamodb(values),
    )


def message_count(chat: dict) -> int:
    return int_value(chat.get("message_count"), 0)
