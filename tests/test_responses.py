from app.core.responses import error_payload, success_payload


def test_success_payload_shape() -> None:
    payload = success_payload({"ok": True}, request_id="req-test")
    assert payload["request_id"] == "req-test"
    assert payload["status"] == "success"
    assert payload["data"] == {"ok": True}
    assert payload["metadata"]["api_version"] == "v1"


def test_error_payload_shape() -> None:
    payload = error_payload("VALIDATION_ERROR", "Bad input", request_id="req-test")
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["message"] == "Bad input"

