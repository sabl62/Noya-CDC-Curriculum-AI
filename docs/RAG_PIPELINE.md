## RAG Pipeline

```
User Question
     │
     ▼
┌──────────────────────────────────────────────────────┐
│                 AIService.chat()                      │
│                                                      │
  │  ┌─ Chapter title provided? ─┐                       │
│  │          │                │                       │
│  │         YES               NO                      │
│  │          │                │                       │
│  │          ▼                ▼                       │
│  │  Extract PDF text    Qdrant similarity            │
│  │  for chapter pages   search (top-5 chunks)        │
│  │          │                │                       │
│  │          ▼                ▼                       │
│  │  Grounding Verification (deterministic token      │
│  │  overlap check against textbook source)           │
│  │          │                                         │
│  │          ▼                                         │
│  │  ┌─ Cache Hit? ──────────────────────────┐         │
│  │  │           │                            │         │
│  │  │          YES                          NO        │
│  │  │           │                            │         │
│  │  │           ▼                            ▼         │
│  │  │    Return cached               Gemini 2.5 Flash  │
│  │  │    answer (<50ms)              generates answer  │
│  │  │                                     │           │
│  │  │                                     ▼           │
│  │  │                              Quality scoring    │
│  │  │                                     │           │
│  │  └───────────── All paths ─────────────┘           │
│  │                                                    │
│  │  Save answer + context to ChatMessage in DB        │
│  │  Warm cache via SemanticCache.learn_from_ai()      │
│  │  Stream response to frontend via SSE               │
│  └────────────────────────────────────────────────────┘
```
