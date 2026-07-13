import pytest

from app.modules.documents.chunking import ChunkingConfig, ChunkingStrategy, chunk_text


@pytest.mark.parametrize(
    ("strategy", "expected_min_chunks"),
    [
        (ChunkingStrategy.recursive, 2),
        (ChunkingStrategy.semantic, 2),
        (ChunkingStrategy.markdown, 2),
        (ChunkingStrategy.parent_child, 3),
        (ChunkingStrategy.sliding_window, 2),
    ],
)
def test_chunking_strategies_generate_multiple_chunks(strategy: ChunkingStrategy, expected_min_chunks: int) -> None:
    text = (
        "# Summary\n\nThis is the first section of a long document with enough words to be split.\n\n"
        "## Details\n\nThis is the second section with more context and additional details for retrieval.\n\n"
        "## Next Steps\n\nThis section closes the narrative with more supportive context."
    )

    chunks = chunk_text(text, ChunkingConfig(strategy=strategy, chunk_size=20, overlap=5))

    assert len(chunks) >= expected_min_chunks
    assert all(chunk["text"] for chunk in chunks)


def test_markdown_chunking_preserves_heading_context() -> None:
    text = "# Overview\n\nA short paragraph under the overview heading.\n\n## Details\n\nMore content about the implementation."

    chunks = chunk_text(text, ChunkingConfig(strategy=ChunkingStrategy.markdown, chunk_size=10, overlap=2))

    assert any("Overview" in chunk["text"] for chunk in chunks)
    assert any("Details" in chunk["text"] for chunk in chunks)


def test_parent_child_chunking_stores_relationships() -> None:
    text = "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi."

    chunks = chunk_text(text, ChunkingConfig(strategy=ChunkingStrategy.parent_child, chunk_size=8, overlap=2))

    parents = [chunk for chunk in chunks if chunk["parent_id"] is None]
    children = [chunk for chunk in chunks if chunk["parent_id"] is not None]

    assert parents
    assert children
    assert all(chunk["children_ids"] for chunk in parents)


def test_sliding_window_uses_overlap() -> None:
    text = "one two three four five six seven eight nine ten"

    chunks = chunk_text(text, ChunkingConfig(strategy=ChunkingStrategy.sliding_window, chunk_size=5, overlap=2))

    assert len(chunks) >= 2
    assert chunks[0]["text"].split()[0] == "one"
    assert chunks[1]["text"].split()[0] == "four"
