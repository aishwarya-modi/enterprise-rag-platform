from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.eval.metrics import (
    ALL_METRICS,
    compute_operational_metrics,
    compute_token_usage_from_text,
    estimate_cost,
)
from app.modules.eval.report import generate_html_report
from app.modules.eval.runner import get_run, list_runs, run_evaluation
from app.modules.eval.schemas import (
    EvaluationInput,
    EvaluationResult,
    EvaluationSample,
    MetricScore,
    SampleResult,
    TokenUsage,
)

client = TestClient(app)


SAMPLES = [
    EvaluationSample(
        query="What is the capital of France?",
        answer="The capital of France is Paris.",
        contexts=["France is a country in Europe. Its capital city is Paris."],
        reference="Paris",
        reference_contexts=["France is a country in Europe. Its capital city is Paris."],
    ),
    EvaluationSample(
        query="What is the population of Tokyo?",
        answer="Tokyo has approximately 14 million people.",
        contexts=["Tokyo is the capital of Japan with a population of about 14 million."],
        reference="About 14 million",
    ),
]


def test_estimate_cost():
    cost = estimate_cost("gpt-4o-mini", 1000, 500)
    assert cost > 0
    assert cost < 0.01


def test_estimate_cost_unknown_model():
    cost = estimate_cost("unknown-model", 1000, 1000)
    assert cost > 0


def test_compute_token_usage_from_text():
    tokens = compute_token_usage_from_text("Hello world, this is a test.", "gpt-4o-mini")
    assert tokens > 0
    assert isinstance(tokens, int)


def test_compute_operational_metrics():
    sample = SAMPLES[0]
    prompt_toks, completion_toks, cost = compute_operational_metrics(sample, 100.0, "gpt-4o-mini")
    assert prompt_toks > 0
    assert completion_toks > 0
    assert cost > 0


def test_schemas_evaluation_input():
    inp = EvaluationInput(samples=SAMPLES)
    assert len(inp.samples) == 2
    assert inp.provider == "openai"
    assert inp.model == "gpt-4o-mini"


def test_schemas_evaluation_result():
    result = EvaluationResult(run_id="test-123", status="completed", sample_count=2)
    assert result.run_id == "test-123"
    assert result.status == "completed"
    assert result.sample_count == 2


def test_schemas_metric_score():
    ms = MetricScore(name="faithfulness", score=0.85, reason="Good")
    assert ms.score == 0.85
    assert ms.name == "faithfulness"


def test_schemas_metric_score_none():
    ms = MetricScore(name="latency", score=None, reason="120ms")
    assert ms.score is None


def test_schemas_token_usage():
    tu = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
    assert tu.total_tokens == 150


class TestReportGeneration:
    def test_report_html_structure(self):
        result = EvaluationResult(
            run_id="report-test-123",
            status="completed",
            sample_count=2,
            aggregate_scores={"faithfulness": 0.85, "answer_relevancy": 0.72, "context_precision": 0.91, "context_recall": 0.68},
            total_latency_ms=450.0,
            total_tokens=TokenUsage(prompt_tokens=500, completion_tokens=200, total_tokens=700),
            total_cost_usd=0.00123,
            sample_results=[
                SampleResult(
                    sample_index=0,
                    query="What is the capital of France?",
                    answer="The capital of France is Paris.",
                    metric_scores=[
                        MetricScore(name="faithfulness", score=0.9),
                        MetricScore(name="latency", reason="120ms"),
                    ],
                    latency_ms=120.0,
                    token_usage=TokenUsage(prompt_tokens=200, completion_tokens=50, total_tokens=250),
                    cost_usd=0.0005,
                ),
                SampleResult(
                    sample_index=1,
                    query="Population of Tokyo?",
                    answer="Tokyo has 14 million people.",
                    metric_scores=[
                        MetricScore(name="faithfulness", score=0.8),
                        MetricScore(name="token_usage", reason="300 tokens"),
                    ],
                    latency_ms=200.0,
                    token_usage=TokenUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300),
                    cost_usd=0.0007,
                ),
            ],
        )
        html_content = generate_html_report(result, title="Test Report")

        assert "<!DOCTYPE html>" in html_content
        assert "Test Report" in html_content
        assert "report-test-123" in html_content
        assert "faithfulness" in html_content
        assert "answer_relevancy" in html_content
        assert "0.850" in html_content
        assert "COMPLETED" in html_content
        assert "Samples" in html_content
        assert "Total Tokens" in html_content
        assert "Total Cost" in html_content
        assert "Aggregate" in html_content

    def test_report_with_no_ragas_scores(self):
        result = EvaluationResult(
            run_id="no-ragas-123",
            status="completed",
            sample_count=1,
            total_latency_ms=50.0,
            total_tokens=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            total_cost_usd=0.0001,
            sample_results=[],
        )
        html_content = generate_html_report(result)
        assert "no-ragas-123" in html_content
        assert "COMPLETED" in html_content


