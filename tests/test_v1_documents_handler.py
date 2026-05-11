import json
from types import SimpleNamespace

from lambdas.v1_documents_handler import handler


def event(route_key, body=None, path=None):
    return {
        "routeKey": route_key,
        "body": json.dumps(body or {}),
        "pathParameters": path or {},
        "requestContext": {
            "requestId": "abc123",
            "authorizer": {"jwt": {"claims": {"sub": "user_123", "email": "test@example.com"}}},
        },
    }


def test_v1_upload_url_uses_authenticated_user(monkeypatch):
    stored = []
    monkeypatch.setattr(
        handler,
        "settings",
        SimpleNamespace(RAW_BUCKET="bucket", MAX_FILES=10, MAX_FILE_SIZE_BYTES=10_485_760),
    )
    monkeypatch.setattr(handler, "put_document", lambda item: stored.append(item))
    monkeypatch.setattr(handler, "create_presigned_post", lambda key, content_type: {"url": "https://s3", "fields": {"key": key}})

    response = handler.lambda_handler(
        event(
            "POST /v1/documents/upload-url",
            {
                "files": [
                    {
                        "file_name": "sample.pdf",
                        "content_type": "application/pdf",
                        "file_size_bytes": 100,
                    }
                ]
            },
        ),
        None,
    )
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["status"] == "success"
    assert stored[0]["user_id"] == "user_123"
    assert stored[0]["s3_key"].startswith("raw/user_123/doc_")


def test_v1_upload_rejects_user_id_in_body():
    response = handler.lambda_handler(
        event(
            "POST /v1/documents/upload-url",
            {
                "user_id": "attacker",
                "files": [
                    {
                        "file_name": "sample.pdf",
                        "content_type": "application/pdf",
                        "file_size_bytes": 100,
                    }
                ],
            },
        ),
        None,
    )
    body = json.loads(response["body"])

    assert response["statusCode"] == 422
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_v1_list_documents(monkeypatch):
    monkeypatch.setattr(
        handler,
        "list_documents_for_user",
        lambda user_id: [
            {
                "document_id": "doc_1",
                "file_name": "sample.pdf",
                "file_size_bytes": 100,
                "upload_status": "UPLOADED",
                "processing_status": "COMPLETED",
                "chunk_count": 2,
            }
        ],
    )

    response = handler.lambda_handler(event("GET /v1/documents"), None)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["data"]["documents"][0]["document_id"] == "doc_1"


def test_v1_process_status_not_found(monkeypatch):
    monkeypatch.setattr(handler, "get_document_for_user", lambda document_id, user_id: {"document_id": document_id, "user_id": user_id, "file_name": "sample.pdf"})
    monkeypatch.setattr(handler, "get_process_job_for_user", lambda process_id, document_id, user_id: None)

    response = handler.lambda_handler(
        event(
            "GET /v1/documents/{document_id}/processes/{process_id}",
            path={"document_id": "doc_1", "process_id": "proc_1"},
        ),
        None,
    )
    body = json.loads(response["body"])

    assert response["statusCode"] == 404
    assert body["error"]["code"] == "NOT_FOUND"
