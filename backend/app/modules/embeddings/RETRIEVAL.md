# Retrieval pipeline

## Dense retrieval
- Measures similarity between the query and a document embedding.
- Best when semantic similarity matters more than exact keyword overlap.

## BM25
- A lexical ranking model based on term frequency and inverse document frequency.
- Best when keyword precision and exact term matching matter.

## Hybrid search
- Combines dense and BM25 scores using weighted fusion.
- Best for balanced recall and precision.

## Filtering
- Metadata, date, document, and namespace filters narrow the candidate set before scoring.

## Score normalization
- Scores are normalized by the candidate count so different retrieval modes remain comparable.

## Weighted fusion
- Dense and BM25 scores are merged using configurable weights.
