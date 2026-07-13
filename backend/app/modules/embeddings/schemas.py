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
