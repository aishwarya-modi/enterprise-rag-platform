from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.health import register_health_check
from app.core.logging import configure_logging
from app.core.metrics import PrometheusMiddleware, init_app_info
from app.core.tracing import init_tracing
from app.modules.auth.api import router as auth_router
from app.modules.cache.api import router as cache_router
from app.modules.documents.api import router as documents_router
from app.modules.eval.api import router as eval_router
from app.modules.llm.api import router as llm_router
from app.modules.observability.api import router as obs_router
from app.modules.rag.api import router as rag_router
from app.modules.tenants.api import router as tenants_router

settings = get_settings()

configure_logging(log_level=settings.log_level, json_format=settings.log_json)
init_tracing(
    service_name=settings.otel_service_name,
    otlp_endpoint=settings.otlp_endpoint,
    console_export=settings.debug,
)
init_app_info(version="0.1.0", environment=settings.environment)

register_health_check("config", True)

app = FastAPI(
    title="Enterprise RAG Platform",
    version="0.1.0",
    description="Production-grade enterprise retrieval augmented generation platform",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.prometheus_enabled:
    app.add_middleware(PrometheusMiddleware)

from app.core.middleware import CorrelationIDMiddleware
app.add_middleware(CorrelationIDMiddleware)

app.include_router(obs_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(cache_router, prefix="/api/v1")
app.include_router(tenants_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(llm_router, prefix="/api/v1")
app.include_router(eval_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
