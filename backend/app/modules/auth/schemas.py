from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    tenant_id: str | None = Field(default=None, max_length=36)
    organization_id: str | None = Field(default=None, max_length=36)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class GoogleAuthRequest(BaseModel):
    id_token: str
    email: EmailStr
    tenant_id: str | None = Field(default=None, max_length=36)
    organization_id: str | None = Field(default=None, max_length=36)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    tenant_id: str
    organization_id: str | None = None
    role: str
