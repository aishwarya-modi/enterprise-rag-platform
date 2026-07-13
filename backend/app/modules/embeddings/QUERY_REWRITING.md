# Query rewriting

## HyDE
- Generates a hypothetical document that would answer the query.
- Helps retrieval in sparse or semantic retrieval settings.

## Step-back prompting
- Reframes a narrow question into a broader conceptual one.
- Useful for clarifying the underlying topic.

## LLM query rewriting
- Uses an LLM-style rewrite to make the query more retrieval-friendly.
- Best when you want explicit rewrite quality.

## Multi-query generation
- Expands a user query into multiple retrieval queries.
- Improves recall for broad or ambiguous questions.

## Intent detection
- Discerns the likely intent behind a query before rewriting.
- Helps select the most appropriate rewrite strategy.

## Conversation-aware rewriting
- Includes previous turns in the rewritten query.
- Useful for follow-up or ambiguous questions.

## Evaluation
- The evaluator reports the number of rewritten queries and average query length to make improvements measurable.
