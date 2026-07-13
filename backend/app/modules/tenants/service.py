from app.modules.tenants.schemas import TenantCreateRequest, TenantResponse


class TenantService:
    async def create_tenant(self, request: TenantCreateRequest) -> TenantResponse:
        return TenantResponse(id="tenant-1", name=request.name, slug=request.slug)
