from app.modules.documents.schemas import DocumentResponse, DocumentStatus, DocumentUploadRequest


class DocumentService:
    async def upload_document(self, request: DocumentUploadRequest) -> DocumentResponse:
        return DocumentResponse(
            id="doc-1",
            tenant_id=request.tenant_id,
            title=request.title,
            status=DocumentStatus.processing,
            content_type=request.content_type,
        )
