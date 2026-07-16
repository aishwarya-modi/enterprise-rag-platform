from __future__ import annotations

import logging
import time
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_start_time = time.time()

_health_checks: dict[str, bool] = {}


def register_health_check(name: str, healthy: bool = True) -> None:
    _health_checks[name] = healthy


def update_health_check(name: str, healthy: bool) -> None:
    _health_checks[name] = healthy


class ComponentHealth(BaseModel):
    name: str
    status: Literal["healthy", "unhealthy", "unknown"]
    latency_ms: float = 0.0
    message: str = ""


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str = "0.1.0"
    uptime_seconds: float
    timestamp: float
    checks: list[ComponentHealth] = Field(default_factory=list)


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, bool]
    timestamp: float


def check_redis() -> ComponentHealth:
    start = time.perf_counter()
    try:
        from app.core.cache import get_cache
        cache = get_cache()
        import asyncio
        connected = asyncio.get_event_loop().run_until_complete(cache.ping()) if hasattr(asyncio, '_get_running_loop') and asyncio._get_running_loop() is None else True
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(name="redis", status="healthy" if connected else "unhealthy", latency_ms=latency)
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(name="redis", status="unhealthy", latency_ms=latency, message=str(e))


def check_qdrant() -> ComponentHealth:
    start = time.perf_counter()
    try:
        from qdrant_client import QdrantClient
        from app.core.config import get_settings
        settings = get_settings()
        client = QdrantClient(url=settings.qdrant_url)
        client.get_collections()
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(name="qdrant", status="healthy", latency_ms=latency)
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(name="qdrant", status="unhealthy", latency_ms=latency, message=str(e))


def run_liveness_checks() -> HealthResponse:
    uptime = time.time() - _start_time
    checks = [check_redis(), check_qdrant()]

    unhealthy_count = sum(1 for c in checks if c.status == "unhealthy")
    if unhealthy_count == 0:
        status = "healthy"
    elif unhealthy_count < len(checks):
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthResponse(
        status=status,
        uptime_seconds=uptime,
        timestamp=time.time(),
        checks=checks,
    )


def run_readiness_checks() -> ReadinessResponse:
    checks_dict: dict[str, bool] = {}
    for name, healthy in _health_checks.items():
        checks_dict[name] = healthy

    all_ready = all(checks_dict.values()) if checks_dict else True

    return ReadinessResponse(
        status="ready" if all_ready else "not_ready",
        checks=checks_dict,
        timestamp=time.time(),
    )
