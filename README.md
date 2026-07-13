# Enterprise RAG Platform

A production-grade, cloud-ready enterprise retrieval augmented generation platform built with modular architecture, async services, and deployment automation.

## Architecture decisions

- Hexagonal architecture keeps domain logic isolated from infrastructure details.
- FastAPI provides OpenAPI-first APIs and async request handling.
- LangGraph is the orchestration layer for multi-step reasoning and agentic workflows.
- Qdrant handles vector search, PostgreSQL stores metadata, and Redis powers caching and queueing.
- The backend is split into modules with API, service, repository, schema, model, and test layers.
- The frontend is a Next.js control plane that can evolve into an admin experience and chat surface.

## Stack

- Backend: Python 3.13, FastAPI, SQLAlchemy, Alembic, Pydantic v2, Poetry
- AI: LangGraph, OpenAI, Anthropic Claude, Gemini, Ollama
- Data: Qdrant, PostgreSQL, Redis
- Deployment: Docker Compose, Kubernetes, Helm, GitHub Actions
- Frontend: React, Next.js, TypeScript, TailwindCSS, shadcn/ui

## Repository structure

- backend/app: modular backend application
- frontend: Next.js application
- docker-compose.yml: local orchestration
- backend/Dockerfile: container image for the API service

## Next steps

1. Add Alembic migrations and SQLAlchemy models.
2. Implement real JWT/OAuth and RBAC enforcement.
3. Create ingestion workers and queue-based document processing.
4. Add full LLM provider adapters with provider selection.
5. Add Kubernetes manifests and Helm charts.
6. Add GitHub Actions CI/CD and observability.
