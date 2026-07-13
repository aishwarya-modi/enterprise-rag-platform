from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.tenants.schemas import TenantCreateRequest, TenantResponse
from app.modules.tenants.service import TenantService

router = APIRouter(prefix="/tenants", tags=["tenants"])


def get_tenant_service() -> TenantService:
    return TenantService()


@router.post("", response_model=TenantResponse, summary="Create a tenant")
async def create_tenant(request: TenantCreateRequest, service: Annotated[TenantService, Depends(get_tenant_service)]) -> TenantResponse:
    return await service.create_tenant(request)
