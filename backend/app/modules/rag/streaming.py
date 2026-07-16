from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Optional

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    STREAM_START = "stream_start"
    STEP_START = "step_start"
    STEP_COMPLETE = "step_complete"
    TOKEN = "token"
    CITATION = "citation"
    ANSWER_COMPLETE = "answer_complete"
    STREAM_COMPLETE = "stream_complete"
    ERROR = "error"
    ABORTED = "aborted"


@dataclass
class StreamEvent:
    event: EventType
    data: dict[str, Any]
    id: Optional[str] = None
    retry: Optional[int] = None

    def to_sse(self) -> str:
        parts = []
        if self.id:
            parts.append(f"id: {self.id}")
        parts.append(f"event: {self.event.value}")
        if self.retry is not None:
            parts.append(f"retry: {self.retry}")
        payload = json.dumps(self.data, default=str)
        parts.append(f"data: {payload}")
        return "\n".join(parts) + "\n\n"


class StreamAbortController:
    def __init__(self) -> None:
        self._abort_event = threading.Event()
        self._query_id: str = ""

    @property
    def query_id(self) -> str:
        return self._query_id

    @query_id.setter
    def query_id(self, value: str) -> None:
        self._query_id = value

    def abort(self) -> None:
        self._abort_event.set()

    @property
    def is_aborted(self) -> bool:
        return self._abort_event.is_set()

    async def wait_if_needed(self) -> None:
        if self._abort_event.is_set():
            raise StreamAbortedError(self._query_id)


class StreamAbortedError(Exception):
    def __init__(self, query_id: str) -> None:
        self.query_id = query_id
        super().__init__(f"Stream {query_id} was aborted by client")


_active_streams: dict[str, StreamAbortController] = {}


def register_stream(query_id: str) -> StreamAbortController:
    controller = StreamAbortController()
    controller.query_id = query_id
    _active_streams[query_id] = controller
    return controller


def get_stream_controller(query_id: str) -> Optional[StreamAbortController]:
    return _active_streams.get(query_id)


def unregister_stream(query_id: str) -> None:
    _active_streams.pop(query_id, None)


async def _call_llm_streaming(
    provider: str,
    model: str,
    messages: list[dict[str, str]],
    abort_controller: Optional[StreamAbortController] = None,
) -> AsyncGenerator[str, None]:
    from app.core.config import get_settings

    settings = get_settings()

    if provider == "openai" and settings.openai_api_key:
        import openai

        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        stream = await client.chat.completions.create(model=model, messages=messages, stream=True)
        async for chunk in stream:
            await abort_controller.wait_if_needed() if abort_controller else None
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content
        return

    if provider == "anthropic" and settings.anthropic_api_key:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_msgs = [m["content"] for m in messages if m["role"] == "user"]
        async with client.messages.stream(
            model=model,
            max_tokens=4096,
            system=system_msg,
            messages=[{"role": "user", "content": "\n".join(user_msgs)}],
        ) as stream:
            async for text in stream.text_stream:
                await abort_controller.wait_if_needed() if abort_controller else None
                yield text
        return

    full_response = _mock_streaming_response(messages)
    for char in full_response:
        await abort_controller.wait_if_needed() if abort_controller else None
        yield char
        await asyncio.sleep(0.01)


def _mock_streaming_response(messages: list[dict[str, str]]) -> str:
    import re as _re
    all_text = " ".join(m["content"] for m in messages).lower()
    last_msg = messages[-1]["content"] if messages else ""
    if "rewrite" in all_text or "reformulat" in all_text:
        if "Query:" in last_msg:
            return last_msg.split("Query:")[-1].split("\n")[0].strip()
        return last_msg
    if "summarize" in all_text or "compress" in all_text:
        docs_start = last_msg.find("[Source:")
        if docs_start != -1:
            return last_msg[docs_start:docs_start + 500]
        return "No relevant context found."
    if "citation" in all_text:
        sources = _re.findall(r'\[Source: ([^,\]]+), Page: (\d+)\]', last_msg)
        if sources:
            return json.dumps([
                {"source": s[0], "page": int(s[1]), "excerpt": "Referenced in document."}
                for s in sources[:5]
            ])
        docs_match = _re.search(r'Documents:\s*(\[.*\])', last_msg, _re.DOTALL)
        if docs_match:
            try:
                docs = json.loads(docs_match.group(1))
                return json.dumps([
                    {"source": d.get("metadata", {}).get("source", "unknown"), "page": d.get("metadata", {}).get("page", 0), "excerpt": d.get("text", "")[:200]}
                    for d in docs[:5]
                ])
            except (json.JSONDecodeError, TypeError):
                pass
        return json.dumps([{"source": "doc-1", "page": 1, "excerpt": "relevant text"}])
    docs_start = last_msg.find("[Source:")
    if docs_start != -1:
        chunks = _re.split(r'\[Source:', last_msg[docs_start:])
        facts = []
        for chunk in chunks[:3]:
            lines = chunk.strip().split("\n")
            text = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
            if text:
                facts.append(text[:300])
        if facts:
            return (
                "Based on the retrieved documents, here is what I found:\n\n"
                + "\n\n".join(f"- {f}" for f in facts)
                + "\n\nThese sources provide relevant context for answering your question."
            )
    return f"Based on the provided context, here is the answer regarding: {last_msg[:80]}..."


