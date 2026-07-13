from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.auth.schemas import LoginRequest, TokenResponse, UserResponse
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service() -> AuthService:
    return AuthService()


@router.post("/login", response_model=TokenResponse, summary="Authenticate a user")
async def login(request: LoginRequest, service: Annotated[AuthService, Depends(get_auth_service)]) -> TokenResponse:
    return await service.login(request)


@router.get("/me", response_model=UserResponse, summary="Fetch the current user")
async def get_current_user(service: Annotated[AuthService, Depends(get_auth_service)]) -> UserResponse:
    return await service.get_current_user("token")
