from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    indexed = "indexed"
    failed = "failed"


class DocumentUploadRequest(BaseModel):
    tenant_id: str
    title: str = Field(min_length=1, max_length=255)
    content_type: str
    size_bytes: int | None = None
    checksum: str | None = None


class DocumentResponse(BaseModel):
    id: str
    tenant_id: str
    title: str
    status: DocumentStatus
    content_type: str
    checksum: str | None = None
    storage_path: str | None = None
    extracted_text: str | None = None
    confidence_score: float | None = None
    pages: int | None = None
    error: str | None = None


class DocumentParseResponse(BaseModel):
    document_id: str
    tenant_id: str
    title: str
    parsed_content: dict[str, object] | None = None
