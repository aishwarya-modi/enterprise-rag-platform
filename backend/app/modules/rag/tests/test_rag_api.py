from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestRAGQueryEndpoint:
    def test_query_returns_200_with_valid_request(self) -> None:
        response = client.post(
            "/api/v1/rag/query",
            json={"query": "What is enterprise RAG?", "tenant_id": "test-tenant"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "citations" in data
        assert "step_history" in data
        assert data["status"] in ("completed", "failed")
        assert isinstance(data["citations"], list)

    def test_query_includes_step_history(self) -> None:
        response = client.post(
            "/api/v1/rag/query",
            json={"query": "Explain document processing"},
        )
        data = response.json()
        assert len(data["step_history"]) > 0
        assert "rewrite_query" in data["step_history"]
        assert "retrieve_documents" in data["step_history"]

    def test_query_with_custom_provider(self) -> None:
        response = client.post(
            "/api/v1/rag/query",
            json={"query": "Hello", "provider": "anthropic", "model": "claude-3-haiku-20240307"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "anthropic"
        assert data["model"] == "claude-3-haiku-20240307"

    def test_query_with_empty_query_returns_422(self) -> None:
        response = client.post("/api/v1/rag/query", json={"query": ""})
        assert response.status_code == 422

    def test_query_with_missing_query_returns_422(self) -> None:
        response = client.post("/api/v1/rag/query", json={})
        assert response.status_code == 422


class TestRAGStreamEndpoint:
    def test_stream_returns_sse_headers(self) -> None:
        response = client.post(
            "/api/v1/rag/query/stream",
            json={"query": "What is RAG?"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["connection"] == "keep-alive"
        assert response.headers["x-accel-buffering"] == "no"

    def test_stream_emits_stream_start_event(self) -> None:
        response = client.post(
            "/api/v1/rag/query/stream",
            json={"query": "What is RAG?"},
        )
        assert "event: stream_start" in response.text

    def test_stream_emits_stream_complete_event(self) -> None:
        response = client.post(
            "/api/v1/rag/query/stream",
            json={"query": "What is RAG?"},
        )
        assert "event: stream_complete" in response.text

    def test_stream_emits_step_events(self) -> None:
        response = client.post(
            "/api/v1/rag/query/stream",
            json={"query": "What is RAG?"},
        )
        assert "event: step_start" in response.text
        assert "event: step_complete" in response.text

    def test_stream_emits_token_events(self) -> None:
        response = client.post(
            "/api/v1/rag/query/stream",
            json={"query": "What is RAG?"},
        )
        assert "event: token" in response.text

    def test_stream_emits_citation_events(self) -> None:
        response = client.post(
            "/api/v1/rag/query/stream",
            json={"query": "What is RAG?"},
        )
        assert "event: citation" in response.text

    def test_stream_has_query_id(self) -> None:
        response = client.post(
            "/api/v1/rag/query/stream",
            json={"query": "What is RAG?"},
        )
        assert "query_id" in response.text

    def test_stream_token_events_have_field(self) -> None:
        response = client.post(
            "/api/v1/rag/query/stream",
            json={"query": "What is RAG?"},
        )
        assert "event: token" in response.text
        assert '"token"' in response.text
        assert '"field"' in response.text
        assert '"node"' in response.text

    def test_stream_complete_has_full_answer(self) -> None:
        response = client.post(
            "/api/v1/rag/query/stream",
            json={"query": "What is RAG?"},
        )
        assert "event: stream_complete" in response.text
        assert '"answer"' in response.text
        assert '"citations"' in response.text
        assert '"step_history"' in response.text
        assert '"status"' in response.text


class TestRAGAbortEndpoint:
    def test_abort_nonexistent_stream_returns_404(self) -> None:
        response = client.post("/api/v1/rag/query/nonexistent-id/abort")
        assert response.status_code == 404

    def test_abort_returns_success_for_active_stream(self) -> None:
        response = client.post(
            "/api/v1/rag/query/stream",
            json={"query": "What is RAG?"},
        )
        assert "query_id" in response.text
        import re
        match = re.search(r'"query_id":\s*"([^"]+)"', response.text)
        if match:
            query_id = match.group(1)
            abort_response = client.post(f"/api/v1/rag/query/{query_id}/abort")
            assert abort_response.status_code in (200, 404)


class TestRAGGraphVisualization:
    def test_graph_returns_mermaid(self) -> None:
        response = client.get("/api/v1/rag/graph")
        assert response.status_code == 200
        data = response.json()
        assert "mermaid" in data
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert len(data["nodes"]) > 0

    def test_graph_nodes_have_required_fields(self) -> None:
        response = client.get("/api/v1/rag/graph")
        data = response.json()
        for node in data["nodes"]:
            assert "id" in node
            assert "label" in node
            assert "type" in node
            assert "description" in node

    def test_graph_edges_have_required_fields(self) -> None:
        response = client.get("/api/v1/rag/graph")
        data = response.json()
        for edge in data["edges"]:
            assert "source" in edge
            assert "target" in edge


class TestRAGWorkflowNodes:
    def test_rewrite_query_returns_rewritten(self) -> None:
        from app.modules.rag.nodes import rewrite_query
        from app.modules.rag.state import RAGState

        state = RAGState(query="What is RAG?")
        import asyncio

        result = asyncio.run(rewrite_query(state))
        assert "rewritten_query" in result
        assert len(result["rewritten_query"]) > 0
        assert "rewrite_query" in result["step_history"]

    def test_retrieve_documents_returns_documents(self) -> None:
        from app.modules.rag.nodes import retrieve_documents
        from app.modules.rag.state import RAGState

        state = RAGState(query="test query", rewritten_query="test query", tenant_id="test")
        import asyncio

        result = asyncio.run(retrieve_documents(state))
        assert "documents" in result
        assert len(result["documents"]) > 0
        assert "retrieve_documents" in result["step_history"]

    def test_rerank_documents_sorts_by_score(self) -> None:
        from app.modules.rag.nodes import rerank_documents
        from app.modules.rag.state import RAGState

        docs = [
            {"id": "1", "text": "low", "metadata": {}, "score": 0.3},
            {"id": "2", "text": "high", "metadata": {}, "score": 0.9},
            {"id": "3", "text": "mid", "metadata": {}, "score": 0.6},
        ]
        state = RAGState(query="test", documents=docs)
        import asyncio

        result = asyncio.run(rerank_documents(state))
        assert len(result["ranked_documents"]) == 3
        assert result["ranked_documents"][0]["score"] >= result["ranked_documents"][1]["score"]
        assert result["ranked_documents"][1]["score"] >= result["ranked_documents"][2]["score"]

    def test_compress_context_returns_string(self) -> None:
        from app.modules.rag.nodes import compress_context
        from app.modules.rag.state import RAGState

        docs = [{"id": "1", "text": "Sample document text", "metadata": {"source": "test.pdf", "page": 1}, "score": 0.9}]
        state = RAGState(query="test", rewritten_query="test", ranked_documents=docs)
        import asyncio

        result = asyncio.run(compress_context(state))
        assert "compressed_context" in result
        assert len(result["compressed_context"]) > 0

    def test_generate_answer_returns_answer(self) -> None:
        from app.modules.rag.nodes import generate_answer
        from app.modules.rag.state import RAGState

        state = RAGState(query="test", rewritten_query="test", compressed_context="Some context about testing.")
        import asyncio

        result = asyncio.run(generate_answer(state))
        assert "answer" in result
        assert len(result["answer"]) > 0

    def test_generate_citations_returns_list(self) -> None:
        from app.modules.rag.nodes import generate_citations
        from app.modules.rag.state import RAGState

        docs = [{"id": "1", "text": "Citation text", "metadata": {"source": "doc.pdf", "page": 5}, "score": 0.9}]
        state = RAGState(
            query="test",
            rewritten_query="test",
            answer="This is based on doc.pdf page 5.",
            ranked_documents=docs,
        )
        import asyncio

        result = asyncio.run(generate_citations(state))
        assert "citations" in result
        assert isinstance(result["citations"], list)
        assert len(result["citations"]) > 0

    def test_handle_failure_returns_error_message(self) -> None:
        from app.modules.rag.nodes import handle_failure
        from app.modules.rag.state import RAGState

        state = RAGState(error="Something went wrong")
        import asyncio

        result = asyncio.run(handle_failure(state))
        assert "answer" in result
        assert "Something went wrong" in result["answer"]
        assert result["status"] == "failed"


class TestRAGState:
    def test_default_state_values(self) -> None:
        from app.modules.rag.state import RAGState

        state = RAGState()
        assert state.query == ""
        assert state.rewritten_query == ""
        assert state.documents == []
        assert state.ranked_documents == []
        assert state.compressed_context == ""
        assert state.answer == ""
        assert state.citations == []
        assert state.retry_count == 0
        assert state.max_retries == 2
        assert state.status == "running"

    def test_state_reduce_docs_replaces(self) -> None:
        from app.modules.rag.state import reduce_docs

        result = reduce_docs([{"id": "1"}], [{"id": "2"}])
        assert result == [{"id": "2"}]

    def test_state_reduce_docs_keeps_left_on_none_right(self) -> None:
        from app.modules.rag.state import reduce_docs

        result = reduce_docs([{"id": "1"}], None)
        assert result == [{"id": "1"}]

    def test_state_reduce_docs_empty_on_both_none(self) -> None:
        from app.modules.rag.state import reduce_docs

        result = reduce_docs(None, None)
        assert result == []


class TestStreamSSEFormat:
    def test_stream_event_to_sse_format(self) -> None:
        from app.modules.rag.streaming import EventType, StreamEvent

        event = StreamEvent(
            event=EventType.TOKEN,
            data={"token": "hello", "node": "test", "field": "answer"},
            id="test-123",
        )
        sse = event.to_sse()
        assert "id: test-123" in sse
        assert "event: token" in sse
        assert "data:" in sse
        assert sse.endswith("\n\n")

    def test_stream_event_with_retry(self) -> None:
        from app.modules.rag.streaming import EventType, StreamEvent

        event = StreamEvent(
            event=EventType.ERROR,
            data={"error": "fail"},
            retry=5000,
        )
        sse = event.to_sse()
        assert "retry: 5000" in sse
        assert "event: error" in sse

    def test_stream_start_registers_controller(self) -> None:
        from app.modules.rag.streaming import (
            StreamAbortController,
            _active_streams,
            register_stream,
            unregister_stream,
        )

        controller = register_stream("test-query-1")
        assert "test-query-1" in _active_streams
        assert _active_streams["test-query-1"] is controller
        unregister_stream("test-query-1")
        assert "test-query-1" not in _active_streams

    def test_abort_controller_sets_flag(self) -> None:
        from app.modules.rag.streaming import StreamAbortController

        controller = StreamAbortController()
        assert not controller.is_aborted
        controller.abort()
        assert controller.is_aborted
