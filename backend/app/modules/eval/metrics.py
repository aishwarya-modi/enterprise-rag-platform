from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

from app.modules.eval.schemas import EvaluationSample, MetricScore

logger = logging.getLogger(__name__)

ALL_METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall", "latency", "token_usage", "cost"]

COST_PER_1K_INPUT_TOKENS: dict[str, float] = {
    "gpt-4o": 0.0025,
    "gpt-4o-mini": 0.00015,
    "gpt-4-turbo": 0.01,
    "gpt-3.5-turbo": 0.0005,
    "claude-3-5-sonnet-20241022": 0.003,
    "claude-3-haiku-20240307": 0.00025,
}

COST_PER_1K_OUTPUT_TOKENS: dict[str, float] = {
    "gpt-4o": 0.01,
    "gpt-4o-mini": 0.0006,
    "gpt-4-turbo": 0.03,
    "gpt-3.5-turbo": 0.0015,
    "claude-3-5-sonnet-20241022": 0.015,
    "claude-3-haiku-20240307": 0.00125,
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    input_rate = COST_PER_1K_INPUT_TOKENS.get(model, 0.003)
    output_rate = COST_PER_1K_OUTPUT_TOKENS.get(model, 0.015)
    return (prompt_tokens / 1000.0 * input_rate) + (completion_tokens / 1000.0 * output_rate)


def _get_ragas_llm(provider: str, model: str):
    from ragas.llms import LangchainLLMWrapper

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        from app.core.config import get_settings
        settings = get_settings()
        api_key = settings.openai_api_key or "sk-fake"
        llm = ChatOpenAI(model=model, api_key=api_key, temperature=0)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        from app.core.config import get_settings
        settings = get_settings()
        api_key = settings.anthropic_api_key or "sk-ant-fake"
        llm = ChatAnthropic(model=model, api_key=api_key, temperature=0)
    else:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=model, api_key="sk-fake", temperature=0)
    return LangchainLLMWrapper(llm)


def _get_ragas_embeddings():
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_openai import OpenAIEmbeddings
    from app.core.config import get_settings
    settings = get_settings()
    api_key = settings.openai_api_key or "sk-fake"
    return LangchainEmbeddingsWrapper(OpenAIEmbeddings(api_key=api_key))


def _build_dataset(samples: list[EvaluationSample]):
    from ragas.dataset_schema import EvaluationDataset, SingleTurnSample

    rows = []
    for s in samples:
        row = {
            "user_input": s.query,
            "response": s.answer,
            "retrieved_contexts": s.contexts,
        }
        if s.reference:
            row["reference"] = s.reference
        if s.reference_contexts:
            row["reference_contexts"] = s.reference_contexts
        rows.append(SingleTurnSample(**row))
    return EvaluationDataset(samples=rows)


async def run_ragas_metrics(
    samples: list[EvaluationSample],
    metrics: list[str],
    provider: str = "openai",
    model: str = "gpt-4o-mini",
) -> dict[int, list[MetricScore]]:
    from ragas.metrics.collections import Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall

    ragas_llm = _get_ragas_llm(provider, model)
    ragas_embeddings = _get_ragas_embeddings()

    metric_instances = []
    if "faithfulness" in metrics:
        metric_instances.append(Faithfulness(llm=ragas_llm))
    if "answer_relevancy" in metrics:
        metric_instances.append(AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings))
    if "context_precision" in metrics:
        metric_instances.append(ContextPrecision(llm=ragas_llm))
    if "context_recall" in metrics:
        metric_instances.append(ContextRecall(llm=ragas_llm))

    if not metric_instances:
        return {i: [] for i in range(len(samples))}

    dataset = _build_dataset(samples)

    from ragas import evaluate
    try:
        result = evaluate(
            dataset=dataset,
            metrics=metric_instances,
            show_progress=False,
            raise_exceptions=False,
        )
    except Exception as e:
        logger.warning("Ragas evaluate failed: %s — falling back to per-sample scoring", e)
        return await _fallback_ragas_scoring(samples, metric_instances)

    per_sample: dict[int, list[MetricScore]] = {i: [] for i in range(len(samples))}

    if hasattr(result, "to_pandas"):
        df = result.to_pandas()
        for idx in range(len(df)):
            row = df.iloc[idx]
            for metric_inst in metric_instances:
                name = metric_inst.name
                val = row.get(name)
                score_val = float(val) if val is not None and str(val) != "nan" else None
                per_sample[idx].append(MetricScore(name=name, score=score_val))
    elif hasattr(result, "scores") and isinstance(result.scores, dict):
        for metric_name, scores_list in result.scores.items():
            for idx, val in enumerate(scores_list):
                score_val = float(val) if val is not None else None
                per_sample.setdefault(idx, []).append(MetricScore(name=metric_name, score=score_val))

    return per_sample


async def _fallback_ragas_scoring(
    samples: list[EvaluationSample],
    metric_instances: list,
) -> dict[int, list[MetricScore]]:
    per_sample: dict[int, list[MetricScore]] = {i: [] for i in range(len(samples))}
    for idx, sample in enumerate(samples):
        for metric_inst in metric_instances:
            try:
                score = await metric_inst.ascore(
                    user_input=sample.query,
                    response=sample.answer,
                    retrieved_contexts=sample.contexts,
                )
                score_val = float(score) if score is not None else None
                per_sample[idx].append(MetricScore(name=metric_inst.name, score=score_val))
            except Exception as e:
                logger.warning("Metric %s failed for sample %d: %s", metric_inst.name, idx, e)
                per_sample[idx].append(MetricScore(name=metric_inst.name, score=None, reason=str(e)))
    return per_sample


def measure_latency(func):
    import asyncio
    import functools

    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            return result, elapsed_ms
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            return result, elapsed_ms
        return sync_wrapper


def compute_token_usage_from_text(text: str, model: str = "gpt-4o-mini") -> int:
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        return len(text.split()) * 4 // 3


def compute_operational_metrics(
    sample: EvaluationSample,
    latency_ms: float,
    model: str = "gpt-4o-mini",
) -> tuple[int, int, float]:
    prompt_tokens = compute_token_usage_from_text(sample.query + "\n".join(sample.contexts), model)
    completion_tokens = compute_token_usage_from_text(sample.answer, model)
    total = prompt_tokens + completion_tokens
    cost = estimate_cost(model, prompt_tokens, completion_tokens)
    return prompt_tokens, completion_tokens, cost
