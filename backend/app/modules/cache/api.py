from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.core.cache import CacheNamespace, metrics as cache_metrics, get_cache
from app.core.config import get_settings
from app.modules.cache.schemas import (
    CacheInvalidationRequest,
    CacheInvalidationResponse,
    CacheMetricsResponse,
    CacheTTLResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["Cache"])


@router.get("/metrics", response_model=CacheMetricsResponse)
async def get_cache_metrics() -> CacheMetricsResponse:
    cache = get_cache()
    redis_connected = await cache.ping()
    return CacheMetricsResponse(
        namespaces=cache_metrics.get_all_metrics(),
        redis_connected=redis_connected,
    )


@router.post("/invalidate", response_model=CacheInvalidationResponse)
async def invalidate_cache(request: CacheInvalidationRequest) -> CacheInvalidationResponse:
    cache = get_cache()
    total_deleted = 0

    if request.tenant_id:
        count = await cache.flush_tenant(request.tenant_id)
        total_deleted += count

    if request.namespace:
        try:
            ns = CacheNamespace(request.namespace)
            count = await cache.delete_namespace(ns)
            total_deleted += count
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid namespace: {request.namespace}. Valid: {[n.value for n in CacheNamespace]}")

    if request.pattern:
        count = await cache.delete_pattern(request.pattern)
        total_deleted += count

    if not request.tenant_id and not request.namespace and not request.pattern:
        raise HTTPException(status_code=400, detail="At least one of namespace, tenant_id, or pattern must be provided")

    return CacheInvalidationResponse(
        success=True,
        keys_deleted=total_deleted,
        message=f"Deleted {total_deleted} keys",
    )


@router.get("/ttl", response_model=CacheTTLResponse)
async def get_cache_ttl_config() -> CacheTTLResponse:
    settings = get_settings()
    return CacheTTLResponse(
        embedding_ttl=settings.cache_embedding_ttl,
        search_ttl=settings.cache_search_ttl,
        llm_ttl=settings.cache_llm_ttl,
        auth_ttl=settings.cache_auth_ttl,
        session_ttl=settings.cache_session_ttl,
        default_ttl=settings.cache_default_ttl,
    )
