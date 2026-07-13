from __future__ import annotations

import time

from app.modules.embeddings.reranking import CohereReranker, CrossEncoderReranker, RerankRequest


def run_benchmark() -> None:
    request = RerankRequest(
        query="alpha",
        documents=[{"id": f"doc-{index}", "payload": {"text": "alpha beta gamma delta"}} for index in range(100)],
        top_k=10,
    )
    rerankers = [
        ("cohere", CohereReranker()),
        ("cross-encoder", CrossEncoderReranker()),
    ]
    for name, reranker in rerankers:
        start = time.perf_counter()
        reranker.rerank(request)
        latency_ms = (time.perf_counter() - start) * 1000
        print(f"{name}: latency_ms={latency_ms:.2f}")


if __name__ == "__main__":
    run_benchmark()
