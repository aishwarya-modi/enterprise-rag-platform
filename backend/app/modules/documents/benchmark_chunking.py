from __future__ import annotations

from app.modules.documents.chunking import ChunkingConfig, ChunkingStrategy, chunk_text


SAMPLE_TEXT = """
# Overview
This section introduces the product and why the team built it.

## Architecture
The architecture uses a modular backend and a responsive frontend.

## Retrieval Strategy
Chunking improves retrieval quality by preserving context around each segment.

## Benchmarks
Benchmarks help compare strategies such as recursive, semantic, markdown, parent-child, and sliding window.
"""


def run_benchmarks() -> None:
    strategies = [
        ChunkingStrategy.recursive,
        ChunkingStrategy.semantic,
        ChunkingStrategy.markdown,
        ChunkingStrategy.parent_child,
        ChunkingStrategy.sliding_window,
    ]

    for strategy in strategies:
        config = ChunkingConfig(strategy=strategy, chunk_size=20, overlap=5)
        chunks = chunk_text(SAMPLE_TEXT, config)
        average_words = sum(len(chunk["text"].split()) for chunk in chunks) / max(len(chunks), 1)
        print(f"{strategy.value}: chunks={len(chunks)} avg_words={average_words:.2f}")


if __name__ == "__main__":
    run_benchmarks()
