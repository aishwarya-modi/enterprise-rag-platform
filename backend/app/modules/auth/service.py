from typing import Protocol

from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import LoginRequest, TokenResponse, UserResponse


class AuthServiceProtocol(Protocol):
    async def login(self, request: LoginRequest) -> TokenResponse: ...

    async def get_current_user(self, token: str) -> UserResponse: ...


class AuthService:
    def __init__(self, repository: AuthRepository | None = None) -> None:
        self._repository = repository or AuthRepository()

    async def login(self, request: LoginRequest) -> TokenResponse:
        user = await self._repository.get_user_by_email(request.email)
        if user is None:
            raise ValueError("Invalid credentials")
        return TokenResponse(access_token="mock-token")

    async def get_current_user(self, token: str) -> UserResponse:
        return UserResponse(id="user-1", email="admin@example.com", tenant_id="tenant-1", role="admin")
