from datetime import UTC, datetime, timedelta
from typing import Protocol

from fastapi import HTTPException, status
from redis import Redis
from redis.exceptions import ConnectionError

from app.core.config import get_settings
from app.core.security import create_token, decode_token, verify_password
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    GoogleAuthRequest,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
)


class AuthServiceProtocol(Protocol):
    async def login(self, request: LoginRequest, request_ip: str | None = None) -> TokenResponse: ...

    async def get_current_user(self, token: str) -> UserResponse: ...


class AuthService:
    def __init__(self, repository: AuthRepository | None = None) -> None:
        self._repository = repository or AuthRepository()
        self._settings = get_settings()
        self._rate_limit_store: dict[str, list[datetime]] = {}
        self._blacklisted_tokens: set[str] = set()
        self._redis_client: Redis | None = None

    def _get_redis_client(self) -> Redis | None:
        if self._redis_client is None:
            try:
                self._redis_client = Redis.from_url(self._settings.redis_url, decode_responses=True)
                self._redis_client.ping()
            except ConnectionError:
                self._redis_client = None
        return self._redis_client

    def _is_blacklisted_token(self, token: str) -> bool:
        client = self._get_redis_client()
        if client is not None:
            return bool(client.get(f"blacklist:{token}"))
        return token in self._blacklisted_tokens

    def _blacklist_token(self, token: str) -> None:
        client = self._get_redis_client()
        if client is not None:
            client.setex(f"blacklist:{token}", 60 * 60 * 24 * 7, "1")
        else:
            self._blacklisted_tokens.add(token)

    def _get_rate_limit_key(self, request_ip: str | None, email: str) -> str:
        return f"{request_ip or 'unknown'}:{email}"

    def _check_rate_limit(self, request_ip: str | None, email: str) -> None:
        now = datetime.now(UTC)
        key = self._get_rate_limit_key(request_ip, email)
        attempts = [ts for ts in self._rate_limit_store.get(key, []) if now - ts < timedelta(minutes=5)]
        if len(attempts) >= 5:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
        attempts.append(now)
        self._rate_limit_store[key] = attempts

    async def login(self, request: LoginRequest, request_ip: str | None = None) -> TokenResponse:
        self._check_rate_limit(request_ip, str(request.email))
        user = await self._repository.get_user_by_email(str(request.email))
        if user is None or not verify_password(request.password, str(user.get("hashed_password") or "")):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        tenant_id = request.tenant_id or str(user.get("tenant_id") or "default-tenant")
        organization_id = request.organization_id or str(user.get("organization_id") or "")
        await self._repository.create_or_update_user(
            email=str(request.email),
            tenant_id=tenant_id,
            organization_id=organization_id,
            role=str(user.get("role") or "viewer"),
            hashed_password=str(user.get("hashed_password") or ""),
        )

        access_token = create_token(
            str(user["id"]),
            token_type="access",
            tenant_id=tenant_id,
            organization_id=organization_id,
            role=str(user.get("role") or "viewer"),
        )
        refresh_token = create_token(
            str(user["id"]),
            token_type="refresh",
            tenant_id=tenant_id,
            organization_id=organization_id,
            role=str(user.get("role") or "viewer"),
            expires_delta=timedelta(days=7),
        )
        await self._repository.store_refresh_token(str(user["id"]), refresh_token)
        return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

    async def refresh(self, payload: RefreshTokenRequest) -> TokenResponse:
        if self._is_blacklisted_token(payload.refresh_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

        try:
            decoded = decode_token(payload.refresh_token)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

        if decoded.get("token_type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        user = await self._repository.get_user_by_id(str(decoded.get("sub")))
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        if not await self._repository.is_refresh_token_active(str(user["id"]), payload.refresh_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

        tenant_id = str(decoded.get("tenant_id") or user.get("tenant_id") or "default-tenant")
        organization_id = str(decoded.get("organization_id") or user.get("organization_id") or "")
        access_token = create_token(
            str(user["id"]),
            token_type="access",
            tenant_id=tenant_id,
            organization_id=organization_id,
            role=str(user.get("role") or "viewer"),
        )
        refresh_token = create_token(
            str(user["id"]),
            token_type="refresh",
            tenant_id=tenant_id,
            organization_id=organization_id,
            role=str(user.get("role") or "viewer"),
            expires_delta=timedelta(days=7),
        )
        await self._repository.revoke_refresh_token(payload.refresh_token)
        await self._repository.store_refresh_token(str(user["id"]), refresh_token)
        return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

    async def logout(self, payload: LogoutRequest) -> dict[str, str]:
        self._blacklist_token(payload.refresh_token)
        await self._repository.revoke_refresh_token(payload.refresh_token)
        return {"message": "Logged out successfully"}

    async def google_auth(self, request: GoogleAuthRequest) -> TokenResponse:
        user = await self._repository.create_or_update_user(
            email=str(request.email),
            tenant_id=request.tenant_id or "default-tenant",
            organization_id=request.organization_id,
            role="viewer",
            oauth_provider="google",
        )
        tenant_id = str(user.get("tenant_id") or "default-tenant")
        organization_id = str(user.get("organization_id") or "")
        access_token = create_token(
            str(user["id"]),
            token_type="access",
            tenant_id=tenant_id,
            organization_id=organization_id,
            role=str(user.get("role") or "viewer"),
        )
        refresh_token = create_token(
            str(user["id"]),
            token_type="refresh",
            tenant_id=tenant_id,
            organization_id=organization_id,
            role=str(user.get("role") or "viewer"),
            expires_delta=timedelta(days=7),
        )
        await self._repository.store_refresh_token(str(user["id"]), refresh_token)
        return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

    async def get_current_user(self, token: str) -> UserResponse:
        if self._is_blacklisted_token(token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
        try:
            decoded = decode_token(token)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

        if decoded.get("token_type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = await self._repository.get_user_by_id(str(decoded.get("sub")))
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        return UserResponse(
            id=str(user["id"]),
            email=str(user["email"]),
            tenant_id=str(user.get("tenant_id") or "default-tenant"),
            organization_id=str(user.get("organization_id") or "") or None,
            role=str(user.get("role") or "viewer"),
        )

    async def require_role(self, token: str, allowed_roles: set[str]) -> UserResponse:
        user = await self.get_current_user(token)
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
