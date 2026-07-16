from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Optional

from app.modules.eval.metrics import (
    ALL_METRICS,
    compute_operational_metrics,
    run_ragas_metrics,
)
from app.modules.eval.schemas import (
    EvaluationInput,
    EvaluationResult,
    MetricScore,
    SampleResult,
    TokenUsage,
)

logger = logging.getLogger(__name__)

_runs: dict[str, EvaluationResult] = {}


def get_run(run_id: str) -> Optional[EvaluationResult]:
    return _runs.get(run_id)


def list_runs() -> list[EvaluationResult]:
    return list(_runs.values())


async def run_evaluation(input_data: EvaluationInput) -> EvaluationResult:
    run_id = input_data.run_id or str(uuid.uuid4())
    requested_metrics = input_data.metrics or list(ALL_METRICS)

    result = EvaluationResult(
        run_id=run_id,
        status="running",
        sample_count=len(input_data.samples),
    )
    _runs[run_id] = result

    total_start = time.perf_counter()

    try:
        ragas_metric_names = [m for m in requested_metrics if m in ("faithfulness", "answer_relevancy", "context_precision", "context_recall")]
        ragas_scores = {}
        if ragas_metric_names:
            try:
                ragas_scores = await run_ragas_metrics(
                    samples=input_data.samples,
                    metrics=ragas_metric_names,
                    provider=input_data.provider,
                    model=input_data.model,
                )
            except Exception as e:
                logger.warning("Ragas scoring failed: %s — proceeding with operational metrics only", e)

        total_prompt = 0
        total_completion = 0
        total_cost = 0.0
        total_latency = 0.0
        all_sample_results: list[SampleResult] = []

        for idx, sample in enumerate(input_data.samples):
            sample_start = time.perf_counter()
            latency_ms = (time.perf_counter() - sample_start) * 1000

            metric_scores: list[MetricScore] = list(ragas_scores.get(idx, []))

            if "latency" in requested_metrics:
                metric_scores.append(MetricScore(name="latency", score=None, reason=f"{latency_ms:.1f}ms"))

            prompt_toks, completion_toks, cost = compute_operational_metrics(sample, latency_ms, input_data.model)
            total_prompt += prompt_toks
            total_completion += completion_toks
            total_cost += cost
            total_latency += latency_ms

            token_usage = TokenUsage(prompt_tokens=prompt_toks, completion_tokens=completion_toks, total_tokens=prompt_toks + completion_toks)

            if "token_usage" in requested_metrics:
                metric_scores.append(MetricScore(name="token_usage", score=None, reason=f"{token_usage.total_tokens} tokens"))

            if "cost" in requested_metrics:
                metric_scores.append(MetricScore(name="cost", score=None, reason=f"${cost:.6f}"))

            all_sample_results.append(SampleResult(
                sample_index=idx,
                query=sample.query,
                answer=sample.answer,
                metric_scores=metric_scores,
                latency_ms=latency_ms,
                token_usage=token_usage,
                cost_usd=cost,
            ))

        aggregate_scores: dict[str, Optional[float]] = {}
        for metric_name in ragas_metric_names:
            scores_for_metric = [
                ms.score for sr in all_sample_results
                for ms in sr.metric_scores
                if ms.name == metric_name and ms.score is not None
            ]
            if scores_for_metric:
                aggregate_scores[metric_name] = sum(scores_for_metric) / len(scores_for_metric)
            else:
                aggregate_scores[metric_name] = None

        result.sample_results = all_sample_results
        result.aggregate_scores = aggregate_scores
        result.total_latency_ms = total_latency
        result.total_tokens = TokenUsage(prompt_tokens=total_prompt, completion_tokens=total_completion, total_tokens=total_prompt + total_completion)
        result.total_cost_usd = total_cost
        result.status = "completed"

    except Exception as e:
        logger.error("Evaluation run %s failed: %s", run_id, e)
        result.status = "failed"
        result.error = str(e)

    result.total_latency_ms = (time.perf_counter() - total_start) * 1000
    return result
