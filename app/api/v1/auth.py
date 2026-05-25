from fastapi import APIRouter

from app.core.responses import success_payload
from app.schemas.auth import ConfirmRequest, LoginRequest, RefreshRequest, RegisterRequest, LogoutRequest
from app.services.auth_service import AuthService

router = APIRouter()
service = AuthService()


@router.post("/register")
def register(request: RegisterRequest) -> dict:
    return success_payload(service.register(request))


@router.post("/confirm")
def confirm(request: ConfirmRequest) -> dict:
    return success_payload(service.confirm(request))


@router.post("/login")
def login(request: LoginRequest) -> dict:
    return success_payload(service.login(request))


@router.post("/refresh")
def refresh(request: RefreshRequest) -> dict:
    return success_payload(service.refresh(request.refresh_token))


@router.post("/logout")
def logout(request: LogoutRequest) -> dict:
    return success_payload(service.logout(request.access_token))
