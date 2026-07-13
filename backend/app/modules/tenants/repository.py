from typing import Protocol


class TenantRepositoryProtocol(Protocol):
    async def save(self, name: str, slug: str) -> str: ...


class TenantRepository:
    async def save(self, name: str, slug: str) -> str:
        return "tenant-1"
