import pytest

from shared.request_context import (
    AuthError,
    build_request_context,
    get_claims_from_event,
    get_request_id,
    parse_json_body,
    require_user_id,
)


def test_get_claims_from_http_api_jwt_event():
    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user_123",
                        "email": "test@example.com",
                    }
                }
            }
        }
    }

    assert get_claims_from_event(event)["sub"] == "user_123"


def test_require_user_id_from_claims():
    event = {"requestContext": {"authorizer": {"jwt": {"claims": {"sub": "user_123"}}}}}

    assert require_user_id(event) == "user_123"


def test_require_user_id_raises_without_auth(monkeypatch):
    monkeypatch.delenv("AUTH_DISABLED", raising=False)

    with pytest.raises(AuthError):
        require_user_id({})


def test_require_user_id_allows_local_body_when_auth_disabled(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")

    assert require_user_id({}, {"user_id": "local_user"}) == "local_user"


def test_build_request_context_uses_request_id_and_email():
    event = {
        "requestContext": {
            "requestId": "abc123",
            "authorizer": {"jwt": {"claims": {"sub": "user_123", "email": "test@example.com"}}},
        }
    }

    context = build_request_context(event)

    assert context.request_id == "req_abc123"
    assert context.user_id == "user_123"
    assert context.email == "test@example.com"


def test_parse_json_body_rejects_invalid_json():
    with pytest.raises(ValueError):
        parse_json_body({"body": "{"})


def test_get_request_id_uses_header_when_gateway_id_missing():
    assert get_request_id({"headers": {"X-Request-Id": "req_custom"}}) == "req_custom"
