from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.llm.schemas import ChatRequest, ChatResponse
from app.modules.llm.service import LLMService

router = APIRouter(prefix="/llm", tags=["llm"])


def get_llm_service() -> LLMService:
    return LLMService()


@router.post("/chat", response_model=ChatResponse, summary="Chat with the configured LLM provider")
async def chat(request: ChatRequest, service: Annotated[LLMService, Depends(get_llm_service)]) -> ChatResponse:
    return await service.chat(request)
