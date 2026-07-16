FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    "fastapi[all]>=0.128.0,<1.0" \
    "uvicorn[standard]>=0.39.0,<1.0" \
    "pydantic>=2.13.0,<3.0" \
    "pydantic-settings>=2.11.0,<3.0" \
    "SQLAlchemy>=2.0.0,<3.0" \
    "asyncpg>=0.31.0,<1.0" \
    "redis>=5.0.0,<6.0" \
    "qdrant-client>=1.16.0,<2.0" \
    "langgraph>=0.6.0,<1.0" \
    "openai>=1.0.0,<3.0" \
    "anthropic>=0.116.0,<1.0" \
    "httpx>=0.28.0,<1.0" \
    "PyJWT>=2.10.0,<3.0" \
    "python-multipart>=0.0.20,<1.0" \
    "opentelemetry-api>=1.27.0" \
    "opentelemetry-sdk>=1.27.0" \
    "opentelemetry-exporter-otlp>=1.27.0" \
    "opentelemetry-instrumentation-fastapi>=0.48b0" \
    "prometheus-client>=0.21.0" \
    "ragas>=0.4.0,<1.0" \
    "tiktoken>=0.13.0"

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY backend/app ./app

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
