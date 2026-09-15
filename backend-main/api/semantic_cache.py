import hashlib
import math
import re
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from django.db.models import F
from django.utils import timezone

from .models import CacheLookupEvent, KnowledgeBaseEntry, SemanticAnswerCache
from .curriculum_scope import normalize_subject


DECISION_CACHE_HIT = "CACHE_HIT"
DECISION_KB_HIT = "KNOWLEDGE_BASE_HIT"
DECISION_RETRIEVAL_HIT = "RETRIEVAL_HIT"
DECISION_AI_REQUIRED = "AI_REQUIRED"

INTENT_ALIASES = {
    "explain": {"explain", "meaning", "understand", "easy words", "simple", "simply", "beginners", "what is", "what are", "how does", "describe", "tell me about"},
    "definition": {"define", "definition", "meaning of", "what do you mean", "what is the meaning"},
    "exam_notes": {"exam notes", "notes", "important points", "memorize", "see notes", "key points", "revision notes", "study notes"},
    "important_questions": {"important questions", "5 marks", "question", "questions", "likely questions", "expected questions", "exam questions", "possible questions"},
    "summary": {"summary", "summarize", "short summary", "short", "brief", "overview", "gist", "main points"},
    "quiz": {"quiz", "test me", "mcq", "practice", "mock test", "objective questions"},
    "solved_exercise": {"solve", "answer", "exercise", "numerical", "solution", "work out", "calculate", "find the value"},
    "derivation": {"derive", "derivation", "prove", "show that", "deduce"},
    "formula": {"formula", "equation", "law", "principle", "rule"},
    "page_explanation": {"page", "whole page"},
    "examples": {"example", "examples", "give example", "illustrate", "instance"},
    "differences": {"difference", "differences", "compare", "contrast", "distinguish", "vs", "versus"},
}

STOPWORDS = {
    "a", "an", "the", "is", "are", "am", "was", "were", "be", "been", "being",
    "can", "could", "would", "should", "please", "for", "me", "to", "of", "in",
    "on", "from", "and", "or", "with", "this", "that", "these", "those", "chapter",
    "unit", "lesson", "explain", "tell", "about", "give", "make", "what", "how",
    "why", "when", "where", "who", "which", "there", "here", "it", "its", "it's",
}


# ─── Exercise reference extraction (anti cross-exercise contamination) ────

_DEVANAGARI_DIGITS = "०१२३४५६७८९"

_EXERCISE_WORD = r"\b(?:exercise|exer\.?|ex\.?|अभ्यास)"
_QUESTION_WORD = r"(?:question|ques\.?|q\.?|number|no\.?|num\.?|प्रश्न)"


def _to_arabic_digits(text: str) -> str:
    return str(text or "").translate(str.maketrans(_DEVANAGARI_DIGITS, "0123456789"))


def extract_exercise_refs(text: str) -> List[str]:
    """Extract all explicit exercise references from a message.

    Each ref is a composite "exercise[#question]" string, e.g.:
        "solve exercise 7.3 question 2"  -> ["7.3#2"]
        "explain ex 7.1"                 -> ["7.1"]
        "7.2 no. 4"                      -> ["7.2#4"]
    Returns [] when the message names no explicit exercise.
    """
    if not text:
        return []
    normalized = _to_arabic_digits(text)
    refs: List[str] = []
    seen = set()
    for match in re.finditer(
        rf"{_EXERCISE_WORD}\s*([0-9]+(?:\.[0-9]+)?)(?:\s*{_QUESTION_WORD}\s*([0-9]+))?",
        normalized,
        re.IGNORECASE,
    ):
        ref = match.group(1) + (f"#{match.group(2)}" if match.group(2) else "")
        if ref not in seen:
            seen.add(ref)
            refs.append(ref)
    for match in re.finditer(
        rf"\b([0-9]+(?:\.[0-9]+)?)\s*{_QUESTION_WORD}\s*([0-9]+)\b",
        normalized,
        re.IGNORECASE,
    ):
        ref = f"{match.group(1)}#{match.group(2)}"
        if ref not in seen:
            seen.add(ref)
            refs.append(ref)
    return refs


