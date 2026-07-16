from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CacheNamespace(str, Enum):
    EMBEDDING = "emb"
    SEARCH = "search"
    LLM = "llm"
    AUTH = "auth"
    SESSION = "session"


@dataclass
class CacheMetrics:
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    total_get_latency_ms: float = 0.0
    total_set_latency_ms: float = 0.0

    @property
    def total_requests(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        total = self.total_requests
        return self.hits / total if total > 0 else 0.0

    @property
    def avg_get_latency_ms(self) -> float:
        return self.total_get_latency_ms / self.total_requests if self.total_requests > 0 else 0.0

    @property
    def avg_set_latency_ms(self) -> float:
        return self.total_set_latency_ms / self.sets if self.sets > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "total_requests": self.total_requests,
            "hit_rate": round(self.hit_rate, 4),
            "avg_get_latency_ms": round(self.avg_get_latency_ms, 3),
            "avg_set_latency_ms": round(self.avg_set_latency_ms, 3),
        }


class MetricsCollector:
    def __init__(self) -> None:
        self._metrics: dict[str, CacheMetrics] = {}
        self._lock = threading.Lock()

    def _get_or_create(self, namespace: str) -> CacheMetrics:
        if namespace not in self._metrics:
            self._metrics[namespace] = CacheMetrics()
        return self._metrics[namespace]

    def record_hit(self, namespace: str, latency_ms: float) -> None:
        with self._lock:
            m = self._get_or_create(namespace)
            m.hits += 1
            m.total_get_latency_ms += latency_ms

    def record_miss(self, namespace: str, latency_ms: float) -> None:
        with self._lock:
            m = self._get_or_create(namespace)
            m.misses += 1
            m.total_get_latency_ms += latency_ms

    def record_set(self, namespace: str, latency_ms: float) -> None:
        with self._lock:
            m = self._get_or_create(namespace)
            m.sets += 1
            m.total_set_latency_ms += latency_ms

    def record_delete(self, namespace: str) -> None:
        with self._lock:
            m = self._get_or_create(namespace)
            m.deletes += 1

    def record_error(self, namespace: str) -> None:
        with self._lock:
            m = self._get_or_create(namespace)
            m.errors += 1

    def get_all_metrics(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {ns: m.to_dict() for ns, m in self._metrics.items()}

    def get_metrics(self, namespace: str) -> dict[str, Any]:
        with self._lock:
            m = self._get_or_create(namespace)
            return m.to_dict()


metrics = MetricsCollector()


def make_key(namespace: CacheNamespace, *parts: str) -> str:
    prefix = namespace.value
    separator = ":"
    all_parts = [prefix] + list(parts)
    return separator.join(all_parts)


def make_hash(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class RedisCache:
    def __init__(self, redis_url: str, default_ttl: int = 3600) -> None:
        self._redis_url = redis_url
        self._default_ttl = default_ttl
        self._client: Any = None
        self._lock = threading.Lock()

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        with self._lock:
            if self._client is not None:
                return self._client
            try:
                import redis.asyncio as aioredis

                self._client = aioredis.from_url(
                    self._redis_url,
                    decode_responses=True,
                    socket_connect_timeout=3,
                    socket_timeout=3,
                    retry_on_timeout=True,
                )
                logger.info("Redis cache connected: %s", self._redis_url)
            except Exception as e:
                logger.warning("Redis unavailable, using no-op cache: %s", e)
                self._client = _NoOpRedis()
            return self._client

    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        start = time.monotonic()
        try:
            client = self._get_client()
            raw = await client.get(key)
            latency = (time.monotonic() - start) * 1000
            if raw is not None:
                metrics.record_hit(namespace, latency)
                return json.loads(raw)
            metrics.record_miss(namespace, latency)
            return None
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            metrics.record_error(namespace)
            metrics.record_miss(namespace, latency)
            logger.debug("Cache get error for %s: %s", key, e)
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None, namespace: str = "default") -> bool:
        start = time.monotonic()
        try:
            client = self._get_client()
            serialized = json.dumps(value, default=str)
            effective_ttl = ttl if ttl is not None else self._default_ttl
            if effective_ttl > 0:
                await client.setex(key, effective_ttl, serialized)
            else:
                await client.set(key, serialized)
            latency = (time.monotonic() - start) * 1000
            metrics.record_set(namespace, latency)
            return True
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            metrics.record_error(namespace)
            logger.debug("Cache set error for %s: %s", key, e)
            return False

    async def delete(self, key: str, namespace: str = "default") -> bool:
        try:
            client = self._get_client()
            await client.delete(key)
            metrics.record_delete(namespace)
            return True
        except Exception as e:
            metrics.record_error(namespace)
            logger.debug("Cache delete error for %s: %s", key, e)
            return False

    async def delete_pattern(self, pattern: str, namespace: str = "default") -> int:
        try:
            client = self._get_client()
            count = 0
            async for key in client.scan_iter(match=pattern, count=100):
                await client.delete(key)
                count += 1
            metrics.record_delete(namespace)
            return count
        except Exception as e:
            metrics.record_error(namespace)
            logger.debug("Cache delete_pattern error for %s: %s", pattern, e)
            return 0

    async def delete_namespace(self, namespace: CacheNamespace) -> int:
        pattern = f"{namespace.value}:*"
        return await self.delete_pattern(pattern, namespace.value)

    async def flush_tenant(self, tenant_id: str) -> int:
        count = 0
        for ns in CacheNamespace:
            pattern = f"{ns.value}:tenant:{tenant_id}:*"
            count += await self.delete_pattern(pattern, ns.value)
        return count

    async def get_ttl(self, key: str) -> int:
        try:
            client = self._get_client()
            return await client.ttl(key)
        except Exception:
            return -1

    async def exists(self, key: str) -> bool:
        try:
            client = self._get_client()
            return bool(await client.exists(key))
        except Exception:
            return False

    async def ping(self) -> bool:
        try:
            client = self._get_client()
            return await client.ping()
        except Exception:
            return False

    async def close(self) -> None:
        if self._client and not isinstance(self._client, _NoOpRedis):
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None


class _NoOpRedis:
    async def get(self, *a: Any, **kw: Any) -> None:
        return None

    async def set(self, *a: Any, **kw: Any) -> bool:
        return True

    async def setex(self, *a: Any, **kw: Any) -> bool:
        return True

    async def delete(self, *a: Any, **kw: Any) -> int:
        return 0

    async def exists(self, *a: Any, **kw: Any) -> bool:
        return False

    async def ping(self) -> bool:
        return False

    async def ttl(self, *a: Any, **kw: Any) -> int:
        return -1

    def scan_iter(self, *a: Any, **kw: Any) -> Any:
        return _AsyncEmptyIterator()


class _AsyncEmptyIterator:
    def __aiter__(self) -> _AsyncEmptyIterator:
        return self

    async def __anext__(self) -> Any:
        raise StopAsyncIteration


_cache: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    global _cache
    if _cache is None:
        from app.core.config import get_settings

        settings = get_settings()
        _cache = RedisCache(
            redis_url=settings.redis_url,
            default_ttl=settings.cache_default_ttl,
        )
    return _cache


async def cache_get_or_set(
    key: str,
    factory: Any,
    ttl: Optional[int] = None,
    namespace: str = "default",
) -> Any:
    cache = get_cache()
    cached = await cache.get(key, namespace)
    if cached is not None:
        return cached
    result = await factory() if callable(factory) else factory
    await cache.set(key, result, ttl=ttl, namespace=namespace)
    return result
