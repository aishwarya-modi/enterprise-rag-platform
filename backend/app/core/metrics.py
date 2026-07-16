from __future__ import annotations

import time
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram, Info, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

ACTIVE_REQUESTS = Gauge(
    "http_active_requests",
    "Number of in-flight requests",
)

RAG_QUERY_COUNT = Counter(
    "rag_queries_total",
    "Total RAG queries processed",
    ["provider", "model", "status"],
)

RAG_LATENCY = Histogram(
    "rag_query_duration_seconds",
    "RAG query end-to-end latency",
    ["provider", "model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

RAG_DOCUMENTS_RETRIEVED = Histogram(
    "rag_documents_retrieved",
    "Number of documents retrieved per query",
    buckets=[0, 1, 2, 5, 10, 20, 50],
)

LLM_CALL_COUNT = Counter(
    "llm_calls_total",
    "Total LLM API calls",
    ["provider", "model", "cached"],
)

LLM_LATENCY = Histogram(
    "llm_call_duration_seconds",
    "LLM API call latency",
    ["provider", "model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

CACHE_OPERATIONS = Counter(
    "cache_operations_total",
    "Cache operations",
    ["namespace", "operation", "hit"],
)

EVAL_RUN_COUNT = Counter(
    "evaluation_runs_total",
    "Total evaluation runs completed",
    ["status"],
)

APP_INFO = Info(
    "app",
    "Application metadata",
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    _skip_paths = frozenset({"/metrics", "/health", "/ready", "/health/live", "/health/ready"})

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self._skip_paths:
            return await call_next(request)

        ACTIVE_REQUESTS.inc()
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code="500",
            ).inc()
            raise
        finally:
            ACTIVE_REQUESTS.dec()

        elapsed = time.perf_counter() - start
        endpoint = _normalize_path(request.url.path)

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=str(response.status_code),
        ).inc()

        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(elapsed)

        return response


def _normalize_path(path: str) -> str:
    parts = path.strip("/").split("/")
    prefix_parts: list[str] = []
    resource_count = 0
    result: list[str] = []

    for part in parts:
        if part in ("api", "v1", "v2"):
            prefix_parts.append(part)
            result.append(part)
        elif resource_count < 2:
            result.append(part)
            resource_count += 1
        else:
            result.append("{id}")

    if not result:
        return path
    return "/" + "/".join(result)


def get_metrics_text() -> bytes:
    return generate_latest()


def init_app_info(version: str = "0.1.0", environment: str = "development") -> None:
    APP_INFO.info({"version": version, "environment": environment})
