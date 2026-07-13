from pydantic import BaseModel, Field


class EmbeddingRequest(BaseModel):
    texts: list[str] = Field(min_length=1)
    provider: str = "openai"
    model: str | None = None
    dimensions: int | None = None
    batch_size: int = 32
    retry_count: int = 3


class EmbeddingResponse(BaseModel):
    embeddings: list[list[float]]
    provider: str
    model: str
    dimensions: int


class ContextCompressionRequest(BaseModel):
    contexts: list[dict[str, object]] = Field(default_factory=list)
    strategy: str = "hybrid"
    max_tokens: int = 512
    preserve_citations: bool = True


class ContextCompressionResponse(BaseModel):
    compressed_context: list[dict[str, object]]
    original_token_count: int
    compressed_token_count: int
    removed_items: int
    strategy: str
