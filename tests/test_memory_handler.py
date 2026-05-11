import json

from lambdas.memory_handler import handler


def event(route_key, body=None, path=None):
    return {
        "routeKey": route_key,
        "body": json.dumps(body or {}),
        "pathParameters": path or {"chat_id": "chat_123"},
        "requestContext": {
            "requestId": "abc123",
            "authorizer": {"jwt": {"claims": {"sub": "user_123", "email": "test@example.com"}}},
        },
    }


def test_get_memory_returns_chat_summary(monkeypatch):
    monkeypatch.setattr(handler, "get_chat_for_user", lambda chat_id, user_id: {"chat_id": chat_id, "user_id": user_id, "memory_summary": "hello"})
    monkeypatch.setattr(
        handler,
        "list_memories",
        lambda chat_id: [
            {
                "memory_id": "mem_1",
                "memory_type": "CONVERSATION_SUMMARY",
                "content": "hello",
                "importance": 0.5,
            }
        ],
    )

    response = handler.lambda_handler(event("GET /v1/chats/{chat_id}/memory"), None)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["data"]["memory_summary"] == "hello"
    assert body["data"]["memories"][0]["memory_id"] == "mem_1"


def test_summarize_memory_creates_memory(monkeypatch):
    saved = []
    updates = []
    monkeypatch.setattr(handler, "get_chat_for_user", lambda chat_id, user_id: {"chat_id": chat_id, "user_id": user_id})
    monkeypatch.setattr(
        handler,
        "list_recent_messages",
        lambda chat_id, limit: [
            {"message_id": "msg_1", "role": "USER", "content": "What is this document?"},
            {"message_id": "msg_2", "role": "ASSISTANT", "content": "It is a resume template."},
        ],
    )
    monkeypatch.setattr(handler, "put_memory", lambda item: saved.append(item))
    monkeypatch.setattr(handler, "update_chat_memory_summary", lambda chat_id, summary: updates.append((chat_id, summary)))

    response = handler.lambda_handler(event("POST /v1/chats/{chat_id}/memory/summarize", {"source_message_limit": 20}), None)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["data"]["status"] == "CREATED"
    assert saved[0]["source_message_ids"] == ["msg_1", "msg_2"]
    assert updates[0][0] == "chat_123"


def test_memory_requires_existing_chat(monkeypatch):
    monkeypatch.setattr(handler, "get_chat_for_user", lambda chat_id, user_id: None)

    response = handler.lambda_handler(event("GET /v1/chats/{chat_id}/memory"), None)
    body = json.loads(response["body"])

    assert response["statusCode"] == 404
    assert body["error"]["code"] == "NOT_FOUND"
