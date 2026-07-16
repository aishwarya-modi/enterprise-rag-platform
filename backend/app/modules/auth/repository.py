from __future__ import annotations

from typing import Protocol


class AuthRepositoryProtocol(Protocol):
    async def get_user_by_email(self, email: str) -> dict[str, str] | None: ...


class AuthRepository:
    async def get_user_by_email(self, email: str) -> dict[str, str] | None:
        if email == "admin@example.com":
            return {"id": "user-1", "email": email, "tenant_id": "tenant-1", "role": "admin"}
        return None
