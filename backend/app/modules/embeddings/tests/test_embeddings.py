import pytest

from app.modules.embeddings.service import EmbeddingService, EmbeddingProvider, QdrantStore


class FakeProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self.calls = 0

    def embed_texts(self, texts: list[str], model: str | None = None, dimensions: int | None = None) -> list[list[float]]:
        self.calls += 1
        return [[float(len(text) % 10)] * (dimensions or 3) for text in texts]


class FailingThenWorkingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self.calls = 0

    def embed_texts(self, texts: list[str], model: str | None = None, dimensions: int | None = None) -> list[list[float]]:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary failure")
        return [[0.1, 0.2, 0.3] for _ in texts]


def test_embedding_service_validates_dimensions_and_batches() -> None:
    provider = FakeProvider()
    service = EmbeddingService(provider=provider, default_model="demo-model")

    response = service.embed_texts(["alpha", "beta", "gamma"], dimensions=4, batch_size=2)

    assert len(response.embeddings) == 3
    assert all(len(vector) == 4 for vector in response.embeddings)
    assert provider.calls == 2


def test_embedding_service_uses_cache_for_repeated_requests() -> None:
    provider = FakeProvider()
    service = EmbeddingService(provider=provider, default_model="demo-model")

    first = service.embed_texts(["shared text"], dimensions=3)
    second = service.embed_texts(["shared text"], dimensions=3)

    assert first.embeddings == second.embeddings
    assert provider.calls == 1


def test_embedding_service_retries_failed_provider_call() -> None:
    provider = FailingThenWorkingProvider()
    service = EmbeddingService(provider=provider, default_model="demo-model", max_retries=2, backoff_seconds=0)

    response = service.embed_texts(["hello"], dimensions=3)

    assert len(response.embeddings) == 1
    assert provider.calls == 2


def test_qdrant_store_fallback_upserts_and_queries_vectors() -> None:
    store = QdrantStore(url="http://localhost:6333", collection_name="test-collection")
    store.upsert_vectors([{"id": "doc-1", "vector": [0.1, 0.2], "payload": {"source": "unit-test"}}])

    result = store.query_vectors([0.1, 0.2], limit=1)

    assert result
    assert result[0]["id"] == "doc-1"


def test_embedding_service_enforces_rate_limit() -> None:
    provider = FakeProvider()
    service = EmbeddingService(provider=provider, default_model="demo-model", rate_limit_per_minute=1)

    service.embed_texts(["alpha"], dimensions=3)

    with pytest.raises(RuntimeError):
        service.embed_texts(["beta"], dimensions=3)
