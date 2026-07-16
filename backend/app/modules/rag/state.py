from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any, Literal, Optional

from langgraph.graph.message import add_messages


def reduce_docs(left: Optional[list[dict[str, Any]]], right: Optional[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    if right is None:
        return left or []
    return right


@dataclass
class RAGState:
    query: str = ""
    rewritten_query: str = ""
    documents: Annotated[list[dict[str, Any]], reduce_docs] = field(default_factory=list)
    ranked_documents: list[dict[str, Any]] = field(default_factory=list)
    compressed_context: str = ""
    answer: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)
    messages: Annotated[list[Any], add_messages] = field(default_factory=list)
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    tenant_id: str = ""
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2
    step_history: list[str] = field(default_factory=list)
    status: Literal["running", "completed", "failed"] = "running"
