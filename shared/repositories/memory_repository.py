from boto3.dynamodb.conditions import Key

from shared.config import settings
from shared.repositories.base import clean_for_dynamodb, now_iso, table


def chats_table():
    return table(settings.CHAT_TABLE)


def messages_table():
    return table(settings.MESSAGE_TABLE)


def memory_table():
    return table(settings.MEMORY_TABLE)


def get_chat_for_user(chat_id: str, user_id: str) -> dict | None:
    response = chats_table().get_item(Key={"chat_id": chat_id})
    item = response.get("Item")
    if not item or item.get("user_id") != user_id:
        return None
    return item


def update_chat_memory_summary(chat_id: str, memory_summary: str) -> None:
    chats_table().update_item(
        Key={"chat_id": chat_id},
        UpdateExpression="SET #memory_summary = :memory_summary, #updated_at = :updated_at",
        ExpressionAttributeNames={"#memory_summary": "memory_summary", "#updated_at": "updated_at"},
        ExpressionAttributeValues={":memory_summary": memory_summary, ":updated_at": now_iso()},
    )


def list_recent_messages(chat_id: str, limit: int = 20) -> list[dict]:
    response = messages_table().query(
        KeyConditionExpression=Key("chat_id").eq(chat_id),
        ScanIndexForward=False,
        Limit=limit,
    )
    return list(reversed(response.get("Items", [])))


def put_memory(item: dict) -> None:
    memory_table().put_item(Item=clean_for_dynamodb(item))


def list_memories(chat_id: str, limit: int = 50) -> list[dict]:
    response = memory_table().query(
        IndexName="chat_id-created_at-index",
        KeyConditionExpression=Key("chat_id").eq(chat_id),
        ScanIndexForward=False,
        Limit=limit,
    )
    return response.get("Items", [])
