from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from app.core.cache import CacheNamespace, get_cache, make_hash, make_key

logger = logging.getLogger(__name__)


def _get_settings():
    from app.core.config import get_settings

    return get_settings()


def _llm_cache_key(provider: str, model: str, messages: list[dict[str, str]]) -> str:
    content = json.dumps(messages, sort_keys=True, default=str)
    h = make_hash(provider, model, content)
    return make_key(CacheNamespace.LLM, provider, model, h)


def _embedding_cache_key(query: str) -> str:
    h = make_hash(query)
    return make_key(CacheNamespace.EMBEDDING, h)


def _search_cache_key(query: str, tenant_id: str, limit: int) -> str:
    h = make_hash(query, tenant_id, str(limit))
    return make_key(CacheNamespace.SEARCH, "tenant", tenant_id, h)


async def _call_llm(provider: str, model: str, messages: list[dict[str, str]]) -> str:
    cache = get_cache()
    settings = _get_settings()
    cache_key = _llm_cache_key(provider, model, messages)
    cached = await cache.get(cache_key, CacheNamespace.LLM.value)
    if cached is not None:
        logger.debug("LLM cache hit: %s", cache_key)
        return cached

    result = await _call_llm_uncached(provider, model, messages)
    if result:
        await cache.set(cache_key, result, ttl=settings.cache_llm_ttl, namespace=CacheNamespace.LLM.value)
    return result


async def _call_llm_uncached(provider: str, model: str, messages: list[dict[str, str]]) -> str:
    settings = _get_settings()
    if provider == "openai" and settings.openai_api_key:
        import openai

        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(model=model, messages=messages)
        return resp.choices[0].message.content or ""
    if provider == "anthropic" and settings.anthropic_api_key:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_msgs = [m["content"] for m in messages if m["role"] == "user"]
        resp = await client.messages.create(
            model=model, max_tokens=4096, system=system_msg, messages=[{"role": "user", "content": "\n".join(user_msgs)}]
        )
        return resp.content[0].text if resp.content else ""
    return _mock_llm_response(provider, messages)


def _mock_llm_response(provider: str, messages: list[dict[str, str]]) -> str:
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
        sources = re.findall(r'\[Source: ([^,\]]+), Page: (\d+)\]', last_msg)
        if sources:
            return json.dumps([
                {"source": s[0], "page": int(s[1]), "excerpt": "Referenced in document."}
                for s in sources[:5]
            ])
        docs_match = re.search(r'Documents:\s*(\[.*\])', last_msg, re.DOTALL)
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
        chunks = re.split(r'\[Source:', last_msg[docs_start:])
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


async def _embed_query(query: str) -> list[float]:
    cache = get_cache()
    settings = _get_settings()
    cache_key = _embedding_cache_key(query)
    cached = await cache.get(cache_key, CacheNamespace.EMBEDDING.value)
    if cached is not None:
        logger.debug("Embedding cache hit")
        return cached

    import hashlib
    import random
    h = hashlib.sha256(query.encode()).digest()
    random.seed(h)
    embedding = [random.gauss(0, 0.3) for _ in range(1536)]
    norm = sum(v * v for v in embedding) ** 0.5
    embedding = [v / norm for v in embedding]
    await cache.set(cache_key, embedding, ttl=settings.cache_embedding_ttl, namespace=CacheNamespace.EMBEDDING.value)
    return embedding


async def _search_documents(query: str, tenant_id: str, limit: int = 10) -> list[dict[str, Any]]:
    cache = get_cache()
    settings = _get_settings()
    cache_key = _search_cache_key(query, tenant_id, limit)
    cached = await cache.get(cache_key, CacheNamespace.SEARCH.value)
    if cached is not None:
        logger.debug("Search cache hit for query: %s", query[:50])
        return cached

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        qdrant_settings = _get_settings()
        client = QdrantClient(url=qdrant_settings.qdrant_url)
        embedding = await _embed_query(query)
        result = client.query_points(
            collection_name=f"tenant_{tenant_id}",
            query=embedding,
            limit=limit,
            query_filter=Filter(must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))])
            if tenant_id
            else None,
        )
        documents = [
            {"id": str(r.id), "text": r.payload.get("text", ""), "metadata": r.payload.get("metadata", {}), "score": r.score}
            for r in result.points
        ]
    except Exception as e:
        logger.warning("Qdrant retrieval failed, using mock documents: %s", e)
        documents = [
            {"id": f"doc-{i}", "text": f"Mock document chunk {i} related to: {query[:50]}", "metadata": {"source": f"file-{i}.pdf", "page": i}, "score": 0.9 - i * 0.05}
            for i in range(5)
        ]

    await cache.set(cache_key, documents, ttl=settings.cache_search_ttl, namespace=CacheNamespace.SEARCH.value)
    return documents


