from fastapi import FastAPI

from app.core.logging import configure_logging
from app.modules.auth.api import router as auth_router
from app.modules.documents.api import router as documents_router
from app.modules.embeddings.api import router as embeddings_router
from app.modules.llm.api import router as llm_router
from app.modules.tenants.api import router as tenants_router

configure_logging()

app = FastAPI(
    title="Enterprise RAG Platform",
    version="0.1.0",
    description="Production-grade enterprise retrieval augmented generation platform",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(tenants_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(embeddings_router, prefix="/api/v1")
app.include_router(llm_router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
