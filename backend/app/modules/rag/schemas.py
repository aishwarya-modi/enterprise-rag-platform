from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.modules.llm.schemas import LLMProvider


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000, description="The user query to process through the RAG pipeline")
    tenant_id: str = Field(default="default", description="Tenant identifier for multi-tenant isolation")
    provider: LLMProvider = Field(default=LLMProvider.openai, description="LLM provider to use")
    model: str = Field(default="gpt-4o-mini", description="Model identifier for the chosen provider")
    max_retries: int = Field(default=2, ge=0, le=5, description="Maximum number of retry attempts on failure")


class Citation(BaseModel):
    source: str = Field(description="Source document filename or identifier")
    page: int = Field(description="Page number in the source document")
    excerpt: str = Field(description="Relevant text excerpt from the source")


class RAGQueryResponse(BaseModel):
    answer: str = Field(description="Generated answer to the query")
    citations: list[Citation] = Field(default_factory=list, description="Source citations for the answer")
    rewritten_query: str = Field(description="The rewritten query used for retrieval")
    step_history: list[str] = Field(description="Ordered list of workflow steps executed")
    status: str = Field(description="Final status: completed or failed")
    provider: str = Field(description="LLM provider used")
    model: str = Field(description="Model used")


class GraphVisualizationResponse(BaseModel):
    mermaid: str = Field(description="Mermaid diagram definition of the workflow graph")
    nodes: list[dict[str, str]] = Field(description="Graph nodes with id, label, type, and description")
    edges: list[dict[str, str]] = Field(description="Graph edges with source, target, and condition")


class SSEStreamStartData(BaseModel):
    query_id: str
    query: str


class SSEStepData(BaseModel):
    node: str
    message: Optional[str] = None
    rewritten_query: Optional[str] = None
    document_count: Optional[int] = None
    ranked_count: Optional[int] = None
    citation_count: Optional[int] = None
    error: Optional[str] = None


class SSETokenData(BaseModel):
    node: str
    token: str
    field: Literal["rewritten_query", "compressed_context", "answer"]


class SSECitationData(BaseModel):
    citation: dict[str, Any]


class SSEAnswerCompleteData(BaseModel):
    answer: str


class SSEStreamCompleteData(BaseModel):
    query_id: str
    status: Literal["completed", "failed"]
    answer: str
    citations: list[dict[str, Any]]
    step_history: list[str]
    rewritten_query: str
    provider: str
    model: str


class SSEErrorData(BaseModel):
    query_id: Optional[str] = None
    error: str
    message: Optional[str] = None


class AbortRequest(BaseModel):
    query_id: str = Field(description="The query ID to abort")


class AbortResponse(BaseModel):
    success: bool
    query_id: str
    message: str