async def rewrite_query(state: Any) -> dict[str, Any]:
    logger.info("Rewriting query: %s", state.query)
    messages = [
        {"role": "system", "content": (
            "You are a query rewriting specialist. Rewrite the user query to improve "
            "retrieval quality. Preserve semantic meaning while making the query more "
            "specific and searchable. Return ONLY the rewritten query, nothing else."
        )},
        {"role": "user", "content": state.query},
    ]
    rewritten = await _call_llm(state.provider, state.model, messages)
    logger.info("Rewritten query: %s", rewritten)
    return {
        "rewritten_query": rewritten.strip(),
        "step_history": [*state.step_history, "rewrite_query"],
    }


async def retrieve_documents(state: Any) -> dict[str, Any]:
    query = state.rewritten_query or state.query
    logger.info("Retrieving documents for: %s", query)
    documents = await _search_documents(query, state.tenant_id)
    return {"documents": documents, "step_history": [*state.step_history, "retrieve_documents"]}


async def rerank_documents(state: Any) -> dict[str, Any]:
    logger.info("Reranking %d documents", len(state.documents))
    if not state.documents:
        return {"ranked_documents": [], "step_history": [*state.step_history, "rerank_documents"]}
    try:
        ranked = sorted(state.documents, key=lambda d: d.get("score", 0), reverse=True)[:5]
    except Exception as e:
        logger.warning("Reranking failed, using original order: %s", e)
        ranked = state.documents[:5]
    return {"ranked_documents": ranked, "step_history": [*state.step_history, "rerank_documents"]}


async def compress_context(state: Any) -> dict[str, Any]:
    logger.info("Compressing context from %d documents", len(state.ranked_documents))
    if not state.ranked_documents:
        return {"compressed_context": "No relevant context found.", "step_history": [*state.step_history, "compress_context"]}
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
    compressed = await _call_llm(state.provider, state.model, messages)
    return {"compressed_context": compressed, "step_history": [*state.step_history, "compress_context"]}


async def generate_answer(state: Any) -> dict[str, Any]:
    logger.info("Generating answer")
    messages = [
        {"role": "system", "content": (
            "You are a helpful enterprise assistant. Answer the user's question using ONLY "
            "the provided context. If the context does not contain enough information, say so. "
            "Be precise, cite your sources inline using [Source: filename, Page: X] format. "
            "Structure your response clearly."
        )},
        {"role": "user", "content": f"Context:\n{state.compressed_context}\n\nQuestion: {state.rewritten_query or state.query}"},
    ]
    answer = await _call_llm(state.provider, state.model, messages)
    return {"answer": answer, "step_history": [*state.step_history, "generate_answer"]}


async def generate_citations(state: Any) -> dict[str, Any]:
    logger.info("Generating citations")
    if not state.ranked_documents:
        return {"citations": [], "status": "completed", "step_history": [*state.step_history, "generate_citations"]}
    messages = [
        {"role": "system", "content": (
            "Extract citations from the answer based on the provided documents. "
            "Return a JSON array of objects with keys: source, page, excerpt. "
            "Only include citations that are actually referenced in the answer."
        )},
        {"role": "user", "content": f"Answer:\n{state.answer}\n\nDocuments:\n{json.dumps(state.ranked_documents, default=str)}"},
    ]
    raw = await _call_llm(state.provider, state.model, messages)
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
    return {"citations": citations, "status": "completed", "step_history": [*state.step_history, "generate_citations"]}


async def handle_failure(state: Any) -> dict[str, Any]:
    logger.error("Workflow failure: %s", state.error)
    return {
        "answer": f"I encountered an error while processing your query: {state.error}. Please try again.",
        "status": "failed",
        "step_history": [*state.step_history, "handle_failure"],
    }
