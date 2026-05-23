from app.core.security import AuthContext
from app.repositories.memory import store
from app.schemas.profile import ProfileCreateRequest, ProfileResponse


class ProfileService:
    def create(self, auth: AuthContext, request: ProfileCreateRequest) -> ProfileResponse:
        store.users[auth.user_id] = {
            "user_id": auth.user_id,
            "cognito_sub": auth.cognito_sub,
            "email": request.email or auth.email,
            "display_name": request.display_name,
            "status": "active",
        }
        return self.get(auth)

    def get(self, auth: AuthContext) -> ProfileResponse:
        user = store.users.get(auth.user_id) or {
            "user_id": auth.user_id,
            "cognito_sub": auth.cognito_sub,
            "email": auth.email,
            "display_name": auth.email or auth.cognito_sub,
            "status": "active",
        }
        return ProfileResponse(**user)

