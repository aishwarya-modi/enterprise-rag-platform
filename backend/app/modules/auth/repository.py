from typing import Protocol
from uuid import uuid4

from app.core.security import hash_password


class AuthRepositoryProtocol(Protocol):
    async def get_user_by_email(self, email: str) -> dict[str, object] | None: ...


class AuthRepository:
    _instance: "AuthRepository | None" = None

    def __new__(cls) -> "AuthRepository":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._users: dict[str, dict[str, object]] = {}
        self._refresh_tokens: dict[str, str] = {}
        self._seed_admin_user()
        self._initialized = True

    def _seed_admin_user(self) -> None:
        if not self._users:
            self._users["user-1"] = {
                "id": "user-1",
                "email": "admin@example.com",
                "tenant_id": "tenant-1",
                "organization_id": "org-1",
                "role": "admin",
                "hashed_password": hash_password("Password123!"),
                "is_active": True,
            }

    async def get_user_by_email(self, email: str) -> dict[str, object] | None:
        normalized_email = email.lower()
        for user in self._users.values():
            if str(user["email"]).lower() == normalized_email:
                return user
        return None

    async def get_user_by_id(self, user_id: str) -> dict[str, object] | None:
        return self._users.get(user_id)

    async def create_or_update_user(
        self,
        *,
        email: str,
        tenant_id: str,
        organization_id: str | None,
        role: str,
        hashed_password: str | None = None,
        oauth_provider: str | None = None,
    ) -> dict[str, object]:
        existing = await self.get_user_by_email(email)
        if existing is not None:
            existing["tenant_id"] = tenant_id
            existing["organization_id"] = organization_id
            existing["role"] = role
            existing["hashed_password"] = hashed_password or existing.get("hashed_password")
            existing["oauth_provider"] = oauth_provider or existing.get("oauth_provider")
            existing["is_active"] = True
            return existing

        user_id = str(uuid4())
        user = {
            "id": user_id,
            "email": email.lower(),
            "tenant_id": tenant_id,
            "organization_id": organization_id,
            "role": role,
            "hashed_password": hashed_password,
            "oauth_provider": oauth_provider,
            "is_active": True,
        }
        self._users[user_id] = user
        return user

    async def store_refresh_token(self, user_id: str, refresh_token: str) -> None:
        self._refresh_tokens[refresh_token] = user_id

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        self._refresh_tokens.pop(refresh_token, None)

    async def is_refresh_token_active(self, user_id: str, refresh_token: str) -> bool:
        return self._refresh_tokens.get(refresh_token) == user_id


def get_auth_repository() -> AuthRepository:
    return AuthRepository()
