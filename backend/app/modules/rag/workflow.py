from __future__ import annotations

import logging
from typing import Any, Literal

from langgraph.graph import END, StateGraph

from app.modules.rag.nodes import (
    compress_context,
    generate_answer,
    generate_citations,
    handle_failure,
    rerank_documents,
    retrieve_documents,
    rewrite_query,
)
from app.modules.rag.state import RAGState

logger = logging.getLogger(__name__)


def _check_retries(state: RAGState) -> Literal["handle_failure", "rewrite_query"]:
    if state.retry_count < state.max_retries:
        logger.info("Retrying workflow (attempt %d/%d)", state.retry_count + 1, state.max_retries)
        return "rewrite_query"
    return "handle_failure"


def _route_after_retrieve(state: RAGState) -> Literal["handle_failure", "rerank_documents"]:
    if state.error:
        if state.retry_count < state.max_retries:
            return "handle_failure"
    if not state.documents:
        state.error = "No documents retrieved"
        if state.retry_count < state.max_retries:
            return "handle_failure"
    return "rerank_documents"


def _should_retry_on_error(state: RAGState) -> Literal["handle_failure", "rewrite_query"]:
    if state.error and state.retry_count < state.max_retries:
        return "rewrite_query"
    if state.error:
        return "handle_failure"
    return "generate_citations"


def _increment_retry(state: RAGState) -> dict[str, Any]:
    return {"retry_count": state.retry_count + 1, "error": None}


def build_rag_graph() -> StateGraph:
    graph = StateGraph(RAGState)

    graph.add_node("rewrite_query", rewrite_query)
    graph.add_node("retrieve_documents", retrieve_documents)
    graph.add_node("rerank_documents", rerank_documents)
    graph.add_node("compress_context", compress_context)
    graph.add_node("generate_answer", generate_answer)
    graph.add_node("generate_citations", generate_citations)
    graph.add_node("handle_failure", handle_failure)
    graph.add_node("increment_retry", _increment_retry)

    graph.set_entry_point("rewrite_query")
    graph.add_edge("rewrite_query", "retrieve_documents")

    graph.add_conditional_edges(
        "retrieve_documents",
        _route_after_retrieve,
        {
            "rerank_documents": "rerank_documents",
            "handle_failure": "increment_retry",
        },
    )

    graph.add_edge("rerank_documents", "compress_context")
    graph.add_edge("compress_context", "generate_answer")

    graph.add_conditional_edges(
        "generate_answer",
        _should_retry_on_error,
        {
            "generate_citations": "generate_citations",
            "handle_failure": "handle_failure",
            "rewrite_query": "increment_retry",
        },
    )

    graph.add_conditional_edges(
        "generate_citations",
        lambda s: "handle_failure" if s.error else END,
        {"handle_failure": "handle_failure", END: END},
    )

    graph.add_conditional_edges(
        "increment_retry",
        _check_retries,
        {
            "rewrite_query": "rewrite_query",
            "handle_failure": "handle_failure",
        },
    )

    graph.add_edge("handle_failure", END)

    return graph


_rag_app = None


def get_rag_app() -> Any:
    global _rag_app
    if _rag_app is None:
        _rag_app = build_rag_graph().compile()
    return _rag_app


def get_graph_visualization() -> dict[str, Any]:
    graph = build_rag_graph()
    compiled = graph.compile()
    try:
        mermaid = compiled.get_graph().draw_mermaid()
    except Exception:
        mermaid = "graph TD\n  rewrite_query --> retrieve_documents\n  retrieve_documents --> rerank_documents\n  rerank_documents --> compress_context\n  compress_context --> generate_answer\n  generate_answer --> generate_citations\n  generate_citations --> END"
    nodes = [
        {"id": "rewrite_query", "label": "Rewrite Query", "type": "llm", "description": "Rewrites the user query for better retrieval"},
        {"id": "retrieve_documents", "label": "Retrieve Documents", "type": "retrieval", "description": "Fetches relevant documents from Qdrant"},
        {"id": "rerank_documents", "label": "Rerank Documents", "type": "ranking", "description": "Reranks documents by relevance"},
        {"id": "compress_context", "label": "Compress Context", "type": "llm", "description": "Summarizes retrieved context"},
        {"id": "generate_answer", "label": "Generate Answer", "type": "llm", "description": "Generates the final answer"},
        {"id": "generate_citations", "label": "Generate Citations", "type": "llm", "description": "Extracts source citations"},
        {"id": "handle_failure", "label": "Handle Failure", "type": "error", "description": "Handles errors gracefully"},
        {"id": "increment_retry", "label": "Increment Retry", "type": "control", "description": "Tracks retry attempts"},
    ]
    edges = [
        {"source": "rewrite_query", "target": "retrieve_documents"},
        {"source": "retrieve_documents", "target": "rerank_documents", "condition": "success"},
        {"source": "retrieve_documents", "target": "increment_retry", "condition": "error/no_docs"},
        {"source": "rerank_documents", "target": "compress_context"},
        {"source": "compress_context", "target": "generate_answer"},
        {"source": "generate_answer", "target": "generate_citations", "condition": "success"},
        {"source": "generate_answer", "target": "handle_failure", "condition": "error/no_retries"},
        {"source": "generate_answer", "target": "increment_retry", "condition": "error/retry"},
        {"source": "generate_citations", "target": "END"},
        {"source": "generate_citations", "target": "handle_failure", "condition": "error"},
        {"source": "increment_retry", "target": "rewrite_query", "condition": "retries_remaining"},
        {"source": "increment_retry", "target": "handle_failure", "condition": "max_retries"},
        {"source": "handle_failure", "target": "END"},
    ]
    return {"mermaid": mermaid, "nodes": nodes, "edges": edges}
