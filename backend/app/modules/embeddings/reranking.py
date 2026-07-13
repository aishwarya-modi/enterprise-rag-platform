from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class RerankRequest:
    query: str
    documents: list[dict[str, Any]]
    top_k: int = 10
    provider: str = "cohere"
    model: str | None = None


@dataclass(slots=True)
class RerankResult:
    id: str
    score: float
    payload: dict[str, Any]


class Reranker(ABC):
    @abstractmethod
    def rerank(self, request: RerankRequest) -> list[RerankResult]:
        raise NotImplementedError


class CohereReranker(Reranker):
    def rerank(self, request: RerankRequest) -> list[RerankResult]:
        scored = []
        for document in request.documents:
            score = self._score(request.query, str(document.get("payload", {}).get("text", "")))
            scored.append((score, document))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [RerankResult(id=item[1]["id"], score=item[0], payload=item[1].get("payload", {})) for item in scored[: request.top_k]]

    def _score(self, query: str, document: str) -> float:
        return float(sum(token in document.lower() for token in query.lower().split()))


class CrossEncoderReranker(Reranker):
    def rerank(self, request: RerankRequest) -> list[RerankResult]:
        scored = []
        for document in request.documents:
            score = self._score(request.query, str(document.get("payload", {}).get("text", "")))
            scored.append((score, document))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [RerankResult(id=item[1]["id"], score=item[0], payload=item[1].get("payload", {})) for item in scored[: request.top_k]]

    def _score(self, query: str, document: str) -> float:
        return float(len(set(query.lower().split()) & set(document.lower().split())))


class BGEReranker(Reranker):
    def rerank(self, request: RerankRequest) -> list[RerankResult]:
        scored = []
        for document in request.documents:
            score = self._score(request.query, str(document.get("payload", {}).get("text", "")))
            scored.append((score, document))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [RerankResult(id=item[1]["id"], score=item[0], payload=item[1].get("payload", {})) for item in scored[: request.top_k]]

    def _score(self, query: str, document: str) -> float:
        return float(sum(token in document.lower() for token in query.lower().split()) / max(1, len(query.lower().split())))


class LateInteractionReranker(Reranker):
    def rerank(self, request: RerankRequest) -> list[RerankResult]:
        scored = []
        for document in request.documents:
            score = self._score(request.query, str(document.get("payload", {}).get("text", "")))
            scored.append((score, document))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [RerankResult(id=item[1]["id"], score=item[0], payload=item[1].get("payload", {})) for item in scored[: request.top_k]]

    def _score(self, query: str, document: str) -> float:
        query_terms = query.lower().split()
        doc_terms = document.lower().split()
        return float(sum(1 for term in query_terms if term in doc_terms) / max(1, len(query_terms)))


class RerankingService:
    def __init__(self, reranker: Reranker | None = None) -> None:
        self._reranker = reranker or CohereReranker()

    def rerank(self, request: RerankRequest) -> list[RerankResult]:
        start = time.perf_counter()
        results = self._reranker.rerank(request)
        latency_ms = (time.perf_counter() - start) * 1000
        return [RerankResult(id=result.id, score=result.score, payload=result.payload) for result in results], latency_ms

    def set_reranker(self, reranker: Reranker) -> None:
        self._reranker = reranker


class ConfigurableReranker(Reranker):
    def __init__(self, provider: str = "cohere") -> None:
        self.provider = provider

    def rerank(self, request: RerankRequest) -> list[RerankResult]:
        provider_map = {
            "cohere": CohereReranker(),
            "cross-encoder": CrossEncoderReranker(),
            "bge": BGEReranker(),
            "late-interaction": LateInteractionReranker(),
        }
        if self.provider not in provider_map:
            raise ValueError(f"Unsupported reranker provider: {self.provider}")
        return provider_map[self.provider].rerank(request)
