from __future__ import annotations

import logging
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.modules.rag.schemas import (
    AbortRequest,
    AbortResponse,
    GraphVisualizationResponse,
    RAGQueryRequest,
    RAGQueryResponse,
)
from app.modules.rag.state import RAGState
from app.modules.rag.streaming import (
    EventType,
    StreamEvent,
    get_stream_controller,
    register_stream,
    stream_rag_workflow,
    unregister_stream,
)
from app.modules.rag.workflow import get_graph_visualization, get_rag_app

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG Pipeline"])


def _extract_state_field(result: Any, field: str, default: Any = "") -> Any:
    if isinstance(result, dict):
        return result.get(field, default)
    return getattr(result, field, default)


async def _sse_generator(request: RAGQueryRequest) -> AsyncGenerator[str, None]:
    request_data = {
        "query": request.query,
        "tenant_id": request.tenant_id,
        "provider": request.provider.value,
        "model": request.model,
        "max_retries": request.max_retries,
    }
    async for event in stream_rag_workflow(request_data):
        yield event.to_sse()


@router.post("/query", response_model=RAGQueryResponse)
async def query_rag(request: RAGQueryRequest) -> RAGQueryResponse:
    app = get_rag_app()
    initial_state = RAGState(
        query=request.query,
        tenant_id=request.tenant_id,
        provider=request.provider.value,
        model=request.model,
        max_retries=request.max_retries,
    )
    try:
        result = await app.ainvoke(initial_state, config={"recursion_limit": 25})
    except Exception as e:
        logger.error("RAG workflow error: %s", e)
        raise HTTPException(status_code=500, detail=f"RAG pipeline failed: {e}")
    return RAGQueryResponse(
        answer=_extract_state_field(result, "answer"),
        citations=_extract_state_field(result, "citations", []),
        rewritten_query=_extract_state_field(result, "rewritten_query"),
        step_history=_extract_state_field(result, "step_history", []),
        status=_extract_state_field(result, "status", "completed"),
        provider=_extract_state_field(result, "provider", request.provider.value),
        model=_extract_state_field(result, "model", request.model),
    )


@router.post("/query/stream")
async def query_rag_stream(request: RAGQueryRequest) -> StreamingResponse:
    return StreamingResponse(
        _sse_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control, Last-Event-ID",
        },
    )


@router.post("/query/{query_id}/abort", response_model=AbortResponse)
async def abort_query(query_id: str) -> AbortResponse:
    controller = get_stream_controller(query_id)
    if controller is None:
        raise HTTPException(status_code=404, detail=f"Stream {query_id} not found or already completed")
    controller.abort()
    return AbortResponse(
        success=True,
        query_id=query_id,
        message=f"Stream {query_id} abort signal sent",
    )


@router.get("/graph", response_model=GraphVisualizationResponse)
async def get_rag_graph() -> GraphVisualizationResponse:
    viz = get_graph_visualization()
    return GraphVisualizationResponse(
        mermaid=viz["mermaid"],
        nodes=viz["nodes"],
        edges=viz["edges"],
    )