class TestRunner:
    def test_get_run_returns_none(self):
        assert get_run("nonexistent-id") is None

    def test_list_runs_empty(self):
        runs = list_runs()
        assert isinstance(runs, list)

    @patch("app.modules.eval.runner.run_ragas_metrics", new_callable=AsyncMock)
    def test_run_evaluation_with_mock(self, mock_ragas):
        mock_ragas.return_value = {
            0: [MetricScore(name="faithfulness", score=0.9), MetricScore(name="answer_relevancy", score=0.8)],
            1: [MetricScore(name="faithfulness", score=0.7), MetricScore(name="answer_relevancy", score=0.75)],
        }

        inp = EvaluationInput(
            samples=SAMPLES,
            metrics=["faithfulness", "answer_relevancy"],
            provider="openai",
            model="gpt-4o-mini",
        )
        result = asyncio.run(run_evaluation(inp))

        assert result.status == "completed"
        assert result.sample_count == 2
        assert len(result.sample_results) == 2
        assert "faithfulness" in result.aggregate_scores
        assert result.aggregate_scores["faithfulness"] == pytest.approx(0.8, abs=0.01)
        assert result.total_tokens.total_tokens > 0
        assert result.total_cost_usd > 0

    @patch("app.modules.eval.runner.run_ragas_metrics", new_callable=AsyncMock)
    def test_run_evaluation_all_metrics(self, mock_ragas):
        mock_ragas.return_value = {
            0: [MetricScore(name="faithfulness", score=0.85)],
        }

        inp = EvaluationInput(samples=SAMPLES[:1])
        result = asyncio.run(run_evaluation(inp))

        assert result.status == "completed"
        assert result.sample_count == 1
        assert len(result.sample_results) == 1
        sample = result.sample_results[0]
        metric_names = [ms.name for ms in sample.metric_scores]
        assert "latency" in metric_names
        assert "token_usage" in metric_names
        assert "cost" in metric_names


class TestAPI:
    @patch("app.modules.eval.runner.run_ragas_metrics", new_callable=AsyncMock)
    def test_eval_run_returns_200(self, mock_ragas):
        mock_ragas.return_value = {
            0: [MetricScore(name="faithfulness", score=0.9)],
        }
        response = client.post("/api/v1/eval/run", json={
            "samples": [
                {"query": "test?", "answer": "test answer", "contexts": ["context"]},
            ],
            "metrics": ["faithfulness"],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["sample_count"] == 1
        assert "run_id" in data

    def test_eval_run_empty_samples_returns_422(self):
        response = client.post("/api/v1/eval/run", json={"samples": []})
        assert response.status_code == 422

    def test_eval_runs_list_returns_200(self):
        response = client.get("/api/v1/eval/runs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_eval_run_not_found_returns_404(self):
        response = client.get("/api/v1/eval/runs/nonexistent-id")
        assert response.status_code == 404

    @patch("app.modules.eval.runner.run_ragas_metrics", new_callable=AsyncMock)
    def test_report_endpoint(self, mock_ragas):
        mock_ragas.return_value = {
            0: [MetricScore(name="faithfulness", score=0.9)],
        }
        run_resp = client.post("/api/v1/eval/run", json={
            "samples": [{"query": "q", "answer": "a", "contexts": ["c"]}],
            "metrics": ["faithfulness"],
        })
        run_id = run_resp.json()["run_id"]

        report_resp = client.post("/api/v1/eval/report", json={"run_id": run_id, "title": "My Report"})
        assert report_resp.status_code == 200
        report_data = report_resp.json()
        assert "html" in report_data
        assert "My Report" in report_data["html"]
        assert report_data["filename"].endswith(".html")

    @patch("app.modules.eval.runner.run_ragas_metrics", new_callable=AsyncMock)
    def test_report_html_endpoint(self, mock_ragas):
        mock_ragas.return_value = {
            0: [MetricScore(name="faithfulness", score=0.85)],
        }
        run_resp = client.post("/api/v1/eval/run", json={
            "samples": [{"query": "q", "answer": "a", "contexts": ["c"]}],
            "metrics": ["faithfulness"],
        })
        run_id = run_resp.json()["run_id"]

        html_resp = client.get(f"/api/v1/eval/report/{run_id}")
        assert html_resp.status_code == 200
        assert "<!DOCTYPE html>" in html_resp.text

    def test_report_not_found_returns_404(self):
        response = client.post("/api/v1/eval/report", json={"run_id": "nonexistent"})
        assert response.status_code == 404
