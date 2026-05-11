import json

from shared.api_response import error_response, success_response


def test_success_response_uses_global_shape():
    response = success_response({"ok": True}, request_id="req_test")
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["request_id"] == "req_test"
    assert body["status"] == "success"
    assert body["data"] == {"ok": True}
    assert body["metadata"]["api_version"] == "v1"
    assert "timestamp" in body["metadata"]


def test_error_response_uses_global_shape():
    response = error_response(
        request_id="req_test",
        code="VALIDATION_ERROR",
        message="Invalid request payload.",
        details={"field": "query"},
        status_code=422,
    )
    body = json.loads(response["body"])

    assert response["statusCode"] == 422
    assert body["status"] == "error"
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"] == {"field": "query"}
