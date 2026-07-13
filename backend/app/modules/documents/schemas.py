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
    content_type: Literal["pdf", "docx", "pptx", "txt", "markdown", "csv", "png", "jpeg"]


class DocumentResponse(BaseModel):
    id: str
    tenant_id: str
    title: str
    status: DocumentStatus
    content_type: str
