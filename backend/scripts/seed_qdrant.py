"""Seed Qdrant with sample enterprise documents for RAG demo."""
from __future__ import annotations

import hashlib
import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

TENANT_ID = "default"
COLLECTION = f"tenant_{TENANT_ID}"
VECTOR_SIZE = 1536

DOCUMENTS = [
    {
        "source": "ai-strategy-whitepaper.pdf",
        "chunks": [
            {
                "page": 1,
                "text": (
                    "Retrieval-Augmented Generation (RAG) is an AI framework that combines "
                    "information retrieval with large language model generation. RAG enhances LLM "
                    "responses by first retrieving relevant documents from a knowledge base, then "
                    "using those documents as context for generating accurate, grounded answers. "
                    "This approach significantly reduces hallucinations and improves factual accuracy."
                ),
            },
            {
                "page": 2,
                "text": (
                    "The core architecture of a RAG system consists of three stages: indexing, "
                    "retrieval, and generation. During indexing, documents are chunked, embedded "
                    "into vector representations, and stored in a vector database. During retrieval, "
                    "user queries are embedded and matched against stored vectors using approximate "
                    "nearest neighbor search. During generation, retrieved chunks are passed as "
                    "context to an LLM to produce the final answer."
                ),
            },
            {
                "page": 3,
                "text": (
                    "Enterprise RAG deployments require careful consideration of several factors: "
                    "multi-tenancy for data isolation, role-based access control, audit logging "
                    "for compliance, low-latency retrieval at scale, and monitoring of pipeline "
                    "performance. Organizations should implement chunking strategies that preserve "
                    "semantic coherence while maintaining manageable chunk sizes of 256-512 tokens."
                ),
            },
        ],
    },
    {
        "source": "knowledge-management-guide.pdf",
        "chunks": [
            {
                "page": 1,
                "text": (
                    "Enterprise knowledge management systems serve as centralized repositories for "
                    "organizational knowledge. Modern KM platforms leverage AI to automatically "
                    "classify, tag, and surface relevant information. Key capabilities include "
                    "full-text search, semantic search, automated content summarization, and "
                    "intelligent document routing based on topic relevance."
                ),
            },
            {
                "page": 2,
                "text": (
                    "Vector embeddings are numerical representations of text that capture semantic "
                    "meaning. Popular embedding models include OpenAI's text-embedding-3-small "
                    "(1536 dimensions), Cohere's embed-v3, and open-source models like BGE and "
                    "E5. The choice of embedding model impacts retrieval quality and should be "
                    "evaluated against domain-specific benchmarks."
                ),
            },
            {
                "page": 3,
                "text": (
                    "Document chunking is critical for RAG performance. Common strategies include: "
                    "fixed-size chunking (splitting at fixed token counts), recursive character "
                    "splitting (preserving paragraph and sentence boundaries), semantic chunking "
                    "(splitting at topic transitions), and document-structure-aware chunking "
                    "(using headings, sections, and formatting as split points)."
                ),
            },
        ],
    },
    {
        "source": "infrastructure-architecture.pdf",
        "chunks": [
            {
                "page": 1,
                "text": (
                    "Production RAG systems require robust infrastructure. A typical deployment "
                    "includes: a vector database (Qdrant, Pinecone, Weaviate, or Milvus) for "
                    "similarity search, a cache layer (Redis) for query result caching, a relational "
                    "database (PostgreSQL) for metadata storage, and an application layer built "
                    "with FastAPI or similar frameworks for API serving."
                ),
            },
            {
                "page": 2,
                "text": (
                    "Observability is essential for production RAG pipelines. Key metrics to monitor "
                    "include: query latency (p50, p95, p99), retrieval recall and precision, "
                    "LLM response quality scores, cache hit rates, token usage and cost per query, "
                    "and error rates by pipeline stage. OpenTelemetry and Prometheus provide "
                    "comprehensive tracing and metrics collection."
                ),
            },
            {
                "page": 3,
                "text": (
                    "Scaling RAG systems involves horizontal scaling of retrieval and generation "
                    "services, intelligent caching to reduce redundant computations, query batching "
                    "for throughput optimization, and asynchronous processing for non-interactive "
                    "workloads. Kubernetes with Helm charts enables reproducible deployments "
                    "across staging and production environments."
                ),
            },
        ],
    },
    {
        "source": "compliance-framework.pdf",
        "chunks": [
            {
                "page": 1,
                "text": (
                    "Enterprise AI systems must comply with regulatory requirements including GDPR, "
                    "SOC 2, and industry-specific regulations. For RAG systems, this means implementing "
                    "data residency controls, ensuring PII is not exposed in retrieval results, "
                    "maintaining audit trails of all queries and responses, and providing mechanisms "
                    "for data deletion and right-to-be-forgotten requests."
                ),
            },
            {
                "page": 2,
                "text": (
                    "Multi-tenant RAG architectures must enforce strict data isolation between "
                    "tenants. This is typically achieved through: collection-per-tenant isolation "
                    "in vector databases, row-level security in metadata stores, namespace-based "
                    "cache partitioning, and tenant-aware query routing at the API gateway level. "
                    "Each tenant should have dedicated encryption keys for data at rest."
                ),
            },
        ],
    },
    {
        "source": "eval-and-quality.pdf",
        "chunks": [
            {
                "page": 1,
                "text": (
                    "RAG evaluation requires measuring both retrieval quality and generation quality. "
                    "The Ragas framework provides automated evaluation metrics including: answer "
                    "relevance (how well the answer addresses the question), context precision "
                    "(how relevant the retrieved context is), context recall (whether all relevant "
                    "information was retrieved), and faithfulness (whether the answer is grounded "
                    "in the retrieved context)."
                ),
            },
            {
                "page": 2,
                "text": (
                    "Beyond automated metrics, human evaluation remains important for assessing "
                    "RAG system quality. Key human evaluation dimensions include: factual accuracy, "
                    "completeness of the answer, appropriate citation of sources, natural language "
                    "fluency, and adherence to organizational tone and style guidelines. A/B testing "
                    "with real users provides the most reliable quality signals."
                ),
            },
            {
                "page": 3,
                "text": (
                    "Continuous evaluation pipelines should run automatically on a regular schedule "
                    "or on each deployment. These pipelines should: maintain a golden test dataset "
                    "of question-answer-context triples, track metric trends over time, trigger "
                    "alerts when quality degrades below thresholds, and generate HTML reports for "
                    "stakeholder review. Integration with CI/CD ensures quality gates before "
                    "production deployment."
                ),
            },
        ],
    },
    {
        "source": "greetings-faq.pdf",
        "chunks": [
            {
                "page": 1,
                "text": (
                    "Hello! Welcome to the Enterprise RAG Platform. I am your AI assistant, "
                    "ready to help you find information from our knowledge base. You can ask me "
                    "questions about any topic covered in our documents, and I will search for "
                    "relevant answers with proper citations."
                ),
            },
            {
                "page": 2,
                "text": (
                    "Greetings! Here are some things I can help you with: searching enterprise "
                    "documents, answering questions about policies and procedures, finding "
                    "information about technical architectures, understanding compliance "
                    "requirements, and retrieving data from the knowledge base. Just type your "
                    "question and I will stream the answer in real-time."
                ),
            },
            {
                "page": 3,
                "text": (
                    "Hi there! I am powered by Retrieval-Augmented Generation (RAG), which means "
                    "I first search through our document collection to find relevant information, "
                    "then generate a helpful answer based on those sources. Every answer includes "
                    "citations so you can verify the information."
                ),
            },
        ],
    },
    {
        "source": "datetime-reference.pdf",
        "chunks": [
            {
                "page": 1,
                "text": (
                    "The current system date is dynamically determined at query time. Our enterprise "
                    "platform operates in UTC timezone by default. All timestamps in the system use "
                    "ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ). The platform supports timezone "
                    "conversion for multi-region deployments."
                ),
            },
            {
                "page": 2,
                "text": (
                    "For date and time queries, the system references the current server timestamp. "
                    "The platform provides a /health endpoint that includes the current "
                    "uptime_seconds field, which can be used to calculate approximate server time. "
                    "Enterprise scheduling and calendar integrations are available through the API."
                ),
            },
            {
                "page": 3,
                "text": (
                    "Time management features in the platform include: query timestamp logging for "
                    "audit trails, response time tracking per pipeline stage, cache TTL management "
                    "based on time intervals, and scheduled evaluation runs. All timestamps are "
                    "stored with microsecond precision."
                ),
            },
        ],
    },
    {
        "source": "weather-knowledge.pdf",
        "chunks": [
            {
                "page": 1,
                "text": (
                    "I do not have real-time access to weather data or live APIs. However, I can "
                    "answer questions about weather-related topics from our knowledge base, such as "
                    "climate policies, weather data infrastructure, meteorological data processing "
                    "pipelines, and weather-related compliance requirements. For live weather, "
                    "please check a weather service directly."
                ),
            },
            {
                "page": 2,
                "text": (
                    "Our enterprise platform does not include live weather feeds, but it supports "
                    "integration with external data sources through API connectors. Weather data "
                    "can be ingested into the RAG pipeline if stored as documents in the knowledge "
                    "base. The platform supports PDF, text, and structured data ingestion."
                ),
            },
        ],
    },
    {
        "source": "platform-capabilities.pdf",
        "chunks": [
            {
                "page": 1,
                "text": (
                    "The Enterprise RAG Platform provides the following capabilities: real-time "
                    "streaming responses with Server-Sent Events (SSE), multi-tenant document "
                    "isolation, Redis-backed caching for query results, Qdrant vector search for "
                    "semantic retrieval, OpenTelemetry distributed tracing, Prometheus metrics "
                    "collection, and Grafana dashboards for monitoring."
                ),
            },
            {
                "page": 2,
                "text": (
                    "The RAG pipeline consists of six stages: (1) Query Rewriting - reformulates "
                    "the user query for better retrieval, (2) Document Retrieval - searches Qdrant "
                    "vector database for relevant chunks, (3) Reranking - scores and sorts retrieved "
                    "documents by relevance, (4) Context Compression - extracts key information from "
                    "retrieved documents, (5) Answer Generation - produces a grounded answer using "
                    "the compressed context, (6) Citation Extraction - identifies source references "
                    "for the answer."
                ),
            },
            {
                "page": 3,
                "text": (
                    "To get the most out of the RAG platform, try asking specific questions like: "
                    "What is RAG? How does document chunking work? What are the evaluation metrics? "
                    "How do you scale a RAG system? What compliance requirements apply? The more "
                    "specific your question, the better the retrieval and answer quality."
                ),
            },
            {
                "page": 4,
                "text": (
                    "The platform runs on Docker Compose with five services: backend (FastAPI + "
                    "uvicorn on port 8000), frontend (Next.js on port 3000), PostgreSQL (metadata "
                    "storage on port 5432), Redis (caching on port 6379), and Qdrant (vector "
                    "database on ports 6333-6334). All services include health checks and "
                    "auto-restart policies."
                ),
            },
        ],
    },
]


