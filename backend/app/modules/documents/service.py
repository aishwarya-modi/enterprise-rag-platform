import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.schemas import DocumentResponse, DocumentStatus, DocumentUploadRequest
from app.modules.documents.tasks import submit_document_processing


class StorageAdapter(Protocol):
    def save(self, file_name: str, content: bytes) -> str: ...


class LocalStorageAdapter:
    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = Path(base_dir or get_settings().storage_path)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file_name: str, content: bytes) -> str:
        destination = self.base_dir / file_name
        destination.write_bytes(content)
        return str(destination)


class DocumentService:
    def __init__(self, repository: DocumentRepository | None = None, storage: StorageAdapter | None = None) -> None:
        self._repository = repository or DocumentRepository()
        self._storage = storage or LocalStorageAdapter()
        self._settings = get_settings()

    @staticmethod
    def _allowed_content_types() -> set[str]:
        return {"pdf", "docx", "pptx", "txt", "markdown", "csv"}

    @staticmethod
    def _compute_checksum(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def _validate_content_type(self, content_type: str) -> None:
        if content_type not in self._allowed_content_types():
            raise ValueError("Unsupported content type")

    def _validate_file_size(self, size_bytes: int | None) -> None:
        max_size = self._settings.max_upload_size_mb * 1024 * 1024
        if size_bytes is not None and size_bytes > max_size:
            raise ValueError("File exceeds maximum size")

    def _prepare_file_name(self, original_name: str, checksum: str) -> str:
        suffix = Path(original_name).suffix.lower() or ".bin"
        return f"{checksum}{suffix}"

    async def _run_virus_scan(self, content: bytes) -> None:
        if self._settings.virus_scan_enabled:
            return

    async def _process_document(self, document_id: str, content: bytes, request: DocumentUploadRequest) -> None:
        await self._run_virus_scan(content)
        document = await self._repository.get_by_id(document_id)
        if document is None:
            return
        document["status"] = DocumentStatus.indexed.value
        document["processed_at"] = datetime.now(UTC).isoformat()

    async def upload_document(self, request: DocumentUploadRequest, content: bytes, file_name: str) -> DocumentResponse:
        try:
            self._validate_content_type(request.content_type)
            self._validate_file_size(request.size_bytes)
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc

        checksum = request.checksum or self._compute_checksum(content)
        existing = await self._repository.get_by_checksum(checksum)
        if existing is not None:
            return DocumentResponse(
                id=str(existing["id"]),
                tenant_id=str(existing["tenant_id"]),
                title=str(existing["title"]),
                status=DocumentStatus.indexed,
                content_type=str(existing["content_type"]),
                checksum=checksum,
                storage_path=str(existing.get("storage_path") or ""),
            )

        storage_path = self._storage.save(self._prepare_file_name(file_name, checksum), content)
        document_id = await self._repository.save(
            request.tenant_id,
            request.title,
            request.content_type,
            checksum,
            storage_path,
            DocumentStatus.processing.value,
        )
        submit_document_processing(document_id, checksum, storage_path)
        return DocumentResponse(
            id=document_id,
            tenant_id=request.tenant_id,
            title=request.title,
            status=DocumentStatus.processing,
            content_type=request.content_type,
            checksum=checksum,
            storage_path=storage_path,
        )
