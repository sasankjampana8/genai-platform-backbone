import json
from types import SimpleNamespace

from lambdas.auth_handler import handler


class FakeCognito:
    def initiate_auth(self, **kwargs):
        assert kwargs["ClientId"] == "client_123"
        assert kwargs["AuthFlow"] == "USER_PASSWORD_AUTH"
        return {
            "AuthenticationResult": {
                "AccessToken": "access",
                "IdToken": "id",
                "RefreshToken": "refresh",
                "TokenType": "Bearer",
                "ExpiresIn": 900,
            }
        }

    def admin_get_user(self, **kwargs):
        assert kwargs["UserPoolId"] == "pool_123"
        return {"UserAttributes": [{"Name": "sub", "Value": "user_sub_123"}]}


class FakeUsersTable:
    def __init__(self):
        self.items = []

    def put_item(self, **kwargs):
        self.items.append(kwargs["Item"])


def test_login_route_returns_token_payload(monkeypatch):
    monkeypatch.setattr(
        handler,
        "settings",
        SimpleNamespace(
            COGNITO_CLIENT_ID="client_123",
            COGNITO_USER_POOL_ID="pool_123",
            USER_TABLE="cloudrag_users",
            AWS_REGION="ap-south-1",
        ),
    )
    users_table = FakeUsersTable()
    monkeypatch.setattr(handler, "_cognito_client", FakeCognito())
    monkeypatch.setattr(handler, "users_table", lambda: users_table)

    response = handler.lambda_handler(
        {
            "routeKey": "POST /v1/auth/login",
            "body": json.dumps({"email": "test@example.com", "password": "TestPassword123!"}),
            "requestContext": {"requestId": "abc123"},
        },
        None,
    )
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["request_id"] == "req_abc123"
    assert body["status"] == "success"
    assert body["data"]["access_token"] == "access"
    assert body["data"]["refresh_token"] == "refresh"
    assert users_table.items[0]["user_id"] == "user_sub_123"


def test_auth_route_validation_error_does_not_call_cognito():
    response = handler.lambda_handler(
        {
            "routeKey": "POST /v1/auth/login",
            "body": json.dumps({"email": "not-an-email", "password": "TestPassword123!"}),
            "requestContext": {"requestId": "abc123"},
        },
        None,
    )
    body = json.loads(response["body"])

    assert response["statusCode"] == 422
    assert body["status"] == "error"
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_unknown_auth_route_returns_not_found():
    response = handler.lambda_handler(
        {
            "routeKey": "POST /v1/auth/unknown",
            "body": "{}",
            "requestContext": {"requestId": "abc123"},
        },
        None,
    )
    body = json.loads(response["body"])

    assert response["statusCode"] == 404
    assert body["error"]["code"] == "NOT_FOUND"
