from app.modules.embeddings.query_rewriting import QueryRewriter, QueryRewritingEvaluator, RewriteRequest


def test_hyde_and_step_back_rewrite_queries() -> None:
    rewriter = QueryRewriter()

    hyde = rewriter.rewrite(RewriteRequest(query="What is retrieval augmented generation?", strategy="hyde"))
    step_back = rewriter.rewrite(RewriteRequest(query="What is retrieval augmented generation?", strategy="step-back"))

    assert hyde.rewritten_queries
    assert step_back.rewritten_queries
    assert hyde.intent == "explanatory"


def test_multi_query_and_conversation_rewriting_generate_multiple_forms() -> None:
    rewriter = QueryRewriter()

    multi = rewriter.rewrite(RewriteRequest(query="Explain the difference between RAG and fine tuning", strategy="multi-query", max_queries=3))
    convo = rewriter.rewrite(RewriteRequest(query="and how does it work?", strategy="conversation", conversation_history=["We discussed RAG earlier"] ))

    assert len(multi.rewritten_queries) >= 2
    assert convo.rewritten_queries


def test_evaluator_reports_query_metrics() -> None:
    evaluator = QueryRewritingEvaluator()
    result = evaluator.evaluate("What is RAG?", ["What is retrieval augmented generation?", "Explain RAG"])

    assert result["query_count"] == 2
    assert result["average_length"] > 0
