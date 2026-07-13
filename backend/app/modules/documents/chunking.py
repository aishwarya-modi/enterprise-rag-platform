from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import re


class ChunkingStrategy(str, Enum):
    recursive = "recursive"
    semantic = "semantic"
    markdown = "markdown"
    parent_child = "parent_child"
    sliding_window = "sliding_window"


@dataclass(slots=True)
class ChunkingConfig:
    strategy: ChunkingStrategy = ChunkingStrategy.recursive
    chunk_size: int = 300
    overlap: int = 50
    separators: tuple[str, ...] = ("\n\n", "\n", " ")


@dataclass(slots=True)
class Chunk:
    id: str
    text: str
    strategy: str
    start: int = 0
    end: int = 0
    parent_id: str | None = None
    children_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def chunk_text(text: str, config: ChunkingConfig | None = None) -> list[dict[str, Any]]:
    config = config or ChunkingConfig()
    normalized = text.strip()
    if not normalized:
        return []

    if config.strategy == ChunkingStrategy.markdown:
        return _chunk_markdown(normalized, config)
    if config.strategy == ChunkingStrategy.parent_child:
        return _chunk_parent_child(normalized, config)
    if config.strategy == ChunkingStrategy.sliding_window:
        return _chunk_sliding_window(normalized, config)
    if config.strategy == ChunkingStrategy.semantic:
        return _chunk_semantic(normalized, config)
    return _chunk_recursive(normalized, config)


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    step = max(1, chunk_size - overlap)
    chunks: list[str] = []
    for start in range(0, len(words), step):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        if not chunk_words:
            continue
        chunks.append(" ".join(chunk_words))
        if end >= len(words):
            break
    return chunks


def _chunk_recursive(text: str, config: ChunkingConfig) -> list[dict[str, Any]]:
    chunks = _split_text(text, config.chunk_size, config.overlap)
    return [_build_chunk(chunk, index, config.strategy.value, None, []) for index, chunk in enumerate(chunks)]


def _chunk_semantic(text: str, config: ChunkingConfig) -> list[dict[str, Any]]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks = []
    current = ""
    for paragraph in paragraphs:
        if len(current.split()) + len(paragraph.split()) > config.chunk_size:
            if current:
                chunks.append(current)
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return [_build_chunk(chunk, index, config.strategy.value, None, []) for index, chunk in enumerate(chunks)]


def _chunk_markdown(text: str, config: ChunkingConfig) -> list[dict[str, Any]]:
    lines = text.splitlines()
    chunks = []
    current_lines: list[str] = []
    for line in lines:
        current_lines.append(line)
        if len("\n".join(current_lines).split()) >= config.chunk_size:
            chunks.append("\n".join(current_lines).strip())
            current_lines = []
    if current_lines:
        chunks.append("\n".join(current_lines).strip())
    return [_build_chunk(chunk, index, config.strategy.value, None, []) for index, chunk in enumerate(chunks)]


def _chunk_parent_child(text: str, config: ChunkingConfig) -> list[dict[str, Any]]:
    chunks = _split_text(text, config.chunk_size, config.overlap)
    parent_chunk = _build_chunk(chunks[0], 0, ChunkingStrategy.parent_child.value, None, [])
    children = []
    for index, chunk in enumerate(chunks[1:], start=1):
        child_chunk = _build_chunk(chunk, index, ChunkingStrategy.parent_child.value, parent_chunk["id"], [parent_chunk["id"]])
        children.append(child_chunk)
    parent_chunk["children_ids"] = [child["id"] for child in children]
    return [parent_chunk, *children]


def _chunk_sliding_window(text: str, config: ChunkingConfig) -> list[dict[str, Any]]:
    words = text.split()
    if not words:
        return []
    step = max(1, config.chunk_size - config.overlap)
    chunks = []
    for start in range(0, len(words), step):
        end = min(start + config.chunk_size, len(words))
        chunk_words = words[start:end]
        if not chunk_words:
            continue
        chunks.append(" ".join(chunk_words))
    return [_build_chunk(chunk, index, config.strategy.value, None, []) for index, chunk in enumerate(chunks)]


def _build_chunk(text: str, index: int, strategy: str, parent_id: str | None, children_ids: list[str]) -> dict[str, Any]:
    return {
        "id": f"{strategy}-{index}",
        "text": text,
        "strategy": strategy,
        "start": 0,
        "end": len(text),
        "parent_id": parent_id,
        "children_ids": children_ids,
        "metadata": {"word_count": len(text.split())},
    }
