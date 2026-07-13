from pydantic import BaseModel, Field


class TenantCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    slug: str = Field(min_length=3, max_length=100)


class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
