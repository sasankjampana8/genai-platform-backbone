import json

from lambdas.chat_handler import handler


def _event(route_key: str, body=None, path_params=None):
    return {
        "routeKey": route_key,
        "body": json.dumps(body or {}),
        "pathParameters": path_params or {},
        "requestContext": {
            "requestId": "abc",
            "authorizer": {"jwt": {"claims": {"sub": "user_123", "email": "u@example.com"}}},
        },
    }


def test_create_chat(monkeypatch):
    stored = {}
    monkeypatch.setattr(handler.chat_repository, "put_chat", lambda item: stored.update(item))

    response = handler.lambda_handler(_event("POST /v1/chats", {"title": "Docs"}), None)
    body = json.loads(response["body"])

    assert response["statusCode"] == 201
    assert body["data"]["title"] == "Docs"
    assert stored["user_id"] == "user_123"


def test_send_message_enqueues_runtime(monkeypatch):
    messages = []
    runs = []
    queued = []
    monkeypatch.setattr(handler.chat_repository, "get_chat_for_user", lambda chat_id, user_id: {"chat_id": chat_id, "user_id": user_id})
    monkeypatch.setattr(handler.chat_repository, "put_message", lambda item: messages.append(item))
    monkeypatch.setattr(handler.chat_repository, "update_chat_after_message", lambda *args, **kwargs: None)
    monkeypatch.setattr(handler.run_repository, "put_run", lambda item: runs.append(item))
    monkeypatch.setattr(handler, "send_runtime_message", lambda item: queued.append(item))

    response = handler.lambda_handler(
        _event(
            "POST /v1/chats/{chat_id}/messages",
            {"input": "Summarize this", "document_ids": ["doc_1"]},
            {"chat_id": "chat_1"},
        ),
        None,
    )
    body = json.loads(response["body"])

    assert response["statusCode"] == 202
    assert body["data"]["status"] == "QUEUED"
    assert messages[0]["role"] == "USER"
    assert runs[0]["status"] == "QUEUED"
    assert queued[0]["document_ids"] == ["doc_1"]