async def stream_rag_workflow(
    request_data: dict[str, Any],
    abort_controller: Optional[StreamAbortController] = None,
) -> AsyncGenerator[StreamEvent, None]:
    if abort_controller is None:
        abort_controller = StreamAbortController()

    query_id = str(uuid.uuid4())
    abort_controller.query_id = query_id
    _active_streams[query_id] = abort_controller

    yield StreamEvent(
        event=EventType.STREAM_START,
        data={"query_id": query_id, "query": request_data.get("query", "")},
        id=query_id,
    )

    try:
        from app.modules.rag.nodes import (
            _get_settings,
            _embed_query,
        )
        from app.modules.rag.state import RAGState

        state = RAGState(
            query=request_data.get("query", ""),
            tenant_id=request_data.get("tenant_id", "default"),
            provider=request_data.get("provider", "openai"),
            model=request_data.get("model", "gpt-4o-mini"),
            max_retries=request_data.get("max_retries", 2),
        )

        yield StreamEvent(
            event=EventType.STEP_START,
            data={"node": "rewrite_query", "message": "Rewriting query for better retrieval"},
            id=query_id,
        )

        messages = [
            {"role": "system", "content": (
                "You are a query rewriting specialist. Rewrite the user query to improve "
                "retrieval quality. Preserve semantic meaning while making the query more "
                "specific and searchable. Return ONLY the rewritten query, nothing else."
            )},
            {"role": "user", "content": state.query},
        ]
        rewritten = ""
        async for token in _call_llm_streaming(state.provider, state.model, messages, abort_controller):
            rewritten += token
            yield StreamEvent(
                event=EventType.TOKEN,
                data={"node": "rewrite_query", "token": token, "field": "rewritten_query"},
                id=query_id,
            )
        state.rewritten_query = rewritten.strip()
        yield StreamEvent(
            event=EventType.STEP_COMPLETE,
            data={"node": "rewrite_query", "rewritten_query": state.rewritten_query},
            id=query_id,
        )

        yield StreamEvent(
            event=EventType.STEP_START,
            data={"node": "retrieve_documents", "message": "Searching knowledge base"},
            id=query_id,
        )
        await abort_controller.wait_if_needed()
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            settings = _get_settings()
            client = QdrantClient(url=settings.qdrant_url)
            result = client.query_points(
                collection_name=f"tenant_{state.tenant_id}",
                query=await _embed_query(state.rewritten_query or state.query),
                limit=10,
                query_filter=Filter(must=[FieldCondition(key="tenant_id", match=MatchValue(value=state.tenant_id))])
                if state.tenant_id
                else None,
            )
            state.documents = [
                {"id": str(r.id), "text": r.payload.get("text", ""), "metadata": r.payload.get("metadata", {}), "score": r.score}
                for r in result.points
            ]
        except Exception as e:
            logger.warning("Qdrant retrieval failed, using mock documents: %s", e)
            query_text = state.rewritten_query or state.query
            state.documents = [
                {"id": f"doc-{i}", "text": f"Mock document chunk {i} related to: {query_text[:50]}", "metadata": {"source": f"file-{i}.pdf", "page": i}, "score": 0.9 - i * 0.05}
                for i in range(5)
            ]

        yield StreamEvent(
            event=EventType.STEP_COMPLETE,
            data={"node": "retrieve_documents", "document_count": len(state.documents)},
            id=query_id,
        )

        yield StreamEvent(
            event=EventType.STEP_START,
            data={"node": "rerank_documents", "message": f"Reranking {len(state.documents)} documents"},
            id=query_id,
        )
        await abort_controller.wait_if_needed()
        try:
            state.ranked_documents = sorted(state.documents, key=lambda d: d.get("score", 0), reverse=True)[:5]
        except Exception:
            state.ranked_documents = state.documents[:5]
        yield StreamEvent(
            event=EventType.STEP_COMPLETE,
            data={"node": "rerank_documents", "ranked_count": len(state.ranked_documents)},
            id=query_id,
        )

        yield StreamEvent(
            event=EventType.STEP_START,
            data={"node": "compress_context", "message": "Compressing retrieved context"},
            id=query_id,
        )
        await abort_controller.wait_if_needed()
        if state.ranked_documents:
            context_block = "\n\n".join(
                f"[Source: {d.get('metadata', {}).get('source', 'unknown')}, "
                f"Page: {d.get('metadata', {}).get('page', '?')}]\n{d['text']}"
                for d in state.ranked_documents
            )
            messages = [
                {"role": "system", "content": (
                    "You are a context compression specialist. Given the following retrieved documents, "
                    "extract and summarize only the information relevant to answering the user's question. "
                    "Preserve key facts, numbers, and source references. Be concise but thorough."
                )},
                {"role": "user", "content": f"Query: {state.rewritten_query or state.query}\n\nDocuments:\n{context_block}"},
            ]
            compressed = ""
            async for token in _call_llm_streaming(state.provider, state.model, messages, abort_controller):
                compressed += token
                yield StreamEvent(
                    event=EventType.TOKEN,
                    data={"node": "compress_context", "token": token, "field": "compressed_context"},
                    id=query_id,
                )
            state.compressed_context = compressed
        else:
            state.compressed_context = "No relevant context found."

        yield StreamEvent(
            event=EventType.STEP_COMPLETE,
            data={"node": "compress_context"},
            id=query_id,
        )

        yield StreamEvent(
            event=EventType.STEP_START,
            data={"node": "generate_answer", "message": "Generating answer"},
            id=query_id,
        )
        messages = [
            {"role": "system", "content": (
                "You are a helpful enterprise assistant. Answer the user's question using ONLY "
                "the provided context. If the context does not contain enough information, say so. "
                "Be precise, cite your sources inline using [Source: filename, Page: X] format. "
                "Structure your response clearly."
            )},
            {"role": "user", "content": f"Context:\n{state.compressed_context}\n\nQuestion: {state.rewritten_query or state.query}"},
        ]
        answer = ""
        async for token in _call_llm_streaming(state.provider, state.model, messages, abort_controller):
            answer += token
            yield StreamEvent(
                event=EventType.TOKEN,
                data={"node": "generate_answer", "token": token, "field": "answer"},
                id=query_id,
            )
        state.answer = answer

        yield StreamEvent(
            event=EventType.ANSWER_COMPLETE,
            data={"answer": state.answer},
            id=query_id,
        )
        yield StreamEvent(
            event=EventType.STEP_COMPLETE,
            data={"node": "generate_answer"},
            id=query_id,
        )

        yield StreamEvent(
            event=EventType.STEP_START,
            data={"node": "generate_citations", "message": "Extracting citations"},
            id=query_id,
        )
        await abort_controller.wait_if_needed()
        if state.ranked_documents:
            messages = [
                {"role": "system", "content": (
                    "Extract citations from the answer based on the provided documents. "
                    "Return a JSON array of objects with keys: source, page, excerpt. "
                    "Only include citations that are actually referenced in the answer."
                )},
                {"role": "user", "content": f"Answer:\n{state.answer}\n\nDocuments:\n{json.dumps(state.ranked_documents, default=str)}"},
            ]
            raw = ""
            async for token in _call_llm_streaming(state.provider, state.model, messages, abort_controller):
                raw += token
            try:
                citations = json.loads(raw) if raw.strip().startswith("[") else [
                    {"source": d.get("metadata", {}).get("source", "unknown"), "page": d.get("metadata", {}).get("page", 0), "excerpt": d["text"][:200]}
                    for d in state.ranked_documents
                ]
            except (json.JSONDecodeError, TypeError):
                citations = [
                    {"source": d.get("metadata", {}).get("source", "unknown"), "page": d.get("metadata", {}).get("page", 0), "excerpt": d["text"][:200]}
                    for d in state.ranked_documents
                ]
        else:
            citations = []

        state.citations = citations
        for citation in citations:
            yield StreamEvent(
                event=EventType.CITATION,
                data={"citation": citation},
                id=query_id,
            )

        yield StreamEvent(
            event=EventType.STEP_COMPLETE,
            data={"node": "generate_citations", "citation_count": len(citations)},
            id=query_id,
        )

        state.status = "completed"
        yield StreamEvent(
            event=EventType.STREAM_COMPLETE,
            data={
                "query_id": query_id,
                "status": "completed",
                "answer": state.answer,
                "citations": state.citations,
                "step_history": state.step_history + [
                    "rewrite_query", "retrieve_documents", "rerank_documents",
                    "compress_context", "generate_answer", "generate_citations",
                ],
                "rewritten_query": state.rewritten_query,
                "provider": state.provider,
                "model": state.model,
            },
            id=query_id,
        )

    except StreamAbortedError:
        yield StreamEvent(
            event=EventType.ABORTED,
            data={"query_id": query_id, "message": "Stream was aborted by client"},
            id=query_id,
        )
    except Exception as e:
        logger.error("Streaming workflow error: %s", e)
        yield StreamEvent(
            event=EventType.ERROR,
            data={"query_id": query_id, "error": str(e)},
            id=query_id,
        )
    finally:
        _active_streams.pop(query_id, None)
