# Intelligent Chunking Strategies

## Recursive Chunking
- Splits content by the largest semantic separator first and then progressively smaller ones.
- Best for general-purpose retrieval where the input is mostly prose.

## Semantic Chunking
- Groups paragraphs into chunks by topic boundaries rather than fixed token windows.
- Best when preserving topical coherence matters more than strict length.

## Markdown Chunking
- Keeps Markdown headings and sections together.
- Best for documentation, knowledge bases, and code-heavy notes.

## Parent-Child Chunking
- Creates a larger parent chunk with smaller child chunks that link back to it.
- Best when you want both broad context and detailed retrieval candidates.

## Sliding Window
- Moves a window over the text with overlap to preserve continuity across boundaries.
- Best for long-form content where nearby context should remain available.

## Benchmarks
- Run the benchmark script with:
  - `python -m app.modules.documents.benchmark_chunking`
- The script reports the number of chunks and the average chunk size for each strategy.