def extract_exercise_ref(text: str) -> str:
    """First explicit exercise reference in the message, or '' if none."""
    refs = extract_exercise_refs(text)
    return refs[0] if refs else ""


@dataclass
class CacheDecision:
    decision: str
    answer: str = ""
    source: str = ""
    confidence: float = 0.0
    matched_cache: Optional[SemanticAnswerCache] = None
    matched_kb: Optional[KnowledgeBaseEntry] = None
    metadata: Optional[Dict] = None


# ─── In-memory LRU cache (fastest tier) ───────────────────

class _LRUCache:
    """Thread-unsafe in-memory LRU for hot query answers."""

    def __init__(self, maxsize: int = 512):
        self._cache: OrderedDict = OrderedDict()
        self._maxsize = maxsize

    def _key(self, scope: Dict, intent: str, normalized: str, exercise_ref: str = "") -> str:
        """Deterministic cache key."""
        subject = normalize_subject(scope.get("subject", ""))
        chapter = str(scope.get("chapter", ""))
        unit = str(scope.get("unit", ""))
        grade = str(scope.get("grade", "10"))
        # Intent + exercise ref + first 8 content tokens create a robust key.
        # The exercise ref is critical: without it "exercise 7.1" and
        # "exercise 7.3" normalize to near-identical token streams.
        tokens = " ".join(tokenize(normalized)[:8])
        raw = f"{grade}|{subject}|{unit}|{chapter}|{intent}|{exercise_ref}|{tokens}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    def get(self, scope: Dict, intent: str, normalized: str, exercise_ref: str = "") -> Optional[Tuple[str, float]]:
        key = self._key(scope, intent, normalized, exercise_ref)
        if key in self._cache:
            answer, quality = self._cache.pop(key)
            self._cache[key] = (answer, quality)  # move to end (MRU)
            return answer, quality
        return None

    def put(self, scope: Dict, intent: str, normalized: str, answer: str, quality: float = 0.95, exercise_ref: str = ""):
        key = self._key(scope, intent, normalized, exercise_ref)
        if key in self._cache:
            self._cache.pop(key)
        elif len(self._cache) >= self._maxsize:
            self._cache.popitem(last=False)
        self._cache[key] = (answer, quality)

    def clear(self):
        self._cache.clear()


# ─── Query normalization ────────────────────────────────────

