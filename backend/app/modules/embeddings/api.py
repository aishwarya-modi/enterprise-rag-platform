from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.modules.embeddings.schemas import EmbeddingRequest, EmbeddingResponse
from app.modules.embeddings.service import EmbeddingService

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()


@router.post("", response_model=EmbeddingResponse, summary="Create embeddings")
async def create_embeddings(
    request: EmbeddingRequest,
    service: Annotated[EmbeddingService, Depends(get_embedding_service)],
) -> EmbeddingResponse:
    try:
        return service.embed_texts(
            request.texts,
            provider=request.provider,
            model=request.model,
            dimensions=request.dimensions,
            batch_size=request.batch_size,
            max_retries=request.retry_count,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
