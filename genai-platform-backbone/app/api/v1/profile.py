from fastapi import APIRouter, Depends

from app.core.responses import success_payload
from app.core.security import AuthContext, get_auth_context
from app.schemas.profile import ProfileCreateRequest
from app.services.profile_service import ProfileService

router = APIRouter()
service = ProfileService()


@router.post("")
def create_profile(request: ProfileCreateRequest, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.create(auth, request))


@router.get("")
def get_profile(auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.get(auth))

