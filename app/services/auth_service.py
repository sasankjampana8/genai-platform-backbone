from app.core.config import settings
from app.providers.cognito import CognitoProvider
from app.repositories.memory import store
from app.repositories.sql import repository, user_id_from_cognito_sub
from app.schemas.auth import ConfirmRequest, LoginRequest, LoginResponse, RegisterRequest, RegisterResponse


class AuthService:
    def __init__(self) -> None:
        self.cognito = None if settings.mock_mode else CognitoProvider()

    def register(self, request: RegisterRequest) -> RegisterResponse:
        if settings.mock_mode:
            user_id = user_id_from_cognito_sub(request.email)
            store.users[user_id] = {
                "user_id": user_id,
                "email": request.email,
                "name": request.name,
                "status": "active",
            }
            return RegisterResponse(user_id=user_id, email=request.email, status="active")

        assert self.cognito is not None
        response = self.cognito.sign_up(request.email, request.password, request.name)
        cognito_sub = response.get("UserSub", request.email)
        user = repository.ensure_user(
            cognito_sub=cognito_sub,
            email=request.email,
            display_name=request.name,
            status="confirmation_required",
        )
        return RegisterResponse(user_id=user["user_id"], email=request.email, status="confirmation_required")

    def confirm(self, request: ConfirmRequest) -> dict:
        if settings.mock_mode:
            return {"email": request.email, "status": "confirmed"}
        assert self.cognito is not None
        self.cognito.confirm_sign_up(request.email, request.confirmation_code)
        return {"email": request.email, "status": "confirmed"}

    def login(self, request: LoginRequest) -> LoginResponse:
        if settings.mock_mode:
            return LoginResponse(
                access_token="mock-access-token",
                id_token="mock-id-token",
                refresh_token="mock-refresh-token",
                expires_in=900,
            )
        assert self.cognito is not None
        tokens = self.cognito.login(request.email, request.password)
        return LoginResponse(
            access_token=tokens.access_token,
            id_token=tokens.id_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in,
        )

    def refresh(self, refresh_token: str) -> LoginResponse:
        if settings.mock_mode:
            return LoginResponse(access_token="mock-refreshed-access-token", expires_in=900)
        assert self.cognito is not None
        tokens = self.cognito.refresh(refresh_token)
        return LoginResponse(
            access_token=tokens.access_token,
            id_token=tokens.id_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in,
        )

    def logout(self, access_token: str) -> dict:
        if not settings.mock_mode:
            assert self.cognito is not None
            self.cognito.logout(access_token)
        return {"status": "logged_out"}
