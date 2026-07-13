from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class RetrievalRequest:
    query: str
    top_k: int = 5
    dense_weight: float = 0.6
    bm25_weight: float = 0.4
    namespace: str | None = None
    document_ids: list[str] | None = None
    metadata_filter: dict[str, Any] | None = None
    date_filter: dict[str, Any] | None = None
    score_mode: str = "hybrid"


@dataclass(slots=True)
class RetrievalResult:
    id: str
    score: float
    payload: dict[str, Any]


class RetrievalPipeline:
    def __init__(self, store: Any) -> None:
        self._store = store

    def dense_retrieval(self, request: RetrievalRequest) -> list[RetrievalResult]:
        documents = self._filter_documents(request)
        scored = []
        for document in documents:
            score = self._dense_score(request.query, str(document.get("payload", {}).get("text", "")))
            scored.append((score, document))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [RetrievalResult(id=item[1]["id"], score=item[0], payload=item[1].get("payload", {})) for item in scored[: request.top_k]]

    def bm25_retrieval(self, request: RetrievalRequest) -> list[RetrievalResult]:
        documents = self._filter_documents(request)
        corpus = [str(document.get("payload", {}).get("text", "")) for document in documents]
        scores = self._bm25_scores(request.query, corpus)
        ranked = sorted(zip(scores, documents), key=lambda item: item[0], reverse=True)
        return [RetrievalResult(id=item[1]["id"], score=item[0], payload=item[1].get("payload", {})) for item in ranked[: request.top_k]]

    def hybrid_retrieval(self, request: RetrievalRequest) -> list[RetrievalResult]:
        dense_results = self.dense_retrieval(request)
        bm25_results = self.bm25_retrieval(request)
        combined: dict[str, RetrievalResult] = {}
        for result in dense_results:
            combined[result.id] = result
        for result in bm25_results:
            existing = combined.get(result.id)
            if existing is None:
                combined[result.id] = result
            else:
                combined[result.id] = RetrievalResult(
                    id=result.id,
                    score=(request.dense_weight * existing.score) + (request.bm25_weight * result.score),
                    payload=result.payload,
                )
        ranked = sorted(combined.values(), key=lambda item: item.score, reverse=True)
        return ranked[: request.top_k]

    def retrieve(self, request: RetrievalRequest) -> list[RetrievalResult]:
        if request.score_mode == "dense":
            return self.dense_retrieval(request)
        if request.score_mode == "bm25":
            return self.bm25_retrieval(request)
        return self.hybrid_retrieval(request)

    def _filter_documents(self, request: RetrievalRequest) -> list[dict[str, Any]]:
        documents = []
        for namespace_name, items in getattr(self._store, "namespaces", {}).items():
            if request.namespace and namespace_name != request.namespace:
                continue
            for item in items.values() if isinstance(items, dict) else items:
                if item.get("deleted"):
                    continue
                payload = item.get("payload", {})
                if request.document_ids and item.get("id") not in request.document_ids:
                    continue
                if request.metadata_filter and any(payload.get(key) != value for key, value in request.metadata_filter.items()):
                    continue
                if request.date_filter:
                    doc_date = payload.get("date")
                    if doc_date is None:
                        continue
                    if request.date_filter.get("from") and doc_date < request.date_filter["from"]:
                        continue
                    if request.date_filter.get("to") and doc_date > request.date_filter["to"]:
                        continue
                documents.append(item)
        return documents

    def _dense_score(self, query: str, text: str) -> float:
        query_terms = set(re.findall(r"\w+", query.lower()))
        text_terms = set(re.findall(r"\w+", text.lower()))
        if not query_terms or not text_terms:
            return 0.0
        overlap = len(query_terms & text_terms)
        return overlap / max(len(query_terms | text_terms), 1)

    def _bm25_scores(self, query: str, corpus: list[str]) -> list[float]:
        query_terms = re.findall(r"\w+", query.lower())
        if not query_terms:
            return [0.0 for _ in corpus]
        doc_freq = Counter(term for doc in corpus for term in set(re.findall(r"\w+", doc.lower())))
        scores = []
        for doc in corpus:
            doc_terms = re.findall(r"\w+", doc.lower())
            doc_freq_counter = Counter(doc_terms)
            score = 0.0
            for term in query_terms:
                if term not in doc_freq_counter:
                    continue
                tf = doc_freq_counter[term]
                idf = math.log((1 + len(corpus)) / (1 + doc_freq[term])) + 1.0
                score += tf * idf
            scores.append(score)
        return scores
