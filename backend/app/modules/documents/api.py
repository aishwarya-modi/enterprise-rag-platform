from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.modules.documents.schemas import DocumentParseResponse, DocumentResponse, DocumentUploadRequest
from app.modules.documents.service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service() -> DocumentService:
    return DocumentService()


@router.post("", response_model=DocumentResponse, summary="Upload a document")
async def upload_document(
    file: UploadFile = File(...),
    tenant_id: str = Form("tenant-1"),
    title: str | None = Form(default=None),
    content_type: str | None = Form(default=None),
    service: Annotated[DocumentService, Depends(get_document_service)] = None,
) -> DocumentResponse:
    if file.filename is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required")

    content = await file.read()
    request = DocumentUploadRequest(
        tenant_id=tenant_id,
        title=title or file.filename,
        content_type=content_type or file.filename.rsplit(".", 1)[-1].lower(),
        size_bytes=len(content),
    )
    try:
        return await service.upload_document(request, content, file.filename)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{document_id}/parse", response_model=DocumentParseResponse, summary="Parse a document into structured JSON")
async def parse_document(
    document_id: str,
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentParseResponse:
    parsed = await service.parse_document(document_id)
    return DocumentParseResponse(**parsed)
