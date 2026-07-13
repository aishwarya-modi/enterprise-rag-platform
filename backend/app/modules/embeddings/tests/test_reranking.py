from app.modules.embeddings.reranking import ConfigurableReranker, CohereReranker, CrossEncoderReranker, RerankRequest, RerankingService


def test_rerankers_reduce_candidates_to_top_k() -> None:
    request = RerankRequest(
        query="alpha",
        documents=[
            {"id": "doc-1", "payload": {"text": "alpha beta gamma"}},
            {"id": "doc-2", "payload": {"text": "delta epsilon"}},
            {"id": "doc-3", "payload": {"text": "alpha"}},
        ],
        top_k=2,
    )

    results = CohereReranker().rerank(request)

    assert len(results) == 2
    assert results[0].id == "doc-1"


def test_configurable_reranker_switches_provider() -> None:
    request = RerankRequest(query="alpha", documents=[{"id": "doc-1", "payload": {"text": "alpha"}}], top_k=1)
    reranker = ConfigurableReranker(provider="cross-encoder")

    results = reranker.rerank(request)

    assert results[0].id == "doc-1"


def test_reranking_service_reports_latency() -> None:
    service = RerankingService(reranker=CohereReranker())
    results, latency_ms = service.rerank(RerankRequest(query="alpha", documents=[{"id": "doc-1", "payload": {"text": "alpha"}}], top_k=1))

    assert len(results) == 1
    assert latency_ms >= 0
