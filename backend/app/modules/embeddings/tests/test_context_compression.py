from app.modules.embeddings.context_compression import ContextCompressionService


def test_context_compression_removes_duplicates_preserves_citations_and_honors_budget() -> None:
    service = ContextCompressionService()
    request = {
        "contexts": [
            {"text": "Revenue grew by 12% in the last quarter [1].", "citation": "[1]", "priority": 2.0},
            {"text": "Revenue grew by 12% in the last quarter [1].", "citation": "[1]", "priority": 2.0},
            {"text": "The launch date is set for November 15 [2].", "citation": "[2]", "priority": 1.5},
            {"text": "Customer churn improved after the new onboarding flow [3].", "citation": "[3]", "priority": 1.0},
        ],
        "strategy": "hybrid",
        "max_tokens": 40,
        "preserve_citations": True,
    }

    response = service.compress_context(request)

    assert response["compressed_context"]
    assert response["compressed_token_count"] <= response["original_token_count"]
    assert response["removed_items"] >= 1
    assert all(item["citation"] for item in response["compressed_context"])
    assert any("[1]" in item["citation"] for item in response["compressed_context"])
    assert any("[2]" in item["citation"] for item in response["compressed_context"])


def test_context_compression_llm_strategy_compacts_long_text() -> None:
    service = ContextCompressionService()
    request = {
        "contexts": [
            {"text": "The policy requires a detailed review of all vendor invoices before approval.", "citation": "[4]", "priority": 1.0},
            {"text": "The policy requires a detailed review of all vendor invoices before approval and also requires the finance team to confirm the invoices.", "citation": "[4]", "priority": 1.0},
        ],
        "strategy": "llm",
        "max_tokens": 20,
        "preserve_citations": True,
    }

    response = service.compress_context(request)

    assert response["compressed_context"]
    assert response["compressed_token_count"] <= 20
    assert response["compressed_context"][0]["text"].startswith("Policy")
