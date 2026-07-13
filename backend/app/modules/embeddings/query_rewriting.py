from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RewriteRequest:
    query: str
    conversation_history: list[str] | None = None
    strategy: str = "hyde"
    intent: str | None = None
    max_queries: int = 3


@dataclass(slots=True)
class RewriteResult:
    rewritten_queries: list[str]
    intent: str
    strategy: str
    metadata: dict[str, Any] = field(default_factory=dict)


class QueryRewriter:
    def rewrite(self, request: RewriteRequest) -> RewriteResult:
        if request.strategy == "step-back":
            return self._step_back_rewrite(request)
        if request.strategy == "llm":
            return self._llm_rewrite(request)
        if request.strategy == "multi-query":
            return self._multi_query_rewrite(request)
        if request.strategy == "intent":
            return self._intent_rewrite(request)
        if request.strategy == "conversation":
            return self._conversation_rewrite(request)
        return self._hyde_rewrite(request)

    def _hyde_rewrite(self, request: RewriteRequest) -> RewriteResult:
        rewritten = [f"Document discussing {request.query}"]
        intent = self._detect_intent(request.query)
        return RewriteResult(rewritten_queries=rewritten, intent=intent, strategy="hyde")

    def _step_back_rewrite(self, request: RewriteRequest) -> RewriteResult:
        rewritten = [f"What is the broader concept behind {request.query}?"]
        intent = self._detect_intent(request.query)
        return RewriteResult(rewritten_queries=rewritten, intent=intent, strategy="step-back")

    def _llm_rewrite(self, request: RewriteRequest) -> RewriteResult:
        rewritten = [f"Rewrite for retrieval: {request.query}"]
        intent = self._detect_intent(request.query)
        return RewriteResult(rewritten_queries=rewritten, intent=intent, strategy="llm")

    def _multi_query_rewrite(self, request: RewriteRequest) -> RewriteResult:
        terms = re.findall(r"\w+", request.query.lower())
        rewritten = [request.query]
        if len(terms) > 1:
            rewritten.append(" ".join(terms[:2]))
            rewritten.append(" ".join(terms[-2:]))
        intent = self._detect_intent(request.query)
        return RewriteResult(rewritten_queries=rewritten[: request.max_queries], intent=intent, strategy="multi-query")

    def _intent_rewrite(self, request: RewriteRequest) -> RewriteResult:
        intent = request.intent or self._detect_intent(request.query)
        rewritten = [f"Find information about {intent} related to {request.query}"]
        return RewriteResult(rewritten_queries=rewritten, intent=intent, strategy="intent")

    def _conversation_rewrite(self, request: RewriteRequest) -> RewriteResult:
        history = " ".join(request.conversation_history or [])
        rewritten = [f"{history} {request.query}".strip()]
        intent = self._detect_intent(request.query)
        return RewriteResult(rewritten_queries=rewritten, intent=intent, strategy="conversation")

    def _detect_intent(self, query: str) -> str:
        lowered = query.lower()
        if any(term in lowered for term in ["how", "why", "explain", "what is", "what are"]):
            return "explanatory"
        if any(term in lowered for term in ["compare", "difference", "versus"]):
            return "comparative"
        if any(term in lowered for term in ["summarize", "overview"]):
            return "summarization"
        return "informational"


class QueryRewritingEvaluator:
    def evaluate(self, original_query: str, rewritten_queries: list[str]) -> dict[str, Any]:
        return {
            "original_query": original_query,
            "rewritten_queries": rewritten_queries,
            "query_count": len(rewritten_queries),
            "average_length": sum(len(query.split()) for query in rewritten_queries) / max(1, len(rewritten_queries)),
        }
