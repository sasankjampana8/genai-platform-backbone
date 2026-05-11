import json
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError
from pydantic import ValidationError as PydanticValidationError

from shared.api_response import error_response, success_response
from shared.config import settings
from shared.logger import get_logger
from shared.request_context import get_request_id, parse_json_body
from shared.schemas import ConfirmRequest, LoginRequest, LogoutRequest, RefreshRequest, SignupRequest

logger = get_logger(__name__)

_cognito_client = None
_dynamodb_resource = None


def lambda_handler(event, context):
    request_id = get_request_id(event)
    route_key = event.get("routeKey", "")

    try:
        payload = parse_json_body(event)

        if route_key == "POST /v1/auth/signup":
            data = signup(SignupRequest.model_validate(payload))
        elif route_key == "POST /v1/auth/confirm":
            data = confirm(ConfirmRequest.model_validate(payload))
        elif route_key == "POST /v1/auth/login":
            data = login(LoginRequest.model_validate(payload))
        elif route_key == "POST /v1/auth/refresh":
            data = refresh(RefreshRequest.model_validate(payload))
        elif route_key == "POST /v1/auth/logout":
            data = logout(LogoutRequest.model_validate(payload))
        else:
            return error_response(
                request_id=request_id,
                code="NOT_FOUND",
                message="Auth route not found.",
                status_code=404,
            )

        return success_response(data, request_id=request_id)
    except PydanticValidationError as exc:
        return error_response(
            request_id=request_id,
            code="VALIDATION_ERROR",
            message="Invalid request payload.",
            details={"errors": exc.errors()},
            status_code=422,
        )
    except ValueError as exc:
        return error_response(
            request_id=request_id,
            code="BAD_REQUEST",
            message=str(exc),
            status_code=400,
        )
    except ClientError as exc:
        logger.warning("auth provider error | request_id=%s | error=%s", request_id, exc)
        code = exc.response.get("Error", {}).get("Code", "AUTH_PROVIDER_ERROR")
        return error_response(
            request_id=request_id,
            code=code,
            message=client_error_message(code),
            status_code=auth_status_code(code),
        )
    except Exception:
        logger.exception("auth handler failed | request_id=%s", request_id)
        return error_response(
            request_id=request_id,
            code="INTERNAL_SERVER_ERROR",
            message="Internal server error.",
            status_code=500,
        )


def signup(request: SignupRequest) -> dict[str, Any]:
    require_cognito_config()
    response = cognito().sign_up(
        ClientId=settings.COGNITO_CLIENT_ID,
        Username=request.email,
        Password=request.password,
        UserAttributes=[
            {"Name": "email", "Value": request.email},
            {"Name": "name", "Value": request.name},
        ],
    )
    user_id = response.get("UserSub") or request.email
    upsert_user(
        {
            "user_id": user_id,
            "email": request.email,
            "name": request.name,
            "status": "confirmation_required",
        }
    )
    return {
        "user_id": user_id,
        "email": request.email,
        "status": "CONFIRMATION_REQUIRED",
    }


def confirm(request: ConfirmRequest) -> dict[str, str]:
    require_cognito_config()
    cognito().confirm_sign_up(
        ClientId=settings.COGNITO_CLIENT_ID,
        Username=request.email,
        ConfirmationCode=request.confirmation_code,
    )
    user_id = get_cognito_user_sub(request.email)
    if user_id:
        upsert_user(
            {
                "user_id": user_id,
                "email": request.email,
                "status": "active",
            }
        )
    return {
        "email": request.email,
        "status": "CONFIRMED",
    }


def login(request: LoginRequest) -> dict[str, Any]:
    require_cognito_config()
    response = cognito().initiate_auth(
        ClientId=settings.COGNITO_CLIENT_ID,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": request.email,
            "PASSWORD": request.password,
        },
    )
    user_id = get_cognito_user_sub(request.email)
    if user_id:
        upsert_user(
            {
                "user_id": user_id,
                "email": request.email,
                "status": "active",
            }
        )
    return auth_result(response)


def refresh(request: RefreshRequest) -> dict[str, Any]:
    require_cognito_config()
    response = cognito().initiate_auth(
        ClientId=settings.COGNITO_CLIENT_ID,
        AuthFlow="REFRESH_TOKEN_AUTH",
        AuthParameters={
            "REFRESH_TOKEN": request.refresh_token,
        },
    )
    return auth_result(response, include_refresh_token=False)


def logout(request: LogoutRequest) -> dict[str, str]:
    cognito().global_sign_out(AccessToken=request.access_token)
    return {"status": "LOGGED_OUT"}


def auth_result(response: dict[str, Any], include_refresh_token: bool = True) -> dict[str, Any]:
    result = response.get("AuthenticationResult") or {}
    data = {
        "access_token": result.get("AccessToken"),
        "id_token": result.get("IdToken"),
        "token_type": result.get("TokenType", "Bearer"),
        "expires_in": result.get("ExpiresIn", 900),
    }
    if include_refresh_token:
        data["refresh_token"] = result.get("RefreshToken")
    return data


def upsert_user(item: dict[str, Any]) -> None:
    if not settings.USER_TABLE:
        return
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    users_table().put_item(
        Item={
            **item,
            "created_at": now,
            "updated_at": now,
        }
    )


def get_cognito_user_sub(email: str) -> str | None:
    if not settings.COGNITO_USER_POOL_ID:
        return None
    response = cognito().admin_get_user(
        UserPoolId=settings.COGNITO_USER_POOL_ID,
        Username=email,
    )
    for attribute in response.get("UserAttributes", []):
        if attribute.get("Name") == "sub":
            return attribute.get("Value")
    return None


def require_cognito_config() -> None:
    if not settings.COGNITO_CLIENT_ID:
        raise ValueError("COGNITO_CLIENT_ID is not configured")


def cognito():
    global _cognito_client
    if _cognito_client is None:
        _cognito_client = boto3.client("cognito-idp", region_name=settings.AWS_REGION)
    return _cognito_client


def users_table():
    global _dynamodb_resource
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    return _dynamodb_resource.Table(settings.USER_TABLE)


def client_error_message(code: str) -> str:
    messages = {
        "CodeMismatchException": "Invalid confirmation code.",
        "ExpiredCodeException": "Confirmation code has expired.",
        "InvalidPasswordException": "Password does not meet policy requirements.",
        "NotAuthorizedException": "Invalid credentials or token.",
        "UserNotConfirmedException": "User is not confirmed.",
        "UserNotFoundException": "User not found.",
        "UsernameExistsException": "User already exists.",
    }
    return messages.get(code, "Authentication request failed.")


def auth_status_code(code: str) -> int:
    if code in {"CodeMismatchException", "ExpiredCodeException", "InvalidPasswordException"}:
        return 400
    if code in {"NotAuthorizedException", "UserNotConfirmedException"}:
        return 401
    if code == "UserNotFoundException":
        return 404
    if code == "UsernameExistsException":
        return 409
    return 400
