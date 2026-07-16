# Enterprise RAG Platform

A production-grade Retrieval-Augmented Generation platform with streaming responses, intelligent caching, automated evaluation, and full Kubernetes deployment.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [RAG Pipeline](#rag-pipeline)
- [Configuration](#configuration)
- [Testing](#testing)
- [Deployment](#deployment)
- [CI/CD](#cicd)
- [Observability](#observability)
- [Seed Data](#seed-data)

## Features

- **Real-time streaming** — SSE-powered response streaming with token-by-token output
- **6-stage RAG pipeline** — Query rewriting, retrieval, reranking, context compression, answer generation, citation extraction
- **Multi-tenant isolation** — Collection-per-tenant in Qdrant, tenant-aware caching
- **Redis caching** — Namespace-partitioned cache with configurable TTLs and graceful NoOp fallback
- **OpenTelemetry tracing** — Distributed tracing with correlation IDs across all requests
- **Prometheus metrics** — Request duration histograms, cache hit rates, pipeline stage latencies
- **Structured logging** — JSON-formatted logs with correlation ID context propagation
- **Automated evaluation** — Ragas-based metrics with HTML report generation
- **Abort support** — Cancel in-flight streams from the client
- **Helm charts** — Production-ready Kubernetes manifests with HPA, PDB, and ingress
- **CI/CD** — GitHub Actions with lint, test, security scan, Docker build, and staged deployment

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────────────────┐
│   Frontend   │────▶│                   Backend (FastAPI)              │
│  Next.js:3000│ SSE │                                                  │
│              │◀────│  ┌──────────┐  ┌──────────┐  ┌────────────────┐ │
└─────────────┘     │  │ RAG API  │  │  Cache   │  │ Observability  │ │
                    │  │          │  │  Module  │  │    Module      │ │
                    │  └────┬─────┘  └────┬─────┘  └───────┬────────┘ │
                    │       │             │                 │          │
                    │  ┌────▼─────────────▼─────────────────▼────┐     │
                    │  │         LangGraph Workflow               │     │
                    │  │  rewrite → retrieve → rerank →          │     │
                    │  │  compress → generate → cite              │     │
                    │  └────┬─────────────┬─────────────────┬────┘     │
                    └───────┼─────────────┼─────────────────┼──────────┘
                            │             │                 │
                    ┌───────▼───┐  ┌──────▼──────┐  ┌──────▼──────┐
                    │  Qdrant   │  │    Redis     │  │  PostgreSQL  │
                    │  :6333    │  │    :6379     │  │    :5432     │
                    │  Vectors  │  │    Cache     │  │   Metadata   │
                    └───────────┘  └─────────────┘  └─────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.13, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy, Alembic |
| **AI/ML** | LangGraph, OpenAI, Anthropic Claude, Ragas (evaluation) |
| **Vector DB** | Qdrant (1536-dim cosine similarity) |
| **Cache** | Redis 7 with namespace-partitioned keys |
| **Database** | PostgreSQL 16 with async driver (asyncpg) |
| **Frontend** | Next.js 14, React 18, TypeScript, TailwindCSS, Lucide icons |
| **Observability** | OpenTelemetry, Prometheus, Grafana |
| **Infrastructure** | Docker Compose, Kubernetes, Helm, GitHub Actions |
| **Security** | PyJWT, bcrypt, Bandit SAST, Trivy, pip-audit |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### 1. Clone and start

```bash
git clone https://github.com/aishwarya-modi/enterprise-rag-platform.git
cd enterprise-rag-platform
docker compose up -d --build
```

### 2. Verify services

```bash
docker compose ps
```

All 5 services should show `healthy`:

| Service | Port | URL |
|---------|------|-----|
| Backend | 8000 | http://localhost:8000/health |
| Frontend | 3000 | http://localhost:3000 |
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |
| Qdrant | 6333 | http://localhost:6333 |

### 3. Open the UI

Navigate to **http://localhost:3000** and try queries like:

- "What is RAG?"
- "How does document chunking work?"
- "What are the evaluation metrics?"
- "What compliance requirements apply?"

### API Quick Test

```bash
# Health check
curl http://localhost:8000/health

# Streaming query
curl -N -X POST http://localhost:8000/api/v1/rag/query/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "What is RAG?", "tenant_id": "default"}'

# Prometheus metrics
curl http://localhost:8000/metrics
```

## Project Structure

```
enterprise-rag-platform/
├── backend/
│   ├── Dockerfile                  # Multi-stage build (builder → runtime)
│   ├── app/
│   │   ├── main.py                 # FastAPI app, middleware, routers
│   │   ├── core/
│   │   │   ├── cache.py            # Redis client, namespace caching, NoOp fallback
│   │   │   ├── config.py           # Pydantic Settings (env-driven)
│   │   │   ├── health.py           # Liveness/readiness checks
│   │   │   ├── logging.py          # Structured JSON formatter
│   │   │   ├── metrics.py          # Prometheus middleware + custom metrics
│   │   │   ├── middleware.py        # Correlation ID propagation
│   │   │   └── tracing.py          # OpenTelemetry setup
│   │   └── modules/
│   │       ├── rag/                # RAG pipeline (LangGraph)
│   │       │   ├── api.py          # /query, /query/stream, /graph endpoints
│   │       │   ├── nodes.py        # Pipeline nodes (rewrite, retrieve, rerank, etc.)
│   │       │   ├── streaming.py    # SSE streaming with abort support
│   │       │   ├── workflow.py     # LangGraph StateGraph definition
│   │       │   ├── state.py        # RAGState dataclass
│   │       │   └── schemas.py      # Request/response models
│   │       ├── cache/              # Cache metrics & invalidation API
│   │       ├── eval/               # Ragas evaluation + HTML reports
│   │       ├── observability/      # Metrics, health, Grafana dashboards
│   │       ├── auth/               # JWT authentication
│   │       ├── documents/          # Document upload (stub)
│   │       ├── llm/                # LLM chat endpoint
│   │       └── tenants/            # Multi-tenant management
│   └── scripts/
│       └── seed_qdrant.py          # Seed Qdrant with sample documents
├── frontend/
│   ├── Dockerfile                  # Multi-stage Next.js standalone build
│   ├── app/
│   │   ├── layout.tsx              # Root layout (dark theme)
│   │   └── page.tsx                # Main page
│   ├── components/
│   │   ├── chat-interface.tsx      # Chat UI with streaming
│   │   └── message.tsx             # Message bubble component
│   ├── hooks/
│   │   └── use-rag-stream.ts       # SSE streaming hook
│   └── lib/
│       └── rag-client.ts           # API client (POST + ReadableStream SSE)
├── helm/rag-platform/              # Helm chart (17 templates)
├── scripts/
│   ├── deploy.sh                   # Helm deploy/upgrade/teardown
│   ├── lint.sh                     # Ruff + Next.js lint
│   └── test.sh                     # Pytest with coverage
├── docker-compose.yml              # 5-service local orchestration
└── pyproject.toml                  # Python project config
```

## API Reference

All endpoints are prefixed with `/api/v1` (except health and metrics).

### RAG Pipeline

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/rag/query` | Synchronous RAG query |
| `POST` | `/api/v1/rag/query/stream` | Streaming RAG query (SSE) |
| `POST` | `/api/v1/rag/query/{query_id}/abort` | Abort an active stream |
| `GET` | `/api/v1/rag/graph` | LangGraph visualization (Mermaid) |

### Observability

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |
| `GET` | `/health/live` | Detailed liveness |
| `GET` | `/health/ready` | Readiness check (Redis + Qdrant) |
| `GET` | `/metrics` | Prometheus metrics |

### Cache Management

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/cache/metrics` | Cache hit rates + Redis status |
| `POST` | `/api/v1/cache/invalidate` | Invalidate by namespace/tenant/pattern |
| `GET` | `/api/v1/cache/ttl` | TTL configuration |

### Evaluation

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/eval/run` | Run evaluation against test dataset |
| `GET` | `/api/v1/eval/runs` | List evaluation runs |
| `GET` | `/api/v1/eval/runs/{run_id}` | Get evaluation run details |
| `POST` | `/api/v1/eval/report` | Generate HTML report |
| `GET` | `/api/v1/eval/report/{run_id}` | Download HTML report |

### Other

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/login` | User authentication |
| `GET` | `/api/v1/auth/me` | Current user |
| `POST` | `/api/v1/tenants` | Create tenant |
| `POST` | `/api/v1/documents` | Upload document |
| `POST` | `/api/v1/llm/chat` | Chat with LLM |

## RAG Pipeline

The RAG pipeline is built with LangGraph as a 6-node state graph:

```
┌──────────────┐    ┌───────────────────┐    ┌──────────────────┐
│ rewrite_query │───▶│ retrieve_documents │───▶│ rerank_documents │
│              │    │                   │    │                  │
│ Reformulates │    │ Semantic search   │    │ Score & sort     │
│ for retrieval│    │ in Qdrant         │    │ top 5 by score   │
└──────────────┘    └───────────────────┘    └────────┬─────────┘
                                                       │
┌──────────────┐    ┌───────────────────┐    ┌────────▼─────────┐
│   generate   │◀───│  compress_context  │◀───│                  │
│  _citations  │    │                   │    │ Extract key facts│
│              │    │ Summarize relevant │    │ from documents   │
│ Extract      │    │ information       │    │                  │
│ sources      │    │                   │    │                  │
└──────┬───────┘    └───────────────────┘    └──────────────────┘
       │
┌──────▼───────┐
│  stream      │
│  complete    │
│  (6 events)  │
└──────────────┘
```

### SSE Event Types

| Event | Description |
|-------|-------------|
| `stream_start` | Stream begins with query_id |
| `step_start` | Pipeline node begins processing |
| `step_complete` | Pipeline node finishes |
| `token` | Individual token for streaming text |
| `citation` | Source reference extracted |
| `answer_complete` | Full answer assembled |
| `stream_complete` | Stream finished successfully |
| `error` | Error occurred |
| `aborted` | Client aborted the stream |

## Configuration

All settings are driven by environment variables (via Pydantic Settings):

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/rag
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333

# Auth
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# LLM Providers (set at least one)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Cache TTLs (seconds)
CACHE_DEFAULT_TTL=3600
CACHE_EMBEDDING_TTL=86400
CACHE_SEARCH_TTL=3600
CACHE_LLM_TTL=7200

# Observability
LOG_LEVEL=INFO
LOG_JSON=true
PROMETHEUS_ENABLED=true
OTLP_ENDPOINT=http://localhost:4317

# Environment
ENVIRONMENT=development
```

### Docker Compose Environment

The `docker-compose.yml` passes these to the backend container. For the frontend, `NEXT_PUBLIC_API_URL` is a **build-time** variable set via `build.args`.

## Testing

### Run all tests

```bash
PYTHONPATH=backend python3 -m pytest backend/ -v
```

### Test breakdown

| Module | Tests | Coverage |
|--------|-------|----------|
| RAG Pipeline | 34 | Query, streaming, abort, graph, all 6 nodes, state management, SSE format |
| Observability | 28 | Logging, correlation IDs, tracing, Prometheus metrics, health checks |
| Evaluation | 22 | Cost estimation, Ragas metrics, HTML reports, API endpoints |
| Cache | 21 | Metrics, invalidation, TTL config, key generation, NoOp fallback |
| Auth | 1 | Login endpoint |
| Tenants | 1 | Create tenant |
| Documents | 1 | Upload document |
| LLM | 1 | Chat endpoint |
| **Total** | **109** | |

### Lint

```bash
# Backend
ruff check backend/
ruff format --check backend/

# Frontend
cd frontend && npm run lint
```

## Deployment

### Docker Compose (local)

```bash
# Start
docker compose up -d --build

# Stop
docker compose down

# Stop and remove volumes
docker compose down -v

# View logs
docker compose logs -f backend
```

### Kubernetes with Helm

```bash
# Install dependencies
cd helm/rag-platform
helm dependency update

# Deploy to staging
helm install rag-platform . \
  --namespace rag-staging \
  --create-namespace \
  --values values.yaml \
  --set environment=staging

# Upgrade
helm upgrade rag-platform . --namespace rag-staging --values values.yaml

# Deploy to production
helm install rag-platform . \
  --namespace rag-production \
  --create-namespace \
  --values values.yaml \
  --set environment=production \
  --set backend.replicaCount=3 \
  --set frontend.replicaCount=3
```

### Using deploy script

```bash
# Build and push images
./scripts/deploy.sh build

# Deploy to a namespace
./scripts/deploy.sh deploy rag-staging

# Check status
./scripts/deploy.sh status rag-staging

# View logs
./scripts/deploy.sh logs rag-staging

# Teardown
./scripts/deploy.sh teardown rag-staging
```

## CI/CD

### CI Pipeline (on push to `main` or PR)

```
lint → test ──┐
      security─┤
               └→ build-check
```

| Stage | What it does |
|-------|-------------|
| **lint** | Ruff check + format (backend), Next.js lint (frontend) |
| **test** | Pytest with coverage, Codecov upload, JUnit XML |
| **security** | Bandit SAST, pip-audit, Trivy filesystem scan |
| **build-check** | Docker Buildx build (no push), backend health verify |

### Release Pipeline (on tag `v*.*.*`)

```
docker-build-push → deploy-staging → deploy-production → release-notes
```

| Stage | What it does |
|-------|-------------|
| **docker-build-push** | Build + push to `ghcr.io` with semver + SHA tags |
| **deploy-staging** | Helm deploy to `rag-staging`, rollout verify, smoke test |
| **deploy-production** | Helm deploy to `rag-production`, 3-15 replicas |
| **release-notes** | Auto-generated changelog, GitHub Release |

## Observability

### Metrics (`GET /metrics`)

Prometheus-compatible metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `http_request_duration_seconds` | Histogram | Request latency by method, endpoint, status |
| `http_requests_total` | Counter | Total request count |
| `cache_hits_total` | Counter | Cache hit count by namespace |
| `cache_misses_total` | Counter | Cache miss count by namespace |
| `rag_query_duration_seconds` | Histogram | RAG pipeline latency |
| `rag_documents_retrieved` | Histogram | Number of documents retrieved per query |

### Tracing

All requests get a correlation ID (`X-Request-ID` header) that propagates through:
- FastAPI middleware → RAG pipeline nodes → cache lookups → LLM calls
- Included in all log entries and trace spans

### Logging

Structured JSON logs with fields:

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "message": "RAG query completed",
  "correlation_id": "abc-123",
  "query_id": "def-456",
  "duration_ms": 1250
}
```

### Grafana

Pre-configured dashboards in `backend/app/modules/observability/grafana/`:
- `dashboard.json` — Request rate, latency, error rate, cache performance
- `datasources.json` — Prometheus datasource configuration

## Seed Data

The Qdrant vector store is seeded with 26 document chunks across 9 topics:

| Document | Chunks | Topics |
|----------|--------|--------|
| `ai-strategy-whitepaper.pdf` | 3 | RAG framework, architecture, enterprise deployment |
| `knowledge-management-guide.pdf` | 3 | KM systems, embeddings, chunking strategies |
| `infrastructure-architecture.pdf` | 3 | Production infra, observability, scaling |
| `compliance-framework.pdf` | 2 | GDPR, SOC 2, multi-tenant isolation |
| `eval-and-quality.pdf` | 3 | Ragas metrics, human eval, CI/CD quality gates |
| `greetings-faq.pdf` | 3 | Welcome messages, assistant capabilities |
| `datetime-reference.pdf` | 3 | Timestamps, UTC, time management |
| `weather-knowledge.pdf` | 2 | API integration, external data sources |
| `platform-capabilities.pdf` | 4 | Pipeline stages, services, getting started |

### Re-seed

```bash
docker exec enterprise-rag-platform-backend-1 python /app/scripts/seed_qdrant.py
```

## License

MIT
