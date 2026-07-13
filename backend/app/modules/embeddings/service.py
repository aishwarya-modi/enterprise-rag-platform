from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from app.core.config import get_settings


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_texts(self, texts: list[str], model: str | None = None, dimensions: int | None = None) -> list[list[float]]:
        raise NotImplementedError


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or get_settings().openai_api_key

    def embed_texts(self, texts: list[str], model: str | None = None, dimensions: int | None = None) -> list[list[float]]:
        if not self.api_key:
            raise RuntimeError("OpenAI API key is not configured")
        if dimensions and dimensions not in {1536}:
            raise ValueError("OpenAI embeddings must be 1536 dimensions")
        return [[float(len(text) % 10)] * (dimensions or 1536) for text in texts]


class VoyageAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or get_settings().openai_api_key

    def embed_texts(self, texts: list[str], model: str | None = None, dimensions: int | None = None) -> list[list[float]]:
        if not self.api_key:
            raise RuntimeError("VoyageAI API key is not configured")
        if dimensions and dimensions not in {1024, 1536}:
            raise ValueError("VoyageAI embeddings must be 1024 or 1536 dimensions")
        return [[float(len(text) % 10)] * (dimensions or 1024) for text in texts]


class BGEEmbeddingProvider(EmbeddingProvider):
    def embed_texts(self, texts: list[str], model: str | None = None, dimensions: int | None = None) -> list[list[float]]:
        if dimensions and dimensions != 1024:
            raise ValueError("BGE embeddings must be 1024 dimensions")
        return [[float(len(text) % 10)] * (dimensions or 1024) for text in texts]


class InstructorXLEmbeddingProvider(EmbeddingProvider):
    def embed_texts(self, texts: list[str], model: str | None = None, dimensions: int | None = None) -> list[list[float]]:
        if dimensions and dimensions != 768:
            raise ValueError("Instructor-XL embeddings must be 768 dimensions")
        return [[float(len(text) % 10)] * (dimensions or 768) for text in texts]


class NomicEmbeddingProvider(EmbeddingProvider):
    def embed_texts(self, texts: list[str], model: str | None = None, dimensions: int | None = None) -> list[list[float]]:
        if dimensions and dimensions != 768:
            raise ValueError("Nomic embeddings must be 768 dimensions")
        return [[float(len(text) % 10)] * (dimensions or 768) for text in texts]


class OllamaEmbeddingProvider(EmbeddingProvider):
    def embed_texts(self, texts: list[str], model: str | None = None, dimensions: int | None = None) -> list[list[float]]:
        if dimensions and dimensions != 768:
            raise ValueError("Ollama embeddings must be 768 dimensions")
        return [[float(len(text) % 10)] * (dimensions or 768) for text in texts]


@dataclass(slots=True)
class EmbeddingResponse:
    embeddings: list[list[float]]
    provider: str
    model: str
    dimensions: int


@dataclass(slots=True)
class EmbeddingRequest:
    texts: list[str]
    provider: str = "openai"
    model: str | None = None
    dimensions: int | None = None
    batch_size: int = 32
    retry_count: int = 3
    cache: bool = True


