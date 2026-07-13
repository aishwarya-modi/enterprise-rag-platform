from app.modules.llm.schemas import ChatRequest, ChatResponse


class LLMService:
    async def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            provider=request.provider,
            model=request.model,
            response=f"Mock response from {request.provider} for: {request.prompt}",
        )
