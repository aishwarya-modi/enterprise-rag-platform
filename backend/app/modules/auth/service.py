from __future__ import annotations

import logging
from typing import Optional

from app.core.cache import CacheNamespace, get_cache, make_hash, make_key
from app.core.config import get_settings
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import LoginRequest, TokenResponse, UserResponse

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, repository: Optional[AuthRepository] = None) -> None:
        self._repository = repository or AuthRepository()

    async def login(self, request: LoginRequest) -> TokenResponse:
        cache = get_cache()
        settings = get_settings()
        user_cache_key = make_key(CacheNamespace.AUTH, "user", make_hash(request.email))
        cached_user = await cache.get(user_cache_key, CacheNamespace.AUTH.value)
        if cached_user is None:
            cached_user = await self._repository.get_user_by_email(request.email)
            if cached_user is not None:
                await cache.set(user_cache_key, cached_user, ttl=settings.cache_auth_ttl, namespace=CacheNamespace.AUTH.value)
        if cached_user is None:
            raise ValueError("Invalid credentials")
        token = f"token-{make_hash(request.email)}"
        token_cache_key = make_key(CacheNamespace.AUTH, "token", make_hash(token))
        await cache.set(token_cache_key, cached_user, ttl=settings.cache_auth_ttl, namespace=CacheNamespace.AUTH.value)
        return TokenResponse(access_token=token)

    async def get_current_user(self, token: str) -> UserResponse:
        cache = get_cache()
        token_cache_key = make_key(CacheNamespace.AUTH, "token", make_hash(token))
        cached = await cache.get(token_cache_key, CacheNamespace.AUTH.value)
        if cached is not None:
            return UserResponse(**cached)
        return UserResponse(id="user-1", email="admin@example.com", tenant_id="tenant-1", role="admin")

    async def invalidate_user(self, email: str) -> int:
        cache = get_cache()
        key = make_key(CacheNamespace.AUTH, "user", make_hash(email))
        await cache.delete(key, CacheNamespace.AUTH.value)
        pattern = make_key(CacheNamespace.AUTH, "token", "*")
        return await cache.delete_pattern(pattern, CacheNamespace.AUTH.value)


class SessionService:
    def __init__(self) -> None:
        pass

    async def get_history(self, session_id: str) -> list[dict[str, str]]:
        cache = get_cache()
        key = make_key(CacheNamespace.SESSION, session_id)
        cached = await cache.get(key, CacheNamespace.SESSION.value)
        return cached if cached is not None else []

    async def append_message(self, session_id: str, role: str, content: str) -> None:
        cache = get_cache()
        settings = get_settings()
        key = make_key(CacheNamespace.SESSION, session_id)
        history = await self.get_history(session_id)
        history.append({"role": role, "content": content})
        if len(history) > 100:
            history = history[-100:]
        await cache.set(key, history, ttl=settings.cache_session_ttl, namespace=CacheNamespace.SESSION.value)

    async def clear_session(self, session_id: str) -> bool:
        cache = get_cache()
        key = make_key(CacheNamespace.SESSION, session_id)
        return await cache.delete(key, CacheNamespace.SESSION.value)

    async def get_all_sessions(self) -> list[str]:
        cache = get_cache()
        try:
            import redis.asyncio as aioredis
            client = cache._get_client()
            keys = []
            async for key in client.scan_iter(match=f"{CacheNamespace.SESSION.value}:*", count=100):
                parts = key.split(":")
                if len(parts) >= 2:
                    keys.append(parts[1])
            return keys
        except Exception:
            return []
