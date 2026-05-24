from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.responses import success_payload
from app.core.security import AuthContext, get_auth_context
from app.schemas.prompts import PromptCreateRequest, PromptVersionCreateRequest
from app.services.prompt_service import PromptService

router = APIRouter()
service = PromptService()


@router.post("")
def create_prompt(request: PromptCreateRequest, auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload(service.create(auth.user_id, request))


@router.post("/{prompt_id}/versions")
def create_prompt_version(
    prompt_id: UUID,
    request: PromptVersionCreateRequest,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    return success_payload(service.create_version(auth.user_id, prompt_id, request))


@router.get("")
def list_prompts(auth: AuthContext = Depends(get_auth_context)) -> dict:
    return success_payload({"prompts": service.list(auth.user_id)})

