from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestCacheMetrics:
    def test_metrics_returns_200(self) -> None:
        response = client.get("/api/v1/cache/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "namespaces" in data
        assert "redis_connected" in data
        assert isinstance(data["namespaces"], dict)

    def test_metrics_structure(self) -> None:
        response = client.get("/api/v1/cache/metrics")
        data = response.json()
        assert isinstance(data["redis_connected"], bool)


class TestCacheInvalidation:
    def test_invalidate_requires_body(self) -> None:
        response = client.post("/api/v1/cache/invalidate", json={})
        assert response.status_code == 400

    def test_invalidate_by_namespace(self) -> None:
        response = client.post(
            "/api/v1/cache/invalidate",
            json={"namespace": "llm"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "keys_deleted" in data

    def test_invalidate_by_tenant(self) -> None:
        response = client.post(
            "/api/v1/cache/invalidate",
            json={"tenant_id": "test-tenant"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_invalidate_invalid_namespace_returns_400(self) -> None:
        response = client.post(
            "/api/v1/cache/invalidate",
            json={"namespace": "invalid_ns"},
        )
        assert response.status_code == 400

    def test_invalidate_by_pattern(self) -> None:
        response = client.post(
            "/api/v1/cache/invalidate",
            json={"pattern": "llm:test:*"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_invalidate_all_namespaces(self) -> None:
        for ns in ["emb", "search", "llm", "auth", "session"]:
            response = client.post(
                "/api/v1/cache/invalidate",
                json={"namespace": ns},
            )
            assert response.status_code == 200


class TestCacheTTLConfig:
    def test_ttl_returns_defaults(self) -> None:
        response = client.get("/api/v1/cache/ttl")
        assert response.status_code == 200
        data = response.json()
        assert data["embedding_ttl"] == 86400
        assert data["search_ttl"] == 3600
        assert data["llm_ttl"] == 7200
        assert data["auth_ttl"] == 3600
        assert data["session_ttl"] == 1800
        assert data["default_ttl"] == 3600


class TestCacheCore:
    def test_make_key(self) -> None:
        from app.core.cache import CacheNamespace, make_key

        key = make_key(CacheNamespace.LLM, "openai", "gpt-4o", "abc123")
        assert key == "llm:openai:gpt-4o:abc123"

    def test_make_hash_deterministic(self) -> None:
        from app.core.cache import make_hash

        h1 = make_hash("hello", "world")
        h2 = make_hash("hello", "world")
        assert h1 == h2
        assert len(h1) == 16

    def test_make_hash_different_inputs(self) -> None:
        from app.core.cache import make_hash

        h1 = make_hash("hello", "world")
        h2 = make_hash("hello", "earth")
        assert h1 != h2

    def test_metrics_collector(self) -> None:
        from app.core.cache import MetricsCollector

        collector = MetricsCollector()
        collector.record_hit("test", 1.5)
        collector.record_hit("test", 2.0)
        collector.record_miss("test", 0.5)
        collector.record_set("test", 3.0)
        collector.record_delete("test")

        m = collector.get_metrics("test")
        assert m["hits"] == 2
        assert m["misses"] == 1
        assert m["sets"] == 1
        assert m["deletes"] == 1
        assert m["total_requests"] == 3
        assert m["hit_rate"] == pytest.approx(2 / 3, abs=0.01)

    def test_metrics_all_namespaces(self) -> None:
        from app.core.cache import MetricsCollector

        collector = MetricsCollector()
        collector.record_hit("ns1", 1.0)
        collector.record_hit("ns2", 2.0)

        all_m = collector.get_all_metrics()
        assert "ns1" in all_m
        assert "ns2" in all_m

    def test_noop_redis_graceful(self) -> None:
        from app.core.cache import _NoOpRedis
        import asyncio

        noop = _NoOpRedis()
        result = asyncio.run(noop.get("key"))
        assert result is None
        result = asyncio.run(noop.ping())
        assert result is False


class TestCacheIntegration:
    def test_noop_redis_returns_none(self) -> None:
        from app.core.cache import _NoOpRedis
        import asyncio

        noop = _NoOpRedis()
        result = asyncio.run(noop.get("key"))
        assert result is None
        result = asyncio.run(noop.ping())
        assert result is False

    def test_noop_redis_set_returns_true(self) -> None:
        from app.core.cache import _NoOpRedis
        import asyncio

        noop = _NoOpRedis()
        result = asyncio.run(noop.set("key", "value"))
        assert result is True
        result = asyncio.run(noop.setex("key", 60, "value"))
        assert result is True

    def test_noop_redis_delete_returns_zero(self) -> None:
        from app.core.cache import _NoOpRedis
        import asyncio

        noop = _NoOpRedis()
        result = asyncio.run(noop.delete("key"))
        assert result == 0

    def test_cache_graceful_without_redis(self) -> None:
        from app.core.cache import RedisCache
        import asyncio

        cache = RedisCache("redis://invalid:9999", default_ttl=60)
        result = asyncio.run(cache.set("test:key", {"data": "value"}, namespace="test"))
        assert result is True
        result2 = asyncio.run(cache.get("test:key", "test"))
        assert result2 is None

    def test_session_service_graceful_without_redis(self) -> None:
        from app.modules.auth.service import SessionService
        import asyncio

        service = SessionService()
        asyncio.run(service.append_message("test-session-1", "user", "Hello"))
        history = asyncio.run(service.get_history("test-session-1"))
        assert history == []

    def test_session_service_empty(self) -> None:
        from app.modules.auth.service import SessionService
        import asyncio

        service = SessionService()
        history = asyncio.run(service.get_history("nonexistent-session"))
        assert history == []
