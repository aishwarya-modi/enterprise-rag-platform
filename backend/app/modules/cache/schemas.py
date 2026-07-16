from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class CacheMetricsResponse(BaseModel):
    namespaces: dict[str, dict[str, Any]] = Field(description="Per-namespace cache metrics")
    redis_connected: bool = Field(description="Whether Redis is connected")


class CacheInvalidationRequest(BaseModel):
    namespace: Optional[str] = Field(default=None, description="Cache namespace to invalidate (embedding, search, llm, auth, session)")
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID to invalidate all caches for")
    pattern: Optional[str] = Field(default=None, description="Custom key pattern to delete (e.g., 'llm:*')")


class CacheInvalidationResponse(BaseModel):
    success: bool
    keys_deleted: int
    message: str


class CacheTTLResponse(BaseModel):
    embedding_ttl: int
    search_ttl: int
    llm_ttl: int
    auth_ttl: int
    session_ttl: int
    default_ttl: int