def normalize_query(text: str) -> str:
    text = str(text or "").lower()
    # Keep Devanagari and English alphanumeric
    text = re.sub(r"[^a-z0-9\u0900-\u097f\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def infer_intent(text: str, study_mode: str = "") -> str:
    haystack = normalize_query(f"{study_mode} {text}")
    scores = {}
    for intent, aliases in INTENT_ALIASES.items():
        score = sum(1 for alias in aliases if alias in haystack)
        if score:
            scores[intent] = score
    if scores:
        return max(scores, key=scores.get)
    # Default based on question structure
    if any(text.lower().startswith(w) for w in ["what", "define", "describe"]):
        return "explain"
    if any(text.lower().startswith(w) for w in ["solve", "calculate", "find", "prove"]):
        return "solved_exercise"
    if any(text.lower().startswith(w) for w in ["difference", "compare", "distinguish"]):
        return "differences"
    return "explain"


def tokenize(text: str) -> List[str]:
    return [token for token in normalize_query(text).split() if token and token not in STOPWORDS]


def extract_topic(text: str, context: Dict = None) -> str:
    context = context or {}
    chapter_title = normalize_query(context.get("chapter_title", ""))
    tokens = tokenize(text)
    if chapter_title and len(tokens) <= 4:
        return chapter_title
    return " ".join(tokens[:8]) or chapter_title


def embed_text(text: str, dims: int = 192) -> List[float]:
    """Stable hashing embedding. Fast and deterministic."""
    vector = [0.0] * dims
    tokens = tokenize(text)
    if not tokens:
        return vector
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % dims
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def cosine_similarity(left: List[float], right: List[float]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    if not size:
        return 0.0
    dot = sum(float(left[i]) * float(right[i]) for i in range(size))
    left_norm = math.sqrt(sum(float(value) * float(value) for value in left[:size]))
    right_norm = math.sqrt(sum(float(value) * float(value) for value in right[:size]))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def scope_filters(context: Dict = None) -> Dict:
    context = context or {}
    return {
        "grade": str(context.get("grade", "10")),
        "subject": normalize_subject(context.get("subject", "")),
        "unit": str(context.get("unit", "") or ""),
        "chapter": str(context.get("chapter", "") or ""),
        "chapter_title": str(context.get("chapter_title", "") or ""),
    }


def educational_fingerprint(scope: Dict, intent: str, topic: str, normalized: str, exercise_ref: str = "") -> str:
    parts = [
        scope.get("grade", "10"),
        normalize_subject(scope.get("subject", "")),
        str(scope.get("unit", "")),
        str(scope.get("chapter", "")),
        topic,
        intent,
        exercise_ref,
        " ".join(tokenize(normalized)[:10]),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


# ─── Semantic Cache Service ─────────────────────────────────

class SemanticCacheService:
    """High-performance educational semantic cache with 3-tier lookup:
    1. In-memory LRU (O(1), <1ms)
    2. Exact DB fingerprint (indexed lookup, ~5ms)
    3. Scoped semantic match (filtered candidates, ~20-50ms)
    """

    cache_threshold = 0.85
    kb_threshold = 0.80
    free_ai_threshold = 0.75

    def __init__(self):
        self._memory = _LRUCache(maxsize=512)

    def clear(self):
        """Clear all in-memory cache entries."""
        self._memory.clear()

    # ─── Public API ─────────────────────────────────────────

    def inspect(self, message: str, context: Dict = None, user=None, plan_tier: str = "free") -> CacheDecision:
        started = time.perf_counter()
        context = context or {}
        scope = scope_filters(context)
        normalized = normalize_query(message)
        intent = infer_intent(message, context.get("study_mode", ""))
        topic = extract_topic(message, context)
        exercise_ref = extract_exercise_ref(message)
        embedding = embed_text(f"{scope.get('chapter_title', '')} {topic} {intent} {normalized}")
        fingerprint = educational_fingerprint(scope, intent, topic, normalized, exercise_ref)

        # Tier 1: In-memory LRU (fastest)
        mem_hit = self._memory.get(scope, intent, normalized, exercise_ref)
        if mem_hit:
            answer, quality = mem_hit
            decision = CacheDecision(
                decision=DECISION_CACHE_HIT,
                answer=answer,
                source="Hot Memory Cache",
                confidence=round(quality, 4),
                metadata={"intent": intent, "topic": topic, "exercise_ref": exercise_ref, "match": "memory_lru", "tier": 1},
            )
            self._record(message, normalized, scope, plan_tier, decision, started, user)
            return decision

        # Tier 2: Exact fingerprint DB match (very fast, very accurate)
        exact = self._exact_match(scope, intent, fingerprint)
        if exact and self._quality_ok(exact):
            # Defensive guard: never serve a cached answer across exercise refs
            if getattr(exact, "exercise_ref", "") == exercise_ref:
                # Warm the memory cache for next time
                self._memory.put(scope, intent, normalized, exact.answer, float(exact.quality_score or 0.9), exercise_ref)
                decision = CacheDecision(
                    decision=DECISION_CACHE_HIT,
                    answer=exact.answer,
                    source="Semantic Cache (Exact)",
                    confidence=0.99,
                    matched_cache=exact,
                    metadata={"intent": intent, "topic": topic, "exercise_ref": exercise_ref, "match": "fingerprint", "tier": 2},
                )
                self._record(message, normalized, scope, plan_tier, decision, started, user)
                self._mark_cache_hit(exact)
                return decision

        # Tier 3: Knowledge Base lookup (precomputed textbook answers)
        kb_match, kb_score = self._kb_match(scope, intent, topic, embedding, exercise_ref)
        if kb_match and kb_score >= self.kb_threshold and self._quality_ok(kb_match):
            self._memory.put(scope, intent, normalized, kb_match.answer, float(kb_match.quality_score or 0.9), exercise_ref)
            decision = CacheDecision(
                decision=DECISION_KB_HIT,
                answer=kb_match.answer,
                source="Precomputed Knowledge Base",
                confidence=round(kb_score, 4),
                matched_kb=kb_match,
                metadata={"intent": intent, "topic": topic, "exercise_ref": exercise_ref, "tier": 3},
            )
            self._record(message, normalized, scope, plan_tier, decision, started, user)
            self._mark_kb_hit(kb_match)
            return decision

        # Tier 4: Semantic cache fuzzy match (same chapter/intent candidates)
        cache_match, cache_score = self._semantic_match(scope, intent, topic, embedding, plan_tier, exercise_ref)
        threshold = self.cache_threshold if plan_tier == "paid" else self.free_ai_threshold
        if cache_match and cache_score >= threshold and self._quality_ok(cache_match):
            # Defensive guard: fuzzy tier must never cross exercise refs
            if getattr(cache_match, "exercise_ref", "") == exercise_ref:
                self._memory.put(scope, intent, normalized, cache_match.answer, float(cache_match.quality_score or 0.85), exercise_ref)
                decision = CacheDecision(
                    decision=DECISION_CACHE_HIT,
                    answer=cache_match.answer,
                    source="Semantic Cache (Fuzzy)",
                    confidence=round(cache_score, 4),
                    matched_cache=cache_match,
                    metadata={"intent": intent, "topic": topic, "exercise_ref": exercise_ref, "tier": 4},
                )
                self._record(message, normalized, scope, plan_tier, decision, started, user)
                self._mark_cache_hit(cache_match)
                return decision

        # Miss — AI required
        decision = CacheDecision(
            decision=DECISION_AI_REQUIRED,
            confidence=round(max(kb_score, cache_score), 4),
            metadata={
                "intent": intent,
                "topic": topic,
                "exercise_ref": exercise_ref,
                "fingerprint": fingerprint,
                "embedding": embedding,
                "best_kb_score": round(kb_score, 4),
                "best_cache_score": round(cache_score, 4),
            },
        )
        self._record(message, normalized, scope, plan_tier, decision, started, user)
        return decision

    def context_for_paid_generation(self, message: str, context: Dict = None) -> str:
        decision = self.inspect(message, context, user=None, plan_tier="paid")
        if decision.decision in {DECISION_CACHE_HIT, DECISION_KB_HIT} and decision.answer:
            return (
                "HIGH-QUALITY CACHED EDUCATIONAL ANSWER TO USE AS CONTEXT:\n"
                f"{decision.answer[:3500]}\n\n"
                "Use this to improve consistency, but adapt to the exact user request."
            )
        return ""

    def learn_from_ai(
        self,
        message: str,
        answer: str,
        context: Dict = None,
        source: str = "AI",
        model: str = "",
        min_quality: float = 0.74,
    ) -> Optional[SemanticAnswerCache]:
        if not answer or len(answer.strip()) < 120:
            return None
        lower_answer = answer.lower()
        if any(marker in lower_answer for marker in [
            "providers are currently rate-limited",
            "please try again in a few minutes",
            "all ai providers failed",
            "service unavailable",
            "quota",
            "name '",
            "is not defined",
            "traceback",
            "syntaxerror",
            "typeerror",
            "indexerror",
            "keyerror",
        ]):
            return None

        context = context or {}
        scope = scope_filters(context)
        normalized = normalize_query(message)
        intent = infer_intent(message, context.get("study_mode", ""))
        topic = extract_topic(message, context)
        exercise_ref = extract_exercise_ref(message)
        embedding = embed_text(f"{scope.get('chapter_title', '')} {topic} {intent} {normalized} {answer[:800]}")
        quality = self.evaluate_quality(answer, context)
        if quality["quality_score"] < min_quality:
            return None

        fingerprint = educational_fingerprint(scope, intent, topic, normalized, exercise_ref)

        # Warm memory cache immediately
        self._memory.put(scope, intent, normalized, answer, quality["quality_score"], exercise_ref)

        cache, _ = SemanticAnswerCache.objects.update_or_create(
            query_fingerprint=fingerprint,
            subject=scope["subject"],
            grade=scope["grade"],
            unit=scope["unit"],
            chapter=scope["chapter"],
            question_type=intent,
            defaults={
                "chapter_title": scope.get("chapter_title", ""),
                "topic": topic,
                "intent": intent,
                "exercise_ref": exercise_ref,
                "difficulty": str(context.get("difficulty", "easy") or "easy"),
                "normalized_query": normalized,
                "embedding": embedding,
                "answer": answer,
                "source_type": "ai_generated",
                "source_reference": source,
                "quality_score": quality["quality_score"],
                "textbook_alignment_score": quality["textbook_alignment_score"],
                "hallucination_risk_score": quality["hallucination_risk_score"],
                "last_verified_at": timezone.now(),
                "metadata": {"quality": quality, "study_mode": context.get("study_mode", "")},
                "created_from_model": model,
                "is_active": True,
            },
        )
        return cache

    def evaluate_quality(self, answer: str, context: Dict = None) -> Dict[str, float]:
        context = context or {}
        text = answer or ""
        length_score = min(len(text) / 1200, 1.0)
        structure_score = min((text.count("##") + text.count("**") + text.count("\n- ")) / 10, 1.0)
        has_sources = 1.0 if "Sources:" in text or "pp." in text or context.get("chapter") else 0.65
        refusal_penalty = 0.25 if "outside" in text.lower() and "curriculum" in text.lower() else 0.0
        hallucination_risk = max(0.05, 0.35 - (0.18 * has_sources) - (0.12 * structure_score))
        quality = max(0.0, min(1.0, 0.42 * length_score + 0.28 * structure_score + 0.25 * has_sources - refusal_penalty))
        return {
            "quality_score": round(quality, 4),
            "textbook_alignment_score": round(has_sources, 4),
            "hallucination_risk_score": round(hallucination_risk, 4),
        }

    # ─── Internal matching tiers ────────────────────────────

    def _exact_match(self, scope: Dict, intent: str, fingerprint: str) -> Optional[SemanticAnswerCache]:
        """Single-row indexed lookup."""
        return SemanticAnswerCache.objects.filter(
            is_active=True,
            query_fingerprint=fingerprint,
            grade=scope["grade"],
            subject=scope["subject"],
            question_type=intent,
        ).order_by("-quality_score", "-student_feedback_score", "-usage_count").first()

    def _kb_match(self, scope: Dict, intent: str, topic: str, embedding: List[float], exercise_ref: str = "") -> Tuple[Optional[KnowledgeBaseEntry], float]:
        """Knowledge base lookup — same chapter first, then subject-wide.

        exercise_ref is a hard filter: a query naming "exercise 7.3" can only
        match entries stored for exactly that exercise (and vice versa).
        """
        # Try exact chapter match first (most accurate)
        candidates = KnowledgeBaseEntry.objects.filter(
            is_active=True,
            grade=scope["grade"],
            subject=scope["subject"],
            chapter=scope["chapter"],
            question_type__in=["general", intent],
            exercise_ref=exercise_ref,
        ).order_by("-quality_score", "-usage_count")[:20]

        best, best_score = self._score_candidates(candidates, embedding, topic)
        if best and best_score >= self.kb_threshold:
            return best, best_score

        # Broader subject match
        if scope.get("chapter"):
            candidates = KnowledgeBaseEntry.objects.filter(
                is_active=True,
                grade=scope["grade"],
                subject=scope["subject"],
                question_type__in=["general", intent],
                exercise_ref=exercise_ref,
            ).order_by("-quality_score", "-usage_count")[:30]
            best, best_score = self._score_candidates(candidates, embedding, topic)

        return best, best_score

    def _semantic_match(self, scope: Dict, intent: str, topic: str, embedding: List[float], plan_tier: str, exercise_ref: str = "") -> Tuple[Optional[SemanticAnswerCache], float]:
        """Fuzzy semantic match — scoped to same chapter first.

        exercise_ref is a hard filter: entries cached for a different exercise
        (or with no exercise ref) are excluded entirely, never down-weighted.
        """
        # Same chapter + intent (tightest scope)
        candidates = SemanticAnswerCache.objects.filter(
            is_active=True,
            grade=scope["grade"],
            subject=scope["subject"],
            chapter=scope["chapter"],
            question_type__in=["general", intent],
            exercise_ref=exercise_ref,
        ).order_by("-quality_score", "-usage_count")[:20]

        best, best_score = self._score_candidates(candidates, embedding, topic)
        if best and best_score >= (self.cache_threshold if plan_tier == "paid" else self.free_ai_threshold):
            return best, best_score

        # Same subject + intent (broader scope)
        if scope.get("chapter"):
            candidates = SemanticAnswerCache.objects.filter(
                is_active=True,
                grade=scope["grade"],
                subject=scope["subject"],
                question_type__in=["general", intent],
                exercise_ref=exercise_ref,
            ).order_by("-quality_score", "-usage_count")[:30]
            best, best_score = self._score_candidates(candidates, embedding, topic)

        return best, best_score

    def _score_candidates(self, candidates, embedding: List[float], topic: str):
        """Score candidates with early exit on high-confidence match."""
        best = None
        best_score = 0.0
        topic_tokens = set(tokenize(topic))

        for candidate in candidates:
            # Fast topic token overlap check
            cand_topic_tokens = set(tokenize(candidate.topic or ""))
            topic_overlap = 0.0
            if topic_tokens and cand_topic_tokens:
                intersection = topic_tokens & cand_topic_tokens
                union = topic_tokens | cand_topic_tokens
                topic_overlap = len(intersection) / len(union) if union else 0.0

            # Semantic embedding similarity
            similarity = cosine_similarity(embedding, candidate.embedding or [])

            # Quality and feedback scores
            quality = max(0.0, min(1.0, float(candidate.quality_score or 0.0)))
            feedback = max(0.0, min(1.0, 0.5 + float(candidate.student_feedback_score or 0.0) / 2))
            risk = max(0.0, min(1.0, float(candidate.hallucination_risk_score or 0.0)))

            # Combined score: semantic (60%) + topic overlap (15%) + quality (15%) + feedback (5%) - risk (5%)
            score = (
                0.60 * similarity
                + 0.15 * topic_overlap
                + 0.15 * quality
                + 0.05 * feedback
                - 0.05 * risk
            )

            if score > best_score:
                best = candidate
                best_score = score

            # Early exit: if we found an excellent match, stop scanning
            if score >= 0.92:
                break

        return best, best_score

    def _quality_ok(self, item) -> bool:
        return (
            bool(item and item.is_active)
            and float(item.quality_score or 0.0) >= 0.60
            and float(item.hallucination_risk_score or 0.0) <= 0.50
            and bool((item.answer or "").strip())
        )

    def _record(self, message, normalized, scope, plan_tier, decision: CacheDecision, started, user=None):
        try:
            CacheLookupEvent.objects.create(
                user=user if getattr(user, "is_authenticated", False) else None,
                message=message or "",
                normalized_query=normalized or "",
                subject=scope.get("subject", ""),
                grade=scope.get("grade", "10"),
                unit=scope.get("unit", ""),
                chapter=scope.get("chapter", ""),
                plan_tier=plan_tier or "free",
                decision=decision.decision,
                confidence=decision.confidence,
                matched_cache=decision.matched_cache,
                matched_kb=decision.matched_kb,
                latency_ms=int((time.perf_counter() - started) * 1000),
                metadata=decision.metadata or {},
            )
        except Exception as e:
            print(f"Cache event record failed: {e}")

    def _mark_cache_hit(self, item: SemanticAnswerCache):
        SemanticAnswerCache.objects.filter(id=item.id).update(
            usage_count=F("usage_count") + 1,
            hit_count=F("hit_count") + 1,
        )

    def _mark_kb_hit(self, item: KnowledgeBaseEntry):
        KnowledgeBaseEntry.objects.filter(id=item.id).update(
            usage_count=F("usage_count") + 1,
            hit_count=F("hit_count") + 1,
        )


# Singleton
semantic_cache_service = None


def get_semantic_cache_service() -> SemanticCacheService:
    global semantic_cache_service
    if semantic_cache_service is None:
        semantic_cache_service = SemanticCacheService()
    return semantic_cache_service
