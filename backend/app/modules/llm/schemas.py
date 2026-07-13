from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    openai = "openai"
    anthropic = "anthropic"
    gemini = "gemini"
    ollama = "ollama"


class ChatRequest(BaseModel):
    tenant_id: str
    provider: Literal["openai", "anthropic", "gemini", "ollama"] = "openai"
    model: str = Field(default="gpt-4o-mini")
    prompt: str = Field(min_length=1)


class ChatResponse(BaseModel):
    provider: str
    model: str
    response: str
