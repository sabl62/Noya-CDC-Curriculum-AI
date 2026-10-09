"""
AI Service for Noya AI with RAG Integration + Real Streaming
"""

import json
import logging
import os
import re
from typing import Dict, Any, Generator

import httpx

from django.utils import timezone

# Import Gemini
try:
    import google.genai as genai
    from google.genai import types as genai_types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Import RAG service
try:
    from .rag_service import get_rag_service
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

from .curriculum_scope import (
    get_scope_summary,
    is_curriculum_query,
    find_curriculum_focus,
    normalize_subject,
    out_of_scope_response_for_subject,
)
from .chapter_pdf_context import (
    get_chapter_pdf_context,
    get_chapter_text_for_selection,
)
from .semantic_cache import (
    DECISION_AI_REQUIRED,
    DECISION_CACHE_HIT,
    DECISION_KB_HIT,
    extract_exercise_ref,
    extract_exercise_refs,
    get_semantic_cache_service,
)
from .models import ChatMessage, KnowledgeBaseEntry
from .features import billing_enabled
from .error_handling import (
    SERVER_FAILURE,
    classify_provider_error,
    classify_provider_failures,
    user_error_message,
)


_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "how", "in", "is", "it", "of", "on", "or", "please", "the",
    "this", "to", "what", "when", "where", "which", "who", "why",
}

_STUDY_TERMS = {
    "answer", "calculate", "define", "derive", "differentiate", "example",
    "exercise", "explain", "find", "formula", "lesson", "number", "prove",
    "question", "show", "simplify", "solution", "solve", "unit",
}

_GEMINI_FREE_MODEL = "gemini-2.5-flash"

_INVALID_RESPONSE_MARKERS = [
    "name '", "is not defined", "traceback", "syntaxerror",
    "typeerror", "indexerror", "keyerror", "attributeerror",
    ">>> ", "import ", "def ", "print(",
]

_LATEX_MATH_INSTRUCTIONS = r"""MATH FORMATTING RULES (CRITICAL - follow exactly):

1. EVERY mathematical expression MUST be wrapped in dollar signs. NO exceptions.
   - Inline math: $\cos 2A = 2\cos^2 A - 1$
   - Display math (own line): $$\cos 2A = 2\cos^2 A - 1$$

2. NEVER write bare LaTeX commands without $ delimiters. Every single \command must be inside $...$.
   WRONG: \cos 90^\circ = 0
   RIGHT: $\cos 90^\circ = 0$

   WRONG: \frac{a}{b} = \sin \theta
   RIGHT: $\frac{a}{b} = \sin \theta$

   WRONG: 2\cos^2 \left(45^\circ - \frac{A}{2}\right) = 1 + \sin A
   RIGHT: $2\cos^2 \left(45^\circ - \frac{A}{2}\right) = 1 + \sin A$

3. NEVER use $$ inside an expression. Double $$ is ONLY for display math on its OWN line.
   WRONG: \frac{A}{2}$$\right)
   WRONG: $x = \frac{A}{2}$$
   RIGHT: $\frac{A}{2}$ inside single $, or $$\frac{A}{2}$$ on its own line

4. Each math expression gets its own $ delimiters. Do NOT merge multiple expressions into one $ block unless they are part of the same equation.
   RIGHT: $\cos 90^\circ = 0$ and $\sin 90^\circ = 1$
   RIGHT: $\cos 90^\circ = 0$ and $\sin 90^\circ = 1$ (if in same sentence)

5. Use _ for subscripts, ^ for superscripts, \frac{a}{b} for fractions.
   Example: $\sin^2 A + \cos^2 A = 1$
   Example: $\tan \frac{A}{2} = \frac{\sin A}{1 + \cos A}$

6. For submultiple angle proofs, wrap the ENTIRE equation in one $ block:
   RIGHT: $2\cos^2 \left(45^\circ - \frac{A}{2}\right) = 1 + \cos\left(2 \times \left(45^\circ - \frac{A}{2}\right)\right)$

7. NEVER output a line that contains \command outside of $...$. If you need to write text, write plain English. If you need math, wrap it in $.

FORMATTING EXAMPLE (follow this spacing exactly — note the blank line between every line):

## Given

L.H.S. = $\cos^2 \left(45^\circ - \frac{\theta}{2}\right) - \sin^2 \left(45^\circ - \frac{\theta}{2}\right)$

R.H.S. = $\sin \theta$

## Proof

**Step 1:** Apply $\cos 2A = \cos^2 A - \sin^2 A$

Let $A = 45^\circ - \frac{\theta}{2}$

L.H.S. = $\cos \left(2 \times \left(45^\circ - \frac{\theta}{2}\right)\right)$

**Step 2:** Simplify

L.H.S. = $\cos (90^\circ - \theta)$

**Step 3:** Apply $\cos(90^\circ - X) = \sin X$

L.H.S. = $\sin \theta$ = R.H.S. ✓

BAD EXAMPLE (no blank lines — everything crammed):

Step 1: Apply cos2A = cos²A - sin²A. L.H.S. = cos²(45° - θ/2) - sin²(45° - θ/2). Let A = (45° - θ/2). Then, L.H.S. = cos(2A).
"""


def _is_valid_response(text: str) -> bool:
    """Check if AI response is a valid educational answer (not a Python error or code block)."""
    if not text or len(text.strip()) < 10:
        return False
    lower = text.lower()
    return not any(marker in lower for marker in _INVALID_RESPONSE_MARKERS)


