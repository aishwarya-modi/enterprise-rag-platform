import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings
from app.modules.documents.ocr import OCRAdapter, TesseractOCRAdapter
from app.modules.documents.parser import parse_document_content
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
    def __init__(
        self,
        repository: DocumentRepository | None = None,
        storage: StorageAdapter | None = None,
        ocr_adapter: OCRAdapter | None = None,
    ) -> None:
        self._repository = repository or DocumentRepository()
        self._storage = storage or LocalStorageAdapter()
        self._ocr_adapter = ocr_adapter or TesseractOCRAdapter()
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

        extracted_text = ""
        confidence_score = 0.0
        pages = 1
        error = None
        try:
            if request.content_type in {"png", "jpeg", "pdf"}:
                extracted_text, confidence_score, pages = self._ocr_adapter.extract_text(str(document.get("storage_path")))
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
            extracted_text = ""
            confidence_score = 0.0
            pages = 1

        if not extracted_text:
            extracted_text = "OCR fallback: no text extracted"
            confidence_score = 0.0

        parsed_content = parse_document_content(
            request.content_type,
            content,
            metadata={
                "author": "unknown",
                "title": request.title,
                "language": "en",
            },
        )

        await self._repository.update(
            document_id,
            status=DocumentStatus.indexed.value,
            extracted_text=extracted_text,
            confidence_score=confidence_score,
            pages=pages,
            parsed_content=json.dumps(parsed_content),
            error=error,
            processed_at=datetime.now(UTC).isoformat(),
        )

    async def parse_document(self, document_id: str) -> dict[str, object]:
        document = await self._repository.get_by_id(document_id)
        if document is None:
            raise ValueError("Document not found")

        parsed_content: dict[str, object] | None = None
        raw_content = document.get("parsed_content")
        if isinstance(raw_content, str):
            try:
                parsed_content = json.loads(raw_content)
            except json.JSONDecodeError:
                parsed_content = None

        return {
            "document_id": str(document["id"]),
            "tenant_id": str(document["tenant_id"]),
            "title": str(document["title"]),
            "parsed_content": parsed_content or {},
        }

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
        submit_document_processing(document_id, checksum, storage_path, request.content_type)
        return DocumentResponse(
            id=document_id,
            tenant_id=request.tenant_id,
            title=request.title,
            status=DocumentStatus.processing,
            content_type=request.content_type,
            checksum=checksum,
            storage_path=storage_path,
        )
