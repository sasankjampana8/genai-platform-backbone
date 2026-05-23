from uuid import UUID, uuid4

from app.repositories.memory import store
from app.schemas.prompts import PromptCreateRequest, PromptResponse, PromptVersionCreateRequest


class PromptService:
    def create(self, user_id: UUID, request: PromptCreateRequest) -> PromptResponse:
        prompt = PromptResponse(prompt_id=uuid4(), name=request.name, description=request.description)
        store.prompts[prompt.prompt_id] = {**prompt.model_dump(), "user_id": user_id, "versions": []}
        return prompt

    def create_version(self, user_id: UUID, prompt_id: UUID, request: PromptVersionCreateRequest) -> dict:
        prompt = store.prompts[prompt_id]
        version = {"version_id": str(uuid4()), "template": request.template, "variables": request.variables}
        prompt["versions"].append(version)
        return version

    def list(self, user_id: UUID) -> list[PromptResponse]:
        return [PromptResponse(**item) for item in store.prompts.values() if item["user_id"] == user_id]

