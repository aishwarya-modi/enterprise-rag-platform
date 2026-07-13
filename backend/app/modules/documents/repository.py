from typing import Protocol
from uuid import uuid4


class DocumentRepositoryProtocol(Protocol):
    async def save(self, tenant_id: str, title: str, content_type: str, checksum: str, storage_path: str, status: str) -> str: ...


class DocumentRepository:
    _instance: "DocumentRepository | None" = None

    def __new__(cls) -> "DocumentRepository":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._documents: dict[str, dict[str, object]] = {}
        self._initialized = True

    async def save(
        self,
        tenant_id: str,
        title: str,
        content_type: str,
        checksum: str,
        storage_path: str,
        status: str,
    ) -> str:
        existing = await self.get_by_checksum(checksum)
        if existing is not None:
            return str(existing["id"])

        document_id = str(uuid4())
        self._documents[document_id] = {
            "id": document_id,
            "tenant_id": tenant_id,
            "title": title,
            "content_type": content_type,
            "checksum": checksum,
            "storage_path": storage_path,
            "status": status,
        }
        return document_id

    async def get_by_id(self, document_id: str) -> dict[str, object] | None:
        return self._documents.get(document_id)

    async def get_by_checksum(self, checksum: str) -> dict[str, object] | None:
        for document in self._documents.values():
            if str(document.get("checksum")) == checksum:
                return document
        return None
