from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, Response

from app.core.health import HealthResponse, ReadinessResponse, run_liveness_checks, run_readiness_checks
from app.core.metrics import get_metrics_text

router = APIRouter(tags=["Observability"])


@router.get("/health", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return run_liveness_checks()


@router.get("/health/live", response_model=HealthResponse)
async def liveness_detailed() -> HealthResponse:
    return run_liveness_checks()


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness() -> ReadinessResponse:
    return run_readiness_checks()


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    return PlainTextResponse(
        content=get_metrics_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
