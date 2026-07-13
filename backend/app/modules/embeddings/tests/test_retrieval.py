from app.modules.embeddings.retrieval import RetrievalPipeline, RetrievalRequest


class FakeStore:
    def __init__(self) -> None:
        self.namespaces = {
            "default": {
                "doc-1": {"id": "doc-1", "deleted": False, "payload": {"text": "alpha beta", "category": "news", "date": "2024-01-01"}},
                "doc-2": {"id": "doc-2", "deleted": False, "payload": {"text": "beta gamma", "category": "blog", "date": "2024-02-01"}},
                "doc-3": {"id": "doc-3", "deleted": True, "payload": {"text": "alpha", "category": "news", "date": "2024-03-01"}},
            }
        }


def test_dense_and_bm25_retrieval_return_ranked_results() -> None:
    pipeline = RetrievalPipeline(FakeStore())

    dense = pipeline.dense_retrieval(RetrievalRequest(query="alpha", top_k=2))
    bm25 = pipeline.bm25_retrieval(RetrievalRequest(query="beta", top_k=2))

    assert dense[0].id == "doc-1"
    assert bm25[0].id == "doc-1"


def test_hybrid_retrieval_applies_filters_and_normalization() -> None:
    pipeline = RetrievalPipeline(FakeStore())

    request = RetrievalRequest(query="alpha", top_k=2, metadata_filter={"category": "news"}, date_filter={"from": "2024-01-01", "to": "2024-02-01"})
    results = pipeline.hybrid_retrieval(request)

    assert results
    assert all(result.id == "doc-1" for result in results)


def test_namespace_and_document_filters_are_respected() -> None:
    pipeline = RetrievalPipeline(FakeStore())

    request = RetrievalRequest(query="beta", top_k=5, namespace="default", document_ids=["doc-2"])
    results = pipeline.retrieve(request)

    assert [result.id for result in results] == ["doc-2"]