_GEMINI_FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-3.6-flash", "gemini-flash-latest"]
_DEEPSEEK_MODEL = "deepseek-v4-flash-free"
_DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1"
_CEREBRAS_ENDPOINT = "https://api.cerebras.ai/v1"
_GROQ_ENDPOINT = "https://api.groq.com/openai/v1"
_KIRA_ENDPOINT = "https://kiraai.vn/api/v1"
_KIRA_MODEL_FREE = "deepseek-v4-flash-free"

# Cheap, fast models used for the two small side-tasks (titles + question
# classification). These are separate chains from the answer models because
# both providers retire model names regularly and a 404/decommissioned model
# must not take the whole chat path down with it.
_GROQ_TITLE_MODEL = os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")
_GROQ_TITLE_FALLBACKS = ["qwen/qwen3.8-27b", "openai/gpt-oss-20b", "openai/gpt-oss-120b"]

# A failure that names the *model* is the only kind another model can fix.
# Auth, quota and rate-limit errors fail identically for every model, so they
# must abort the chain instead of silently burning every key against it.
_MODEL_UNAVAILABLE_MARKERS = (
    "model_decommissioned",
    "model_not_found",
    "decommissioned",
    "model not found",
    "not supported or not configured",
    "invalid model",
    "unknown model",
    "is not supported",
    "http 404",
)


def _is_model_unavailable_error(error: Exception) -> bool:
    """True when the failure is about the model name, so another model may work."""
    text = str(error).lower()
    return any(marker in text for marker in _MODEL_UNAVAILABLE_MARKERS)


def _model_chain(primary: str, fallbacks: list) -> list:
    return [primary] + [m for m in fallbacks if m != primary]


_TITLE_SYSTEM_PROMPT = (
    "You generate short chat titles for a student study assistant. "
    "Rules:\n"
    "- 3 to 6 words maximum\n"
    "- Be SPECIFIC to the topic (mention the concept, not just 'question')\n"
    "- Use title case\n"
    "- Never start with 'Ask', 'Solve', 'Explain', 'This' — start with the topic name\n"
    "- Examples of GOOD titles: 'Compound Interest Formula', 'Photosynthesis Process', 'Quadratic Equations', 'Newton's Laws of Motion'\n"
    "- Examples of BAD titles: 'Solve Exercise', 'This Simply', 'Math Question', 'Study Help'\n"
    "- Respond with ONLY the title, no quotes, no punctuation"
)

# Leading words that make a title vague rather than descriptive.
_TITLE_NOISE_PREFIX = re.compile(
    r"^(?:"
    r"what(?:'s| is| are)?|explain|describe|define|"
    r"how (?:do|does|did|to|can|could|is|are)|"
    r"why (?:do|does|did|is|are|was|were)|"
    r"when (?:do|does|did|is|are|was|were)|"
    r"where (?:do|does|did|is|are|was|were)|"
    r"who(?:'s| is| are| was| were)?|"
    r"solve|find|calculate|compute|show|tell me|give me|help me|"
    r"can you|i (?:want|need|would like)(?: to)?|please|"
    r"write|read|practice|teach|help|"
    r"steps?(?: to)?|difference between"
    r")\s+"
    # Optional filler that follows the trigger verb: "explain ME ABOUT the ...".
    r"(?:me\s+)?(?:about\s+|us\s+on\s+|on\s+|the\s+|this\s+)?",
    flags=re.IGNORECASE,
)

# Sentence punctuation only — a period between digits is part of a decimal or
# an exercise number ("7.1", "9.8") and must survive.
_TITLE_SENTENCE_PUNCT = re.compile(r"(?<!\d)[.!?]+|[.!?]+(?!\d)")


def _truncate_title(text: str) -> str:
    """Cap a title at 6 words / 50 chars without cutting a word in half."""
    words = text.split()
    if len(words) > 6:
        text = " ".join(words[:6])
    if len(text) > 50:
        text = text[:50].rsplit(" ", 1)[0]
    return text.strip()


def _clean_title(raw: str) -> str:
    """Normalise a model-generated title, rejecting anything unusable.

    Small models like to answer with quotes, markdown, a 'Title:' prefix or a
    sentence of commentary. Anything that is not 2-6 usable words is discarded
    so the caller can move on to the next provider.
    """
    if not raw:
        return ""

    # Keep only the first line — models sometimes add an explanation below it.
    # Guard the index: a whitespace-only completion strips down to no lines.
    first_line = raw.strip().splitlines()
    if not first_line:
        return ""
    text = first_line[0].strip()
    text = text.strip("*_` ")
    text = re.sub(r"^(?:title|t)\s*[:\-–]\s*", "", text, flags=re.IGNORECASE)
    text = text.strip().strip("\"'“”‘’").strip()
    # Re-strip emphasis after the punctuation pass so "**Law**." -> "Law".
    text = _TITLE_SENTENCE_PUNCT.sub(" ", text)
    text = text.strip().strip("*_` ").strip()

    if not text:
        return ""

    text = _truncate_title(text)
    words = text.split()
    if len(words) < 2 or len(text) < 4:
        return ""
    return text


def _heuristic_title(message: str) -> str:
    """Deterministic last-resort title derived from the student's own words."""
    text = (message or "").strip()
    if not text:
        return "New Chat"

    # A pasted question can carry an exercise number or a leading number;
    # keep those, they are often the most identifying part of the title.
    text = _TITLE_NOISE_PREFIX.sub("", text)
    text = _TITLE_SENTENCE_PUNCT.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return "New Chat"

    text = _truncate_title(text)
    # Unlike a model response, a single meaningful word ("Photosynthesis") is a
    # perfectly good title, so only require a minimum length here.
    return text if len(text) >= 4 else "New Chat"