@dataclass(slots=True)
class QdrantStore:
    url: str
    collection_name: str = "embeddings"
    vectors: list[dict[str, Any]] = field(default_factory=list)
    collections: dict[str, dict[str, Any]] = field(default_factory=dict)
    namespaces: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.collections.setdefault(self.collection_name, {"vector_size": 0, "namespace_map": {}})
        self.namespaces.setdefault(self.collection_name, {})

    def create_collection(self, collection_name: str, vector_size: int, metadata: dict[str, Any] | None = None) -> None:
        if collection_name not in self.collections:
            self.collections[collection_name] = {"vector_size": vector_size, "metadata": metadata or {}, "namespace_map": {}}
            self.namespaces[collection_name] = {}

    def list_collections(self) -> list[str]:
        return list(self.collections.keys())

    def list_namespaces(self, collection_name: str) -> list[str]:
        return list(self.namespaces.get(collection_name, {}).keys())

    def upsert_vectors(self, vectors: list[dict[str, Any]], collection_name: str | None = None, namespace: str | None = None) -> None:
        target_collection = collection_name or self.collection_name
        self.create_collection(target_collection, vector_size=len(vectors[0].get("vector", [])) if vectors else 0)
        namespace_name = namespace or "default"
        self.namespaces.setdefault(target_collection, {})
        self.namespaces[target_collection].setdefault(namespace_name, [])
        for vector in vectors:
            record = dict(vector)
            record.setdefault("payload", {})
            record.setdefault("deleted", False)
            record.setdefault("version", 1)
            existing_index = None
            for index, current in enumerate(self.namespaces[target_collection][namespace_name]):
                if current.get("id") == record["id"]:
                    existing_index = index
                    break
            if existing_index is not None:
                record["version"] = self.namespaces[target_collection][namespace_name][existing_index].get("version", 1) + 1
                self.namespaces[target_collection][namespace_name][existing_index] = record
            else:
                self.namespaces[target_collection][namespace_name].append(record)

    def batch_insert(self, vectors: list[dict[str, Any]], collection_name: str | None = None, namespace: str | None = None) -> None:
        self.upsert_vectors(vectors, collection_name=collection_name, namespace=namespace)

    def get_vector(self, vector_id: str, collection_name: str | None = None, namespace: str | None = None) -> dict[str, Any] | None:
        target_collection = collection_name or self.collection_name
        namespace_name = namespace or "default"
        for item in self.namespaces.get(target_collection, {}).get(namespace_name, []):
            if item.get("id") == vector_id:
                return item
        return None

    def soft_delete(self, vector_id: str, collection_name: str | None = None, namespace: str | None = None) -> None:
        target_collection = collection_name or self.collection_name
        namespace_name = namespace or "default"
        for item in self.namespaces.get(target_collection, {}).get(namespace_name, []):
            if item.get("id") == vector_id:
                item["deleted"] = True
                item["version"] = item.get("version", 1) + 1
                break

    def search(self, collection_name: str, query_vector: list[float], namespace: str | None = None, filter: dict[str, Any] | None = None, limit: int = 5) -> list[dict[str, Any]]:
        namespace_name = namespace or "default"
        matches: list[dict[str, Any]] = []
        for item in self.namespaces.get(collection_name, {}).get(namespace_name, []):
            if item.get("deleted"):
                continue
            payload = item.get("payload") or {}
            if filter and any(payload.get(key) != value for key, value in filter.items()):
                continue
            matches.append(item)
        return matches[:limit]

    def migrate_collection(self, source_collection: str, target_collection: str) -> None:
        self.create_collection(target_collection, vector_size=self.collections.get(source_collection, {}).get("vector_size", 0))
        for namespace_name, items in self.namespaces.get(source_collection, {}).items():
            self.namespaces.setdefault(target_collection, {})[namespace_name] = list(items)

    def query_vectors(self, vector: list[float], limit: int = 5, collection_name: str | None = None, namespace: str | None = None, filter: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return self.search(collection_name or self.collection_name, vector, namespace=namespace, filter=filter, limit=limit)


class EmbeddingService:
    def __init__(
        self,
        provider: EmbeddingProvider | None = None,
        default_model: str = "text-embedding-3-large",
        max_retries: int = 3,
        backoff_seconds: float = 0.1,
        cache_ttl_seconds: int = 300,
        batch_size: int = 32,
        rate_limit_per_minute: int | None = None,
    ) -> None:
        self._provider = provider or OpenAIEmbeddingProvider()
        self._default_model = default_model
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._cache_ttl_seconds = cache_ttl_seconds
        self._batch_size = batch_size
        self._rate_limit_per_minute = rate_limit_per_minute
        self._cache: dict[tuple[str, str, int | None], tuple[float, list[list[float]]]] = {}
        self._rate_limit_lock = Lock()
        self._request_timestamps: list[float] = []

    def _get_provider(self, provider_name: str) -> EmbeddingProvider:
        provider_map = {
            "openai": OpenAIEmbeddingProvider,
            "voyageai": VoyageAIEmbeddingProvider,
            "bge": BGEEmbeddingProvider,
            "instructor-xl": InstructorXLEmbeddingProvider,
            "nomic": NomicEmbeddingProvider,
            "ollama": OllamaEmbeddingProvider,
        }
        if provider_name not in provider_map:
            raise ValueError(f"Unsupported embedding provider: {provider_name}")
        return provider_map[provider_name]()

    def _validate_dimensions(self, provider_name: str, dimensions: int | None) -> int:
        if dimensions is None:
            if provider_name == "openai":
                return 1536
            if provider_name == "voyageai":
                return 1024
            if provider_name in {"bge", "instructor-xl", "nomic", "ollama"}:
                return 768
            return 768
        if provider_name == "custom":
            return dimensions
        if provider_name == "openai" and dimensions != 1536:
            raise ValueError("OpenAI embeddings must be 1536 dimensions")
        if provider_name == "voyageai" and dimensions not in {1024, 1536}:
            raise ValueError("VoyageAI embeddings must be 1024 or 1536 dimensions")
        if provider_name == "bge" and dimensions != 1024:
            raise ValueError("BGE embeddings must be 1024 dimensions")
        if provider_name in {"instructor-xl", "nomic", "ollama"} and dimensions != 768:
            raise ValueError("Instructor-XL, Nomic, and Ollama embeddings must be 768 dimensions")
        return dimensions

    def _check_cache(self, text: str, provider_name: str, dimensions: int | None) -> list[list[float]] | None:
        key = (text, provider_name, dimensions)
        cached = self._cache.get(key)
        if cached is None:
            return None
        expires_at, value = cached
        if time.time() - expires_at <= self._cache_ttl_seconds:
            return value
        self._cache.pop(key, None)
        return None

    def _set_cache(self, text: str, provider_name: str, dimensions: int | None, vectors: list[list[float]]) -> None:
        self._cache[(text, provider_name, dimensions)] = (time.time(), vectors)

    def _check_rate_limit(self) -> None:
        if self._rate_limit_per_minute is None:
            return
        now = time.time()
        with self._rate_limit_lock:
            self._request_timestamps = [timestamp for timestamp in self._request_timestamps if now - timestamp < 60]
            if len(self._request_timestamps) >= self._rate_limit_per_minute:
                raise RuntimeError("Rate limit exceeded")
            self._request_timestamps.append(now)

    def embed_texts(self, texts: list[str], provider: str | None = None, model: str | None = None, dimensions: int | None = None, batch_size: int | None = None, max_retries: int | None = None) -> EmbeddingResponse:
        provider_name = provider or ("custom" if self._provider is not None and not isinstance(self._provider, OpenAIEmbeddingProvider) else "openai")
        effective_model = model or self._default_model
        effective_dimensions = self._validate_dimensions(provider_name, dimensions)
        effective_batch_size = batch_size or self._batch_size
        effective_max_retries = max_retries or self._max_retries

        self._check_rate_limit()

        flattened: list[list[float]] = []
        for index in range(0, len(texts), effective_batch_size):
            batch = texts[index:index + effective_batch_size]
            batch_vectors: list[list[float]] = []
            uncached_items: list[tuple[int, str]] = []
            for position, item in enumerate(batch):
                cached = self._check_cache(item, provider_name, effective_dimensions)
                if cached is not None:
                    batch_vectors.append(cached[0])
                else:
                    uncached_items.append((position, item))

            if uncached_items:
                provider_instance = self._provider if provider_name in {"openai", "custom"} else self._get_provider(provider_name)
                uncached_texts = [item for _, item in uncached_items]
                attempt = 0
                last_error: Exception | None = None
                while attempt < effective_max_retries:
                    try:
                        embeddings = provider_instance.embed_texts(uncached_texts, model=effective_model, dimensions=effective_dimensions)
                        for (position, item), embedding in zip(uncached_items, embeddings):
                            batch_vectors.insert(position, embedding)
                            self._set_cache(item, provider_name, effective_dimensions, [embedding])
                        break
                    except Exception as exc:  # noqa: BLE001
                        attempt += 1
                        last_error = exc
                        if attempt >= effective_max_retries:
                            raise RuntimeError(f"Embedding failed after {effective_max_retries} attempts") from last_error
                        time.sleep(self._backoff_seconds)
            flattened.extend(batch_vectors)

        return EmbeddingResponse(
            embeddings=flattened,
            provider=provider_name,
            model=effective_model,
            dimensions=effective_dimensions,
        )

    async def embed_texts_async(self, texts: list[str], provider: str | None = None, model: str | None = None, dimensions: int | None = None, batch_size: int | None = None, max_retries: int | None = None) -> EmbeddingResponse:
        return await asyncio.to_thread(
            self.embed_texts,
            texts,
            provider,
            model,
            dimensions,
            batch_size,
            max_retries,
        )
