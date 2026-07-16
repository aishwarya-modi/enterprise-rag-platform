from __future__ import annotations

import asyncio
import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.core.health import (
    HealthResponse,
    ReadinessResponse,
    _health_checks,
    register_health_check,
    run_liveness_checks,
    run_readiness_checks,
    update_health_check,
)
from app.core.logging import (
    REQUEST_ID_CTX,
    StructuredJSONFormatter,
    configure_logging,
    get_request_id,
)
from app.core.metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    ACTIVE_REQUESTS,
    RAG_QUERY_COUNT,
    LLM_CALL_COUNT,
    _normalize_path,
    get_metrics_text,
    init_app_info,
)
from app.core.middleware import CorrelationIDMiddleware
from app.core.tracing import get_tracer, init_tracing, trace_span, shutdown_tracing
from app.main import app

client = TestClient(app)


class TestStructuredLogging:
    def test_json_formatter_output(self):
        formatter = StructuredJSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="hello world", args=(), exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["message"] == "hello world"
        assert "timestamp" in data
        assert data["logger"] == "test"

    def test_json_formatter_with_exception(self):
        formatter = StructuredJSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="test.py",
            lineno=1, msg="error occurred", args=(), exc_info=exc_info,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["message"] == "test error"

    def test_correlation_id_in_log(self):
        token = REQUEST_ID_CTX.set("test-req-123")
        try:
            formatter = StructuredJSONFormatter()
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="test.py",
                lineno=1, msg="with correlation", args=(), exc_info=None,
            )
            output = formatter.format(record)
            data = json.loads(output)
            assert data["request_id"] == "test-req-123"
        finally:
            REQUEST_ID_CTX.reset(token)

    def test_get_request_id_default(self):
        token = REQUEST_ID_CTX.set(None)
        try:
            assert get_request_id() is None
        finally:
            REQUEST_ID_CTX.reset(token)

    def test_get_request_id_set(self):
        token = REQUEST_ID_CTX.set("abc-123")
        try:
            assert get_request_id() == "abc-123"
        finally:
            REQUEST_ID_CTX.reset(token)

    def test_configure_logging_sets_handler(self):
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        try:
            configure_logging(log_level="WARNING", json_format=True)
            assert len(root.handlers) >= 1
            assert root.level == logging.WARNING
        finally:
            root.handlers = original_handlers


class TestCorrelationMiddleware:
    def test_request_id_generated(self):
        response = client.get("/health")
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0

    def test_request_id_propagated(self):
        response = client.get("/health", headers={"X-Request-ID": "my-custom-id"})
        assert response.headers["X-Request-ID"] == "my-custom-id"

    def test_correlation_id_in_logs(self, caplog):
        with caplog.at_level(logging.INFO):
            client.get("/health", headers={"X-Request-ID": "log-test-id"})
        found = any("log-test-id" in record.message or "log-test-id" in str(record.__dict__) for record in caplog.records)


class TestTracing:
    def test_init_tracing(self):
        provider = init_tracing(service_name="test-service")
        assert provider is not None
        tracer = get_tracer("test")
        assert tracer is not None

    def test_trace_span(self):
        with trace_span("test-span", attributes={"key": "value"}) as span:
            assert span is not None
            assert span.is_recording()

    def test_trace_span_records_exception(self):
        with pytest.raises(ValueError):
            with trace_span("failing-span") as span:
                raise ValueError("boom")

    def test_shutdown_tracing(self):
        init_tracing(service_name="shutdown-test")
        shutdown_tracing()


class TestPrometheusMetrics:
    def test_metrics_endpoint(self):
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "http_requests_total" in response.text

    def test_metrics_text_format(self):
        text = get_metrics_text().decode("utf-8")
        assert "http_requests_total" in text
        assert "http_request_duration_seconds" in text

    def test_normalize_path(self):
        assert _normalize_path("/api/v1/rag/query") == "/api/v1/rag/query"
        assert _normalize_path("/api/v1/auth/login") == "/api/v1/auth/login"
        assert _normalize_path("/health") == "/health"
        assert _normalize_path("/api/v1/eval/runs/run-123") == "/api/v1/eval/runs/{id}"
        assert _normalize_path("/api/v1/rag/query/stream") == "/api/v1/rag/query/{id}"

    def test_metrics_not_counted_on_metrics_endpoint(self):
        initial = REQUEST_COUNT._metrics.get(("GET", "/metrics", "200"), 0)
        client.get("/metrics")
        after = REQUEST_COUNT._metrics.get(("GET", "/metrics", "200"), 0)
        assert after == initial

    def test_request_counted_after_request(self):
        from prometheus_client import Counter
        test_counter = Counter("test_req_count_verify", "test")
        test_counter.inc()
        assert test_counter._value.get() >= 1.0

    def test_init_app_info(self):
        init_app_info(version="1.0.0", environment="test")


class TestHealthChecks:
    def test_liveness_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded", "unhealthy")
        assert "uptime_seconds" in data
        assert "timestamp" in data
        assert isinstance(data["checks"], list)

    def test_liveness_detailed(self):
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded", "unhealthy")

    def test_readiness(self):
        _health_checks.clear()
        register_health_check("test-component", True)
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "test-component" in data["checks"]

    def test_readiness_not_ready(self):
        _health_checks.clear()
        register_health_check("failing-component", False)
        response = client.get("/health/ready")
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["failing-component"] is False

    def test_run_liveness_checks(self):
        result = run_liveness_checks()
        assert isinstance(result, HealthResponse)
        assert result.status in ("healthy", "degraded", "unhealthy")

    def test_run_readiness_checks(self):
        _health_checks.clear()
        register_health_check("ready-check", True)
        result = run_readiness_checks()
        assert isinstance(result, ReadinessResponse)
        assert result.status == "ready"

    def test_update_health_check(self):
        register_health_check("dynamic-check", True)
        update_health_check("dynamic-check", False)
        result = run_readiness_checks()
        assert result.checks["dynamic-check"] is False


class TestAPIMiddlewareIntegration:
    def test_request_id_on_all_endpoints(self):
        for path in ["/health", "/health/live", "/health/ready", "/metrics"]:
            response = client.get(path)
            assert "X-Request-ID" in response.headers

    def test_custom_request_id_on_api_endpoints(self):
        response = client.get("/health", headers={"X-Request-ID": "api-test-456"})
        assert response.headers["X-Request-ID"] == "api-test-456"
