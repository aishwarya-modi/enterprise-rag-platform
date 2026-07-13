import pytest

from app.modules.embeddings.service import QdrantStore


def test_qdrant_store_supports_collections_namespaces_soft_delete_and_filtering() -> None:
    store = QdrantStore(url="http://localhost:6333", collection_name="demo")
    store.create_collection("articles", vector_size=3)

    store.upsert_vectors(
        [
            {"id": "doc-1", "vector": [0.1, 0.2, 0.3], "payload": {"category": "news", "tenant": "a"}},
            {"id": "doc-2", "vector": [0.4, 0.5, 0.6], "payload": {"category": "blog", "tenant": "a"}},
        ],
        collection_name="articles",
        namespace="tenant-a",
    )

    store.soft_delete("doc-1", collection_name="articles", namespace="tenant-a")

    results = store.search(
        collection_name="articles",
        query_vector=[0.1, 0.2, 0.3],
        namespace="tenant-a",
        filter={"category": "news"},
        limit=5,
    )

    assert "articles" in store.list_collections()
    assert "tenant-a" in store.list_namespaces("articles")
    assert results == []


def test_qdrant_store_supports_versioning_and_batch_upserts() -> None:
    store = QdrantStore(url="http://localhost:6333", collection_name="demo")
    store.create_collection("versions", vector_size=3)

    store.batch_insert(
        [
            {"id": "doc-9", "vector": [0.1, 0.1, 0.1], "payload": {"status": "draft"}},
        ],
        collection_name="versions",
    )

    store.upsert_vectors(
        [{"id": "doc-9", "vector": [0.2, 0.2, 0.2], "payload": {"status": "published"}}],
        collection_name="versions",
    )

    item = store.get_vector("doc-9", collection_name="versions")
    assert item is not None
    assert item["version"] == 2
    assert item["payload"]["status"] == "published"


def test_qdrant_store_can_migrate_collections() -> None:
    store = QdrantStore(url="http://localhost:6333", collection_name="demo")
    store.create_collection("source", vector_size=2)
    store.upsert_vectors(
        [{"id": "doc-x", "vector": [0.5, 0.6], "payload": {"source": "migration"}}],
        collection_name="source",
    )

    store.migrate_collection("source", "archive")

    assert "archive" in store.list_collections()
    assert store.get_vector("doc-x", collection_name="archive") is not None
