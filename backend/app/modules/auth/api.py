from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.modules.auth.schemas import (
    GoogleAuthRequest,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service() -> AuthService:
    return AuthService()


def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return authorization.split(" ", 1)[1].strip()


@router.post("/login", response_model=TokenResponse, summary="Authenticate a user")
async def login(
    request: LoginRequest,
    http_request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    client_ip = http_request.headers.get("x-forwarded-for") or http_request.client.host if http_request.client else None
    return await service.login(request, request_ip=client_ip)


@router.post("/refresh", response_model=TokenResponse, summary="Refresh an access token")
async def refresh(
    request: RefreshTokenRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    return await service.refresh(request)


@router.post("/logout", summary="Revoke a refresh token")
async def logout(
    request: LogoutRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict[str, str]:
    return await service.logout(request)


@router.post("/google", response_model=TokenResponse, summary="Authenticate with Google OAuth")
async def google_auth(
    request: GoogleAuthRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    return await service.google_auth(request)


@router.get("/me", response_model=UserResponse, summary="Fetch the current user")
async def get_current_user(
    token: Annotated[str, Depends(get_bearer_token)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    return await service.get_current_user(token)


@router.get("/admin", response_model=UserResponse, summary="Administrator-only access")
async def admin_only(
    token: Annotated[str, Depends(get_bearer_token)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    return await service.require_role(token, {"admin"})
