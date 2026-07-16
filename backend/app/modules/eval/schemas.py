from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class EvaluationSample(BaseModel):
    query: str = Field(description="User query")
    answer: str = Field(description="Generated answer")
    contexts: list[str] = Field(description="Retrieved context strings")
    reference: Optional[str] = Field(default=None, description="Ground truth answer")
    reference_contexts: Optional[list[str]] = Field(default=None, description="Ground truth contexts")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional metadata (tenant_id, model, etc.)")


class EvaluationInput(BaseModel):
    samples: list[EvaluationSample] = Field(..., min_length=1, description="Samples to evaluate")
    metrics: Optional[list[str]] = Field(default=None, description="Specific metrics to run, or all if empty")
    provider: str = Field(default="openai", description="LLM provider for Ragas judges")
    model: str = Field(default="gpt-4o-mini", description="Model for Ragas judges")
    run_id: Optional[str] = Field(default=None, description="Optional run identifier")


class MetricScore(BaseModel):
    name: str
    score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    reason: Optional[str] = None


class SampleResult(BaseModel):
    sample_index: int
    query: str
    answer: str
    metric_scores: list[MetricScore]
    latency_ms: Optional[float] = None
    token_usage: Optional[TokenUsage] = None
    cost_usd: Optional[float] = None


class EvaluationResult(BaseModel):
    run_id: str
    status: Literal["running", "completed", "failed"] = "running"
    sample_results: list[SampleResult] = Field(default_factory=list)
    aggregate_scores: dict[str, Optional[float]] = Field(default_factory=dict)
    total_latency_ms: float = 0.0
    total_tokens: TokenUsage = Field(default_factory=TokenUsage)
    total_cost_usd: float = 0.0
    sample_count: int = 0
    error: Optional[str] = None


class ReportRequest(BaseModel):
    run_id: str = Field(description="Evaluation run ID to generate report for")
    title: Optional[str] = Field(default=None, description="Report title")


class ReportResponse(BaseModel):
    run_id: str
    html: str
    filename: str
