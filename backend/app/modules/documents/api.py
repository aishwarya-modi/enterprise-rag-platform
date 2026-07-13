from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.modules.documents.schemas import DocumentResponse, DocumentUploadRequest
from app.modules.documents.service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service() -> DocumentService:
    return DocumentService()


@router.post("", response_model=DocumentResponse, summary="Upload a document")
async def upload_document(
    file: UploadFile = File(...),
    tenant_id: str = "tenant-1",
    service: Annotated[DocumentService, Depends(get_document_service)] = None,
) -> DocumentResponse:
    request = DocumentUploadRequest(
        tenant_id=tenant_id,
        title=file.filename or "uploaded-document",
        content_type="pdf",
    )
    return await service.upload_document(request)
