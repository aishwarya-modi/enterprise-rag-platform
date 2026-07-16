from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="enterprise-rag-platform")
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/rag"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"
    default_llm_provider: str = "openai"

    cache_default_ttl: int = 3600
    cache_embedding_ttl: int = 86400
    cache_search_ttl: int = 3600
    cache_llm_ttl: int = 7200
    cache_auth_ttl: int = 3600
    cache_session_ttl: int = 1800

    otlp_endpoint: Optional[str] = None
    otel_service_name: str = "enterprise-rag-platform"
    log_level: str = "INFO"
    log_json: bool = True
    prometheus_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
