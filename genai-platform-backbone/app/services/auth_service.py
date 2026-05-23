from uuid import uuid4

from app.core.config import settings
from app.repositories.memory import store
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse


class AuthService:
    def register(self, request: RegisterRequest) -> RegisterResponse:
        user_id = uuid4()
        store.users[user_id] = {
            "user_id": user_id,
            "email": request.email,
            "name": request.name,
            "status": "confirmation_required" if not settings.mock_mode else "active",
        }
        return RegisterResponse(user_id=user_id, email=request.email, status=store.users[user_id]["status"])

    def login(self, request: LoginRequest) -> LoginResponse:
        return LoginResponse(
            access_token="mock-access-token" if settings.mock_mode else "replace-with-cognito-token",
            id_token="mock-id-token" if settings.mock_mode else None,
            refresh_token="mock-refresh-token" if settings.mock_mode else None,
            expires_in=900,
        )

    def refresh(self, refresh_token: str) -> LoginResponse:
        return LoginResponse(access_token="mock-refreshed-access-token", expires_in=900)

    def logout(self, access_token: str) -> dict:
        return {"status": "logged_out"}