def _make_embedding(text: str) -> list[float]:
    """Create a deterministic pseudo-embedding from text content."""
    h = hashlib.sha256(text.encode()).digest()
    random.seed(h)
    vec = [random.gauss(0, 0.3) for _ in range(VECTOR_SIZE)]
    norm = sum(v * v for v in vec) ** 0.5
    return [v / norm for v in vec]


def seed() -> None:
    client = QdrantClient(url="http://localhost:6333")

    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION in collections:
        print(f"Collection '{COLLECTION}' already exists, recreating...")
        client.delete_collection(COLLECTION)

    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    print(f"Created collection '{COLLECTION}'")

    points = []
    point_id = 1
    for doc in DOCUMENTS:
        for chunk in doc["chunks"]:
            embedding = _make_embedding(chunk["text"])
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": chunk["text"],
                        "tenant_id": TENANT_ID,
                        "metadata": {
                            "source": doc["source"],
                            "page": chunk["page"],
                        },
                    },
                )
            )
            point_id += 1

    client.upsert(collection_name=COLLECTION, points=points)
    print(f"Inserted {len(points)} document chunks")

    info = client.get_collection(COLLECTION)
    print(f"Collection '{COLLECTION}': {info.points_count} points, status={info.status}")


if __name__ == "__main__":
    seed()
