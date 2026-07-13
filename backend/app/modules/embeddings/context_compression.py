from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CompressedContextItem:
    text: str
    citation: str | None
    priority: float


class ContextCompressionService:
    """Compress retrieved context for LLM use while preserving citations and respecting budgets."""

    def __init__(self) -> None:
        self._max_sentence_length = 24

    def compress_context(self, request: dict[str, Any]) -> dict[str, Any]:
        contexts = request.get("contexts", [])
        strategy = request.get("strategy", "hybrid")
        max_tokens = int(request.get("max_tokens", 512))
        preserve_citations = bool(request.get("preserve_citations", True))

        if not contexts:
            return {
                "compressed_context": [],
                "original_token_count": 0,
                "compressed_token_count": 0,
                "removed_items": 0,
                "strategy": strategy,
            }

        normalized = self._normalize_contexts(contexts, preserve_citations)
        ranked = sorted(normalized, key=lambda item: (item["priority"], item["text"]), reverse=True)

        compressed: list[dict[str, Any]] = []
        total_tokens = 0
        removed_items = 0
        seen_texts: set[str] = set()

        for item in ranked:
            text = item["text"]
            citation = item["citation"]
            if text in seen_texts:
                removed_items += 1
                continue
            seen_texts.add(text)

            if strategy == "llm":
                text = self._compress_with_llm_style(text)
            elif strategy == "embeddings":
                text = self._compress_for_embeddings(text)
            else:
                text = self._compress_hybrid(text)

            if preserve_citations and citation:
                text = f"{text} {citation}".strip()

            token_count = self._estimate_tokens(text)
            if total_tokens + token_count > max_tokens and compressed:
                removed_items += 1
                continue

            total_tokens += token_count
            compressed.append({"text": text, "citation": citation, "priority": item["priority"]})

        return {
            "compressed_context": compressed,
            "original_token_count": self._estimate_tokens("\n".join(item["text"] for item in normalized)),
            "compressed_token_count": total_tokens,
            "removed_items": removed_items + max(0, len(normalized) - len(compressed)),
            "strategy": strategy,
        }

    def _normalize_contexts(self, contexts: list[dict[str, Any]], preserve_citations: bool) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for context in contexts:
            text = str(context.get("text", "")).strip()
            if not text:
                continue
            citation = context.get("citation") if preserve_citations else None
            priority = float(context.get("priority", 0.0))
            normalized.append({"text": text, "citation": citation, "priority": priority})
        return normalized

    def _compress_with_llm_style(self, text: str) -> str:
        cleaned = text.strip()
        cleaned = re.sub(r"^(the|a|an)\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip()
        if not cleaned:
            return "Context"
        if cleaned.endswith((".", "!", "?")):
            cleaned = cleaned[:-1]
        cleaned = cleaned[0].upper() + cleaned[1:]
        if len(cleaned) > self._max_sentence_length:
            cleaned = cleaned[: self._max_sentence_length].rstrip() + "..."
        return cleaned

    def _compress_for_embeddings(self, text: str) -> str:
        tokens = re.findall(r"\w+|[^\w\s]", text)
        if len(tokens) <= 12:
            return text
        return " ".join(tokens[:12])

    def _compress_hybrid(self, text: str) -> str:
        return self._compress_with_llm_style(text)

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(re.findall(r"\S+", text)))