def _model_for(provider, plan_tier, free_model):
    if not billing_enabled() or str(plan_tier or "free").lower() != "paid":
        return free_model
    try:
        from .pro_ai import model_for
        return model_for(provider, plan_tier, free_model)
    except ImportError:
        return free_model


def _retry_plan_tier(plan_tier):
    if not billing_enabled():
        return "free"
    try:
        from .pro_ai import retry_plan
        return retry_plan(plan_tier)
    except ImportError:
        return "free"

logger = logging.getLogger(__name__)


class AIProviderFailure(Exception):
    """Provider fallback ended without an answer; contains only a safe code."""

    def __init__(self, code=SERVER_FAILURE):
        self.code = code
        super().__init__(code)


class AIService:
    def __init__(self):
        self.gemini_clients = []
        self.gemini_model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self.deepseek_keys = []
        self.deepseek_endpoint = os.environ.get("DEEPSEEK_ENDPOINT", _DEEPSEEK_ENDPOINT)

        # Setup Gemini clients (one per key)
        if GEMINI_AVAILABLE:
            for key in self._get_api_keys("GEMINI"):
                self.gemini_clients.append(genai.Client(api_key=key))

        # Setup DeepSeek keys (used via httpx — no openai dependency needed)
        self.deepseek_keys = self._get_api_keys("DEEPSEEK")

        # Setup Groq keys (used for title generation + question classification)
        self.groq_keys = self._get_api_keys("GROQ")

        # Setup Kira AI keys (primary provider — OpenAI-compatible)
        self.kira_keys = self._get_api_keys("KIRA")

        # RAG is initialized eagerly in apps.py ready() via get_rag_service().
        if RAG_AVAILABLE:
            try:
                self.rag_service = get_rag_service()
            except Exception as e:
                print(f"[AI] RAG singleton error (non-blocking): {e}")

    def _get_api_keys(self, prefix: str) -> list[str]:
        keys = []
        def add(value):
            value = (value or "").strip()
            if value and value not in keys:
                keys.append(value)
        for value in os.environ.get(f"{prefix}_API_KEYS", "").split(","):
            add(value)
        add(os.environ.get(f"{prefix}_API_KEY"))
        for index in range(1, 6):
            add(os.environ.get(f"{prefix}_API_KEY_{index}"))
        return keys

    def _get_rag_context_with_source(self, query: str, grade: str = None, subject: str = None) -> tuple:
        rag_service = getattr(self, "rag_service", None)
        if not rag_service or not rag_service.initialized:
            return ("", "")
        try:
            return rag_service.get_context_for_query_with_source(query, grade, subject)
        except Exception as e:
            print(f"[AI] RAG context error: {e}")
            return ("", "")

    def _content_tokens(self, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(token) > 1 and token not in _STOPWORDS
        }

    def _looks_like_exercise_request(self, message: str) -> bool:
        text = (message or "").lower()
        return bool(
            re.search(r"\b(exercise|ex\.?|question|q\.?|number|no\.?)\s*[0-9]", text)
            or re.search(r"\b[0-9]+(?:\.[0-9]+)?\s*(?:number|no\.?|question|q\.?)\s*[0-9]", text)
        )

    def _is_generative_request(self, message: str) -> bool:
        """Detect requests asking for sample/creative content generation (brochure, example, meaning, etc.)."""
        text = (message or "").lower()
        return bool(
            re.search(r"\b(sample|example|brochure|prepare|create|write|draft|compose|meaning|define|definition|word\s*meaning|meanings?|list\s+the|what\s+are\s+the)\b", text)
            and re.search(r"\b(sample|example|brochure|prepare|create|write|draft|compose|meaning|define|definition|meanings?)\b", text)
        )

    def _grounding_verification(self, message: str, source_text: str, chapter_title: str = "") -> Dict[str, Any]:
        """Deterministic, no-AI check that the request is grounded in retrieved text."""
        # Allow generative/creative requests (samples, examples, word meanings, etc.)
        # These are based on textbook guidelines but require the AI to create content
        if self._is_generative_request(message):
            has_source = bool((source_text or "").strip())
            return {
                "verified": has_source or bool(chapter_title),
                "matched_terms": [],
                "page_refs": sorted(set(re.findall(r"\[Page\s+(\d+)\]", source_text or "")), key=lambda p: int(p))[:5],
                "generative": True,
            }

        message_tokens = self._content_tokens(message) - _STUDY_TERMS
        source_tokens = self._content_tokens(source_text)
        title_tokens = self._content_tokens(chapter_title)
        matched = sorted((message_tokens & source_tokens) | (message_tokens & title_tokens))
        page_refs = sorted(set(re.findall(r"\[Page\s+(\d+)\]", source_text or "")), key=lambda p: int(p))[:5]
        has_source = bool((source_text or "").strip())
        is_exercise = self._looks_like_exercise_request(message)
        has_chapter_match = bool(title_tokens and (title_tokens <= source_tokens or title_tokens & message_tokens))

        # Check if the specific exercise number exists in the source text
        exercise_match = re.search(r"exercise\s+([\d.]+)", message, re.IGNORECASE)
        exercise_number = exercise_match.group(1) if exercise_match else None
        if exercise_number and source_text:
            exercise_in_source = bool(re.search(r"exercise\s+" + re.escape(exercise_number), source_text, re.IGNORECASE))
            if not exercise_in_source:
                return {
                    "verified": False,
                    "matched_terms": matched[:8],
                    "page_refs": page_refs,
                    "reason": f"Exercise {exercise_number} not found in loaded textbook content",
                }

        return {
            "verified": has_source and (bool(matched) or (is_exercise and bool(chapter_title)) or has_chapter_match),
            "matched_terms": matched[:8],
            "page_refs": page_refs,
        }



    def _get_chapter_context(self, subject: str, chapter_title: str, message: str) -> str:
        """Get chapter-scoped textbook context."""
        if not subject or not chapter_title:
            return ""
        text = get_chapter_text_for_selection(subject, chapter_title)
        if text:
            return text
        return get_chapter_pdf_context(subject, message)

    def _is_context_followup(self, message: str) -> bool:
        text = (message or "").strip().lower()
        if not text:
            return False
        followup_phrases = {
            "it", "this", "that", "these", "those", "same", "above", "previous",
            "again", "more", "shorter", "longer", "simpler", "detail", "detailed",
            "explain", "summarize", "summary", "notes", "questions", "answers", "examples",
            "important questions", "exam notes", "make it", "explain it",
            "explain more", "point", "number",
            "continue", "next", "revise", "quiz me", "mcq",
        }
        if any(phrase in text for phrase in followup_phrases):
            return True
        return bool(re.search(r"\b(point|no\.?|number|q\.?)\s*[0-9]+\b", text))

    def _exercise_anchor_note(self, message: str, personal_context: str) -> str:
        """Deterministic anchor note when the student names a specific exercise/question.

        Prevents the LLM from carrying over the previous exercise's context when
        the student switches from e.g. 7.3 to 7.1 mid-session.
        """
        ref = extract_exercise_ref(message)
        if not ref:
            return ""
        exercise_part, _, question_part = ref.partition("#")
        prior_exercises = sorted({
            prior.split("#")[0]
            for prior in extract_exercise_refs(personal_context or "")
            if prior and prior.split("#")[0] != exercise_part
        })
        note = (
            f"EXERCISE ANCHOR: The student is asking about Exercise {exercise_part}"
            + (f", question number {question_part}" if question_part else "")
            + ". Solve ONLY this exercise/question, taken from the textbook content provided.\n"
        )
        if prior_exercises:
            note += (
                f"IMPORTANT: The conversation history mentions other exercises "
                f"({', '.join(prior_exercises)}). The student has SWITCHED exercises — "
                "ignore all previous exercise questions and answers completely.\n"
            )
        return note

    def _call_gemini(
        self, client, model: str, prompt: str, system_prompt: str,
        max_output_tokens: int, timeout: int
    ) -> str:
        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt or None,
            temperature=0.3,
            max_output_tokens=max_output_tokens,
        )
        try:
            response = client.models.generate_content(
                model=model, contents=prompt, config=config, timeout=timeout,
            )
        except TypeError:
            response = client.models.generate_content(
                model=model, contents=prompt, config=config,
            )
        if response and hasattr(response, "text") and response.text:
            return response.text
        raise Exception("Empty response")

    def _call_deepseek(
        self, api_key: str, model: str, prompt: str, system_prompt: str,
        max_output_tokens: int, timeout: int
    ) -> str:
        url = self.deepseek_endpoint.rstrip("/") + "/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": max_output_tokens,
        }
        with httpx.Client(timeout=timeout) as http:
            resp = http.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                content=json.dumps(payload),
            )
            resp.raise_for_status()
            data = resp.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if text:
                return text
        raise Exception("Empty DeepSeek response")

    def _call_cerebras(
        self, api_key: str, prompt: str, system_prompt: str,
        max_tokens: int, timeout: int
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": "llama3.1-8b",
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": max_tokens,
        }
        with httpx.Client(timeout=timeout) as http:
            resp = http.post(
                _CEREBRAS_ENDPOINT + "/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                content=json.dumps(payload),
            )
            resp.raise_for_status()
            data = resp.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if text:
                return text.strip()
        raise Exception("Empty Cerebras response")

    def _try_cerebras(self, prompt: str, system_prompt: str, max_tokens: int, timeout: int) -> str:
        key = os.environ.get("CEREBRAS_API_KEY", "").strip()
        if not key:
            return ""
        try:
            return self._call_cerebras(key, prompt, system_prompt, max_tokens, timeout)
        except Exception as e:
            print(f"[AI] Cerebras error (falling back to heuristic): {e}")
            return ""

    def _call_groq(
        self, api_key: str, prompt: str, system_prompt: str,
        max_tokens: int, timeout: int
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        for model in _model_chain(_GROQ_TITLE_MODEL, _GROQ_TITLE_FALLBACKS):
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": max_tokens,
            }
            try:
                with httpx.Client(timeout=timeout) as http:
                    resp = http.post(
                        _GROQ_ENDPOINT + "/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        content=json.dumps(payload),
                    )
                # Groq reports a bad model name as a 400 with the reason in the
                # body, so raise_for_status() alone is not enough to tell a
                # retired model apart from a bad key.
                if resp.status_code >= 400:
                    raise Exception(
                        f"Groq HTTP {resp.status_code} for model {model}: {resp.text[:200]}"
                    )
                data = resp.json()
                text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
                if text and text.strip():
                    return text.strip()
                last_error = Exception(f"Empty Groq response for model {model}")
            except Exception as e:
                last_error = e
                if not _is_model_unavailable_error(e):
                    raise
                logger.info("Groq model %s unavailable, trying next: %s", model, e)
        raise last_error or Exception("Empty Groq response")

    def _call_kira(
        self, api_key: str, model: str, prompt: str, system_prompt: str,
        max_output_tokens: int, timeout: int
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": max_output_tokens,
        }
        with httpx.Client(timeout=timeout) as http:
            resp = http.post(
                _KIRA_ENDPOINT + "/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                content=json.dumps(payload),
            )
            # Same as Groq: an unsupported model name comes back as a 4xx whose
            # reason is only in the body, so surface it for the fallback chain.
            if resp.status_code >= 400:
                raise Exception(
                    f"Kira HTTP {resp.status_code} for model {model}: {resp.text[:200]}"
                )
            data = resp.json()
            text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            if text and text.strip():
                return text.strip()
        raise Exception("Empty Kira response")

    def _classify_with_groq(self, api_key: str, message: str) -> str:
        system_prompt = """Classify the following student question into exactly one category.
Respond with ONLY one word: "simple", "complex", or "diagram".

Rules:
- "simple": Short factual questions asking for definitions, formulas, values, lists, or straightforward calculations. Usually under 20 words. Starts with what, who, when, where, which, how many, define, list, name, state, write, find, calculate, simplify, solve.
- "complex": Questions that require explanations, derivations, proofs, comparisons, step-by-step solutions, or exercise problems. Includes why, how does, explain, describe, derive, prove, compare, contrast, elaborate, discuss, justify, relationship. Also exercise/ question numbers.
- "diagram": Questions asking to draw, sketch, illustrate, show in, represent in, or about venn diagrams, graphs, charts, figures."""
        prompt = f"Student question: {message}\n\nCategory:"
        return self._call_groq(api_key, prompt, system_prompt, max_tokens=10, timeout=15)

    def _classify_question(self, message: str) -> str:
        """Groq-based classifier with rule-based fallback.

        Returns "simple", "complex", or "diagram".
        """
        for key in self.groq_keys:
            try:
                result = self._classify_with_groq(key, message)
                if result in ("simple", "complex", "diagram"):
                    return result
            except Exception as e:
                print(f"[AI] Groq classifier key failed (trying next): {e}")

        # Rule-based fallback
        text = (message or "").strip().lower()

        # Diagram / image questions → Gemini
        if re.search(
            r"\b(venn|diagram|graph|chart|figure|sketch|illustrat|"
            r"show\s+in|represent\s+in|draw\s+the)\b", text
        ):
            return "diagram"

        wc = len(text.split())

        # Exercise questions need step-by-step solving → Gemini
        # Check FIRST so "solve exercise 1.1 11" doesn't get misclassified as simple
        if re.search(r"\b(exercise|ex\.|question|q\.)\s*\d", text):
            return "complex"

        # Simple factual questions → DeepSeek
        if re.search(
            r"^(what|who|when|where|which|how\s+many|how\s+much|define|"
            r"list|name|state|write|find|calculate|simplify|solve)\b", text
        ) and wc < 20:
            return "simple"
        if re.search(r"\b(formula|definition|meaning|value\s+of)\b", text) and wc < 25:
            return "simple"

        # Long or explanation-type questions → Gemini
        if wc > 30 or re.search(
            r"\b(explain|describe|derive|prove|why|how\s+does|"
            r"compare|contrast|difference|elaborate|discuss|justify|relationship)\b", text
        ):
            return "complex"

        # Default: simple
        return "simple"

    def _try_gemini(
        self, prompt: str, system_prompt: str, max_output_tokens: int,
        timeout: int, plan_tier: str, errors: list
    ) -> str:
        primary = _model_for("gemini", plan_tier, _GEMINI_FREE_MODEL)
        models_to_try = [primary] + [m for m in _GEMINI_FALLBACK_MODELS if m != primary]
        for model in models_to_try:
            for idx, client in enumerate(self.gemini_clients, start=1):
                try:
                    return self._call_gemini(client, model, prompt, system_prompt, max_output_tokens, timeout)
                except Exception as e:
                    err_msg = str(e).lower()
                    if "404" in err_msg or "not found" in err_msg:
                        # Model deprecated, try next model
                        break
                    category = classify_provider_error(e)
                    errors.append({"category": category})
                    logger.warning("Gemini generation failed for %s key slot %s (category=%s)", model, idx, category)
        return ""

    def _try_deepseek(
        self, prompt: str, system_prompt: str, max_output_tokens: int,
        timeout: int, plan_tier: str, errors: list
    ) -> str:
        if not self.deepseek_keys:
            return ""
        model = _model_for("deepseek", plan_tier, _DEEPSEEK_MODEL)
        for idx, key in enumerate(self.deepseek_keys, start=1):
            try:
                return self._call_deepseek(key, model, prompt, system_prompt, max_output_tokens, timeout)
            except Exception as e:
                category = classify_provider_error(e)
                errors.append({"category": category})
                logger.warning("DeepSeek generation failed for %s key slot %s (category=%s)", model, idx, category)
        return ""

    def _try_kira(
        self, prompt: str, system_prompt: str, max_output_tokens: int,
        timeout: int, plan_tier: str, errors: list
    ) -> str:
        if not self.kira_keys:
            return ""
        model = _model_for("kira", plan_tier, _KIRA_MODEL_FREE)
        for idx, key in enumerate(self.kira_keys, start=1):
            try:
                return self._call_kira(key, model, prompt, system_prompt, max_output_tokens, timeout)
            except Exception as e:
                category = classify_provider_error(e)
                errors.append({"category": category})
                logger.warning("Kira generation failed for %s key slot %s (category=%s)", model, idx, category)
        return ""

    def _generate(
        self,
        prompt: str,
        system_prompt: str = None,
        max_output_tokens: int = 2048,
        timeout: int = 30,
        plan_tier: str = "free",
    ) -> str:
        errors = []
        category = self._classify_question(prompt)

        # ── Routing logic ──────────────────────────────────────
        #   DeepSeek (primary) → Kira (backup) → Gemini (final fallback)
        #   simple     → DeepSeek first, then Kira, then Gemini
        #   complex    → DeepSeek first, then Gemini, then Kira
        #   diagram    → DeepSeek first, then Gemini, then Kira
        #   quota hit  → cross-over to other provider

        if category == "simple":
            result = self._try_deepseek(prompt, system_prompt, max_output_tokens, timeout, plan_tier, errors)
            if result:
                return result
            result = self._try_kira(prompt, system_prompt, max_output_tokens, timeout, plan_tier, errors)
            if result:
                return result
            result = self._try_gemini(prompt, system_prompt, max_output_tokens, timeout, plan_tier, errors)
            if result:
                return result
        else:
            result = self._try_deepseek(prompt, system_prompt, max_output_tokens, timeout, plan_tier, errors)
            if result:
                return result
            result = self._try_gemini(prompt, system_prompt, max_output_tokens, timeout, plan_tier, errors)
            if result:
                return result
            result = self._try_kira(prompt, system_prompt, max_output_tokens, timeout, plan_tier, errors)
            if result:
                return result

        raise AIProviderFailure(classify_provider_failures(errors))

    def generate_title(self, user_message: str) -> str:
        """Generate a short, specific title, falling back to a local heuristic.

        Uses Groq only, skipping unavailable Groq models and keys. Never raises:
        a title is cosmetic, so a failure here must not affect the answer the
        student is waiting for.
        """
        message = (user_message or "").strip()
        if not message:
            return "New Chat"

        prompt = f"Student's first message: {message[:200]}"

        def attempt(provider, call):
            try:
                title = _clean_title(call())
            except Exception as e:
                logger.info("Title generation via %s failed: %s", provider, e)
                return ""
            if title:
                logger.info("Title generated via %s: %r", provider, title)
            return title

        # Groq is the only remote provider used for title generation.
        for key in self.groq_keys:
            title = attempt(
                "groq",
                lambda k=key: self._call_groq(k, prompt, _TITLE_SYSTEM_PROMPT, 20, 8),
            )
            if title:
                return title

        fallback = _heuristic_title(message)
        logger.info("Title generated via heuristic: %r", fallback)
        return fallback

    def chat(
        self, message: str, user=None, personal_context: str = "", context: Dict = None
    ) -> Generator[Dict[str, Any], None, None]:
        """Generator that yields real status events, then a complete event.

        Yields:
            {"type": "status", "stage": str, "message": str}
            {"type": "complete", "response": str, "source": str}

        Complete events also flag quota-relevant outcomes:
            "cached": True     — served from cache/KB (does not count against usage)
            "ai_failed": True  — the provider failed (does not count against usage)
        """
        context = context or {}
        subject = normalize_subject(context.get("subject", ""))
        grade = str(context.get("grade", "10"))
        chapter_title = context.get("chapter", "")
        plan_tier = str(getattr(user, "plan_tier", "free") or "free").lower()
        if not billing_enabled():
            plan_tier = "free"
        cache_service = get_semantic_cache_service()

        out_of_scope_response = out_of_scope_response_for_subject(subject)

        yield {"type": "status", "stage": "scope", "message": "Preparing textbook grounding..."}

        # ─── CHAPTER-SCOPED PATH (primary, zero-hallucination) ───
        chapter_context = ""
        if chapter_title:
            yield {"type": "status", "stage": "context", "message": f"Studying..."}
            chapter_context = self._get_chapter_context(subject, chapter_title, message)

            if chapter_context:
                # Extract page info for the status message
                page_info = ""
                if "pages " in chapter_context:
                    try:
                        page_part = chapter_context.split("pages ")[1].split(")")[0]
                        page_info = f" (pages {page_part})"
                    except Exception:
                        pass

                yield {"type": "status", "stage": "context_loaded", "message": f"Textbook content loaded{page_info}."}
                verification = self._grounding_verification(message, chapter_context, chapter_title)
                if not verification["verified"]:
                    reason = verification.get("reason", "")
                    response_msg = (
                        "I found the selected chapter, but I could not verify this question "
                        "against its textbook text. Please include the exact exercise/question "
                        "text or check that the selected chapter is correct."
                    )
                    if reason:
                        response_msg = f"I found the selected chapter, but {reason}. Please select the correct chapter or provide the exact question text."
                    yield {
                        "type": "complete",
                        "response": response_msg,
                        "source": f"CDC Textbook - {subject.title()} - {chapter_title}",
                    }
                    return

                yield {"type": "status", "stage": "cache", "message": "Remembering..."}
                cache_decision = cache_service.inspect(message, context, user=user, plan_tier=plan_tier)

                if cache_decision.decision in {DECISION_CACHE_HIT, DECISION_KB_HIT}:
                    yield {"type": "status", "stage": "cache_hit", "message": ""}
                    yield {"type": "complete", "response": cache_decision.answer, "source": cache_decision.source, "cached": True}
                    return

                yield {"type": "status", "stage": "generating", "message": "Almost there..."}
                system_prompt = f"""You are a Grade 10 CDC study assistant. Answer strictly in English.
You have been provided with retrieved CDC textbook content for the selected chapter.

CRITICAL RULES:
1. Answer the question using the provided textbook content as the primary source.
2. For exercise-style requests, solve the requested item using the definitions, examples, formulas, and exercise text in the selected chapter. If the exact item text is missing, state the assumption you are using and ask for the exact question only when a numeric/symbolic answer cannot be determined.
3. Do NOT use any outside knowledge, internet sources, or your training data for factual questions.
4. Do NOT generate Python code, programming snippets, or any executable code. Use plain text explanations with LaTeX math only.
5. ANTI-HALLUCINATION: Do NOT invent or guess which exercise number or question the student is asking about. If the student says "solve exercise 7.3 question 9", look for that exact question in the provided textbook content. If the exact question text is not found in the content, say "I could not find this specific question in the provided textbook content" and ask the student to provide the exact question text. NEVER make up a question that was not provided by the student.
6. NEVER modify, reinterpret, or "improve" the student's question. Answer exactly what they asked, not what you think they meant.
7. SAMPLE/EXAMPLE GENERATION: When the student explicitly asks you to prepare, create, write, or generate a sample (e.g., "prepare a sample brochure", "give an example of", "write a sample"), you SHOULD create a well-structured example based on the guidelines, structure, or format described in the textbook content. Use the textbook's instructions as a template and fill it with realistic, appropriate content. This is NOT hallucination — it is applying what the textbook teaches. Always note that the sample is an illustrative example based on the chapter's guidelines.
8. SOLVING A QUESTION OF YOUR CHOICE: When the student asks you to solve any question of your choice from the exercise, Please Specify the Exercise/ Chapter and Question.
9. DIAGRAMS: When asked to draw, sketch, or illustrate a diagram, use the appropriate format:
   - Venn diagrams: Use ```venn code block with this format:
     ```
     venn
     sets: S, M, N
     S_only: 20%
     M_only: 20%
     N_only: 20%
     S_M: 5%
     M_N: 15%
     S_N: 10%
     S_M_N: 5%
     ```
   - Flowcharts, cycles, processes, hierarchies: Use ```mermaid code block.
   - Do NOT use TikZ or LaTeX for diagrams.

FORMATTING RULES:
- Use ## for main section headings (## Given, ## To Prove, ## Proof, ## Solution)
- **CRITICAL: Put a BLANK LINE (empty line) between EVERY step, equation, and text block.** Without blank lines, markdown renders everything as one congested block.
- Keep paragraphs SHORT — 1-2 sentences max
- Use **bold** for key terms, formulas, and important results
- For math solutions, write like a student writes in their notebook: clean, short steps with minimal words

{_LATEX_MATH_INSTRUCTIONS}"""
                user_prompt = f"""Student Question: {message}

{self._exercise_anchor_note(message, personal_context)}SELECTED CHAPTER TEXTBOOK CONTENT:
{chapter_context}

CONVERSATION MEMORY:
{personal_context[-1500:] if personal_context else "None"}

INSTRUCTIONS:
1. Provide a direct, concise answer first.
2. For math solutions: write like a student's notebook — short steps, minimal narration, let the math speak.
3. Use ## headings, **bold** key terms, short paragraphs.
4. Do not add information not present in the textbook content for factual questions.
5. Stay grounded in the selected chapter. Do not refuse merely because the student used an exercise number.
6. If the student asks for a sample, example, or creative output (brochure, letter, speech, word meanings, etc.), generate a well-structured example based on the textbook's guidelines. This is an application of the textbook's teaching, not hallucination.
"""
                try:
                    response = self._generate(
                        user_prompt,
                        system_prompt,
                        max_output_tokens=8192,
                        timeout=60,
                        plan_tier=plan_tier,
                    )
                    if not _is_valid_response(response):
                        print(f"[AI] Invalid response detected, retrying with different model...")
                        response = self._generate(
                            user_prompt,
                            system_prompt,
                            max_output_tokens=8192,
                            timeout=60,
                            plan_tier=_retry_plan_tier(plan_tier),
                        )
                    yield {"type": "status", "stage": "caching", "message": "Memorizing..."}
                    cache_service.learn_from_ai(
                        message=message,
                        answer=response.rstrip(),
                        context=context,
                        source=f"CDC Textbook — {subject.title()} — {chapter_title}",
                        model=_model_for("gemini", plan_tier, _GEMINI_FREE_MODEL),
                    )
                    yield {"type": "complete", "response": response, "source": f"CDC Textbook — {subject.title()} — {chapter_title}"}
                    return
                except Exception as e:
                    error_code = getattr(e, "code", classify_provider_error(e))
                    logger.error("AI generation failed on the chapter path (category=%s, error=%s)", error_code, type(e).__name__)
                    yield {
                        "type": "complete",
                        "response": user_error_message(error_code),
                        "source": "Error",
                        "ai_failed": True,
                        "error_code": error_code,
                    }
                    return

        # ─── FALLBACK PATH: Cache → RAG → AI ───
        yield {"type": "status", "stage": "cache", "message": "Remembering..."}
        cache_decision = cache_service.inspect(message, context, user=user, plan_tier=plan_tier)
        if cache_decision.decision in {DECISION_CACHE_HIT, DECISION_KB_HIT}:
            yield {"type": "complete", "response": cache_decision.answer, "source": cache_decision.source, "cached": True}
            return

        yield {"type": "status", "stage": "rag", "message": "Searching curriculum database..."}
        grade_key = f"class_{grade}" if not grade.startswith("class_") else grade
        rag_context, source_info = self._get_rag_context_with_source(message, grade_key, subject)
        verification = self._grounding_verification(message, rag_context, context.get("chapter", ""))
        if not verification["verified"]:
            yield {
                "type": "complete",
                "response": (
                    "I could not verify this against the available CDC textbook context. "
                    "Please select the relevant chapter or include the exact exercise/question text."
                ),
                "source": "Deterministic Grounding Check",
            }
            return

        yield {"type": "status", "stage": "generating", "message": "Generating answer..."}
        is_generative = verification.get("generative", False)
        system_prompt = f"""You are a Grade 10 CDC study assistant. Answer strictly in English.
Use the provided TEXTBOOK CONTEXT to answer the student's question accurately.
Do NOT invent facts outside the provided textbook context for factual questions.
Do NOT invent or guess which question the student is asking about. If the exact question is not in the context, say so and ask for clarification.
If the question is completely outside the CDC syllabus, reply exactly: {out_of_scope_response}
{"SAMPLE/EXAMPLE GENERATION: The student is asking for a sample or creative output. Use the textbook's guidelines, structure, or format as a template and create a well-structured example with realistic content. Always note that the sample is illustrative and based on the chapter's guidelines." if is_generative else ""}
DIAGRAMS: When asked to draw a Venn diagram, use ```venn code block with format: sets: A, B, C / A_only: X% / B_only: Y% / etc. For flowcharts/cycles, use ```mermaid. Do NOT use TikZ.

FORMATTING RULES:
- Use ## for main section headings (## Given, ## To Prove, ## Proof, ## Solution)
- **CRITICAL: Put a BLANK LINE (empty line) between EVERY step, equation, and text block.** Without blank lines, markdown renders everything as one congested block.
- Keep paragraphs SHORT — 1-2 sentences max
- Use **bold** for key terms, formulas, and important results
- For math solutions, write like a student writes in their notebook: clean, short steps with minimal words

SOLUTION STYLE RULES:
- Write at Grade 10 level. Use simple, everyday English. No fancy vocabulary.
- Do NOT separate numerator and denominator into different sections. Keep the fraction as one expression and simplify it directly in place.
- Do NOT explain what a fraction or identity "means". Just apply it and move on.
- Each step: state the identity, substitute, simplify. That's it.
- Maximum 1-2 lines per step. If a step needs more than 2 lines, split it into two steps.
- Use "L.H.S. = ..." format consistently. Don't write long paragraphs describing what you're doing.
- Never say "Assuming ... ≠ 0" or "This expression is not generally equal to". Just solve it.
- If the identity is provable from the textbook, it IS correct. Prove it directly.

{_LATEX_MATH_INSTRUCTIONS}"""
        user_prompt = f"""Student Question: {message}

{self._exercise_anchor_note(message, personal_context)}TEXTBOOK CONTEXT:
{rag_context}

CONVERSATION MEMORY:
{personal_context[-1500:] if personal_context else "None"}

INSTRUCTIONS:
1. Provide a direct, concise answer first.
2. Follow with clear, step-by-step explanations or bullet points.
3. Keep it within 500 words and highly token-efficient.
4. Do not use filler words. Be precise and exam-focused.
5. If the student asks for a sample, example, or creative output (brochure, letter, speech, word meanings, etc.), generate a well-structured example based on the textbook's guidelines. This is an application of the textbook's teaching, not hallucination.
"""
        try:
            response = self._generate(
                user_prompt,
                system_prompt,
                max_output_tokens=2048,
                timeout=30,
                plan_tier=plan_tier,
            )
            if not _is_valid_response(response):
                print(f"[AI] Invalid response detected in fallback, retrying...")
                response = self._generate(
                    user_prompt,
                    system_prompt,
                    max_output_tokens=2048,
                    timeout=30,
                    plan_tier=_retry_plan_tier(plan_tier),
                )
            yield {"type": "status", "stage": "caching", "message": "Almost There..."}
            cache_service.learn_from_ai(
                message=message,
                answer=response,
                context=context,
                source=source_info or "AI Generated",
                model=_model_for("gemini", plan_tier, _GEMINI_FREE_MODEL),
            )
            yield {"type": "complete", "response": response, "source": source_info if source_info else "General Knowledge"}
        except Exception as e:
            error_code = getattr(e, "code", classify_provider_error(e))
            logger.error("AI generation failed on the retrieval path (category=%s, error=%s)", error_code, type(e).__name__)
            yield {
                "type": "complete",
                "response": user_error_message(error_code),
                "source": "Error",
                "ai_failed": True,
                "error_code": error_code,
            }

    def get_rag_status(self) -> Dict:
        if not getattr(self, 'rag_service', None):
            return {"available": False, "message": "RAG not initialized"}
        return self.rag_service.get_status()

    def system_check(self) -> Dict:
        issues = []
        if not getattr(self, 'rag_service', None):
            issues.append("RAG service not initialized")
        if not self.gemini_clients:
            issues.append("Gemini clients not initialized — no primary provider")
        if not self.deepseek_keys:
            issues.append("DeepSeek keys not configured — no fallback provider")
        return {"status": "error" if issues else "ok", "issues": issues}

    def initialize_rag(self, force_rebuild: bool = False) -> Dict:
        if not getattr(self, 'rag_service', None):
            return {"status": "error", "message": "RAG not available"}
        try:
            from .rag_service import initialize_rag as init_rag
            return init_rag(force_rebuild=force_rebuild)
        except Exception as e:
            return {"status": "error", "message": str(e)}
