# Answer cache and knowledge base

This page describes `api/semantic_cache.py` and the way `AIService.chat()` calls it. The implementation is a database-backed answer cache with an in-process hot cache; it is not a separate cache service or a background pipeline.

## Lookup order

For each query, the service normalizes the text, derives a grade/subject/unit/chapter scope, infers an intent and topic, extracts any exercise reference, and creates a deterministic 192-element hashed-token vector. It then checks:

1. **Process-local LRU:** up to 512 recently used answers. Each Django process has its own memory cache; it is not shared across workers and disappears on restart.
2. **Exact semantic-cache fingerprint:** an active `SemanticAnswerCache` row with the same scope, intent, and fingerprint.
3. **Precomputed knowledge base:** active `KnowledgeBaseEntry` rows scoped to the chapter first, then the subject. Candidates are ranked using the stored vector, topic overlap, quality, feedback, and risk.
4. **Fuzzy semantic-answer cache:** active `SemanticAnswerCache` candidates scoped to the chapter first, then the subject.

The cache and knowledge-base checks require the same exercise reference. A query naming a specific exercise does not match an entry for a different exercise or an entry with no exercise reference.

The candidate score is calculated in code as:

```text
0.60 * cosine similarity
+ 0.15 * topic-token overlap
+ 0.15 * quality score
+ 0.05 * normalized feedback score
- 0.05 * hallucination risk
```

The knowledge-base threshold is `0.80`. The fuzzy cache threshold is `0.75` for free and `0.85` for paid. A candidate must also be active, have a non-empty answer, a quality score of at least `0.60`, and hallucination risk no higher than `0.50`.

`inspect()` returns `CACHE_HIT`, `KNOWLEDGE_BASE_HIT`, or `AI_REQUIRED`. The chat flow checks this cache before falling through to Qdrant retrieval; `RETRIEVAL_HIT` is defined as a constant but is not returned by the current lookup implementation.

## Database records and learning

`KnowledgeBaseEntry` contains precomputed/reviewable answer material. `SemanticAnswerCache` contains answers learned from AI responses. Both use the shared educational fields in `EducationalContentBase`: subject, grade, chapter, intent, normalized query, fingerprint, JSON vector, quality fields, answer, and active status. `CacheLookupEvent` records the original message, normalized query, query scope, decision, confidence, and timing for cache inspections.

After a live answer, `learn_from_ai()` saves it only if it is at least 120 characters, passes the current marker checks, and meets the heuristic quality threshold (default `0.74`). It calculates quality, alignment, and risk using code-based heuristics; it does not call a separate evaluator model. Accepted answers are written to `SemanticAnswerCache` and added to that process's LRU.

Both free and paid chat requests can return cache or knowledge-base answers directly. Although the module contains a `context_for_paid_generation()` helper, the current `AIService.chat()` path does not call it.

## Operational endpoints and commands

- `POST /api/cache/inspect/` inspects a query; requires authentication.
- `GET /api/cache/knowledge/` lists active entries; requires authentication. `POST` creates an entry and additionally requires staff access.
- `POST /api/cache/process-content/` uses Gemini to turn supplied text into answer entries; requires staff access.
- `GET /api/cache/answers/` lists active learned entries; requires authentication.
- `GET /api/cache/metrics/` reports decisions from the latest 1,000 events; requires authentication.
- `POST /api/cache/clear/` clears only the current process's in-memory LRU. It does not delete database entries.
- `python manage.py purge_cache` clears the LRU and database cache/knowledge records. Options include `--memory-only`, `--keep-kb`, and `--events`.
- `python manage.py precompute_textbook_cache` builds knowledge-base entries from local PDFs. It supports `--subjects`, `--limit`, `--dry-run`, `--skip-existing`, OCR options, and `--raw-only`; see the command's `--help` for the exact flags.

The precompute command needs the local PDF files described in [RAG and textbook context](RAG_PIPELINE.md). No Celery worker, Redis cache, periodic refresh, scheduled re-verification, or pgvector index is configured in this repository.

