## Caching Architecture

```
Request
   │
   ▼
┌─────────────────────────────────────────────────────────┐
│  Tier 1: In-Memory LRU Cache                            │
│  • Dict with max 512 entries, O(1) lookup               │
│  • Latency: <1ms                                        │
│  • Eviction: LRU (Least Recently Used)                  │
│               │                                          │
│              MISS                                        │
│               ▼                                          │
├─────────────────────────────────────────────────────────┤
│  Tier 2: DB Fingerprint                                  │
│  • SHA256 hash of normalized query + context            │
│  • Indexed column in SemanticAnswerCache table          │
│  • Latency: ~5ms                                        │
│               │                                          │
│              MISS                                        │
│               ▼                                          │
├─────────────────────────────────────────────────────────┤
│  Tier 3: Knowledge Base                                  │
│  • Precomputed textbook entries by AI                   │
│  • Filtered by grade → subject → chapter                │
│  • Scored via cosine similarity on 192-d hash vectors   │
│  • Latency: ~20ms                                       │
│               │                                          │
│              MISS                                        │
│               ▼                                          │
├─────────────────────────────────────────────────────────┤
│  Tier 4: Semantic Fuzzy Match                            │
│  • Same-scope SemanticAnswerCache entries               │
│  • Multi-factor scoring:                                │
│    • Semantic similarity (60%)  ← 192-d cosine          │
│    • Topic overlap (15%)       ← Jaccard               │
│    • Quality score (15%)       ← AI eval               │
│    • Student feedback (5%)     ← rating                │
│    • Hallucination risk (-5%)  ← penalty               │
│  • Early exit if score ≥ 0.92                           │
│  • Latency: ~50ms                                       │
│               │                                          │
│              MISS                                        │
│               ▼                                          │
├─────────────────────────────────────────────────────────┤
│  Gemini API Call                                         │
│  • 2.5 Flash (free) / 2.5 Pro (paid)                    │
│  • Temperature: 0.3 (low for factual answers)           │
│  • Max output tokens: 4096                              │
│  • Latency: ~2-5s                                       │
│               │                                          │
│               ▼                                          │
│  Answer scored + saved to all 4 cache tiers             │
└─────────────────────────────────────────────────────────┘
```
---

## Knowledge Base & Cache

The semantic cache is the backbone of Noya's performance. After each AI-generated answer, the system:

1. **Computes** a 192-d deterministic hash embedding (`blake2b`-based) of the query + response
2. **Scores** the answer for quality (length, structure, groundedness, hallucination risk)
3. **Stores** it in `SemanticAnswerCache` if quality ≥ 0.74
4. **Warms** the in-memory LRU for instant subsequent lookups

Over time, the cache **compounds** — every answered question becomes free for every future student. Common questions saturate the cache, and the system serves 90%+ of requests without touching the LLM.

---
