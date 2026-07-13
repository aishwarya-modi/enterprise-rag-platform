from typing import Protocol


class DocumentRepositoryProtocol(Protocol):
    async def save(self, tenant_id: str, title: str, content_type: str) -> str: ...


class DocumentRepository:
    async def save(self, tenant_id: str, title: str, content_type: str) -> str:
        return "doc-1"
