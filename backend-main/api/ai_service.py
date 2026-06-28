"""
AI Service for Noya AI with RAG Integration + Real Streaming
"""

import json
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
    get_semantic_cache_service,
)
from .models import ChatMessage, KnowledgeBaseEntry


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
_GEMINI_PAID_MODEL = "gemini-2.5-pro"
_DEEPSEEK_MODEL = "deepseek-v4-flash-free"
_DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1"


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

    def _grounding_verification(self, message: str, source_text: str, chapter_title: str = "") -> Dict[str, Any]:
        """Deterministic, no-AI check that the request is grounded in retrieved text."""
        message_tokens = self._content_tokens(message) - _STUDY_TERMS
        source_tokens = self._content_tokens(source_text)
        title_tokens = self._content_tokens(chapter_title)
        matched = sorted((message_tokens & source_tokens) | (message_tokens & title_tokens))
        page_refs = sorted(set(re.findall(r"\[Page\s+(\d+)\]", source_text or "")), key=lambda p: int(p))[:5]
        has_source = bool((source_text or "").strip())
        is_exercise = self._looks_like_exercise_request(message)
        has_chapter_match = bool(title_tokens and (title_tokens <= source_tokens or title_tokens & message_tokens))

        return {
            "verified": has_source and (bool(matched) or (is_exercise and bool(chapter_title)) or has_chapter_match),
            "matched_terms": matched[:8],
            "page_refs": page_refs,
        }



    def _get_chapter_context(self, subject: str, chapter_title: str, message: str) -> str:
        """Get chapter-scoped textbook context."""
        if not subject or not chapter_title:
            return ""
        max_chars = 20000 if self._looks_like_exercise_request(message) else 7000
        text = get_chapter_text_for_selection(subject, chapter_title, max_chars=max_chars)
        if text:
            return text
        return get_chapter_pdf_context(subject, message, max_chars=max_chars)

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
            if resp.status_code == 429:
                raise Exception("Rate limited")
            resp.raise_for_status()
            data = resp.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if text:
                return text
        raise Exception("Empty DeepSeek response")

    def _classify_question(self, message: str) -> str:
        """Rule-based question classifier — no AI calls.

        Returns "simple", "complex", or "diagram".
        """
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
        model = _GEMINI_FREE_MODEL if plan_tier == "free" else _GEMINI_PAID_MODEL
        for idx, client in enumerate(self.gemini_clients, start=1):
            try:
                return self._call_gemini(client, model, prompt, system_prompt, max_output_tokens, timeout)
            except Exception as e:
                err_msg = str(e).lower()
                if any(w in err_msg for w in ("quota", "429", "rate", "limit", "resource exhausted")):
                    errors.append(f"Gemini key {idx} exhausted: {e}")
                else:
                    errors.append(f"Gemini key {idx} error: {e}")
        return ""

    def _try_deepseek(
        self, prompt: str, system_prompt: str, max_output_tokens: int,
        timeout: int, errors: list
    ) -> str:
        if not self.deepseek_keys:
            return ""
        model = _DEEPSEEK_MODEL
        for idx, key in enumerate(self.deepseek_keys, start=1):
            try:
                return self._call_deepseek(key, model, prompt, system_prompt, max_output_tokens, timeout)
            except Exception as e:
                err_msg = str(e).lower()
                if "429" in err_msg or "rate" in err_msg:
                    errors.append(f"DeepSeek key {idx} exhausted: {e}")
                else:
                    errors.append(f"DeepSeek key {idx} error: {e}")
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
        #   simple     → DeepSeek first, Gemini fallback
        #   complex    → Gemini first, DeepSeek fallback
        #   diagram    → Gemini first, DeepSeek fallback
        #   quota hit  → cross-over to other provider

        if category == "simple":
            result = self._try_deepseek(prompt, system_prompt, max_output_tokens, timeout, errors)
            if result:
                return result
            result = self._try_gemini(prompt, system_prompt, max_output_tokens, timeout, plan_tier, errors)
            if result:
                return result
        else:
            result = self._try_gemini(prompt, system_prompt, max_output_tokens, timeout, plan_tier, errors)
            if result:
                return result
            result = self._try_deepseek(prompt, system_prompt, max_output_tokens, timeout, errors)
            if result:
                return result

        raise Exception("All providers exhausted: " + " | ".join(errors))

    def generate_title(self, user_message: str) -> str:
        """Fast heuristic title — zero Gemini API calls."""
        title = (user_message or "").strip()
        title = re.sub(r"^(what is|explain|describe|define|how|why|when|where|who)\s+", "", title, flags=re.IGNORECASE)
        title = title.replace("?", "").replace("!", "")
        words = title.split()
        if len(words) > 8:
            title = " ".join(words[:8]) + "..."
        if len(title) > 50:
            title = title[:50].rsplit(" ", 1)[0] + "..."
        return title or "New Chat"

    def chat(
        self, message: str, user=None, personal_context: str = "", context: Dict = None
    ) -> Generator[Dict[str, Any], None, None]:
        """Generator that yields real status events, then a complete event.

        Yields:
            {"type": "status", "stage": str, "message": str}
            {"type": "complete", "response": str, "source": str}
        """
        context = context or {}
        subject = normalize_subject(context.get("subject", ""))
        grade = str(context.get("grade", "10"))
        chapter_title = context.get("chapter", "")
        plan_tier = str(getattr(user, "plan_tier", "free") or "free").lower()
        cache_service = get_semantic_cache_service()

        out_of_scope_response = out_of_scope_response_for_subject(subject)

        yield {"type": "status", "stage": "scope", "message": "Preparing textbook grounding..."}

        # ─── CHAPTER-SCOPED PATH (primary, zero-hallucination) ───
        chapter_context = ""
        if chapter_title:
            yield {"type": "status", "stage": "context", "message": f"Reading {subject.title()} textbook — {chapter_title}..."}
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
                    yield {
                        "type": "complete",
                        "response": (
                            "I found the selected chapter, but I could not verify this question "
                            "against its textbook text. Please include the exact exercise/question "
                            "text or check that the selected chapter is correct."
                        ),
                        "source": f"CDC Textbook - {subject.title()} - {chapter_title}",
                    }
                    return

                yield {"type": "status", "stage": "cache", "message": "Checking cache for similar questions..."}
                cache_decision = cache_service.inspect(message, context, user=user, plan_tier=plan_tier)

                if cache_decision.decision in {DECISION_CACHE_HIT, DECISION_KB_HIT}:
                    yield {"type": "status", "stage": "cache_hit", "message": "Found cached answer!"}
                    yield {"type": "complete", "response": cache_decision.answer, "source": cache_decision.source}
                    return

                yield {"type": "status", "stage": "generating", "message": "Generating detailed answer from textbook..."}
                system_prompt = f"""You are a Grade 10 CDC study assistant. Answer strictly in English.
You have been provided with retrieved CDC textbook content for the selected chapter.

CRITICAL RULES:
1. Answer the question using ONLY the provided textbook content.
2. For exercise-style requests, solve the requested item using the definitions, examples, formulas, and exercise text in the selected chapter. If the exact item text is missing, state the assumption you are using and ask for the exact question only when a numeric/symbolic answer cannot be determined.
3. Do NOT use any outside knowledge, internet sources, or your training data.
4. Provide a FULL, DETAILED explanation with definitions, examples, and step-by-step reasoning from the textbook.
5. Format with clear markdown headers, bullet points, and numbered steps.
6. Be thorough — aim for a complete explanation suitable for exam preparation, not a brief summary.
"""
                user_prompt = f"""Student Question: {message}

SELECTED CHAPTER TEXTBOOK CONTENT:
{chapter_context}

CONVERSATION MEMORY:
{personal_context[-1500:] if personal_context else "None"}

INSTRUCTIONS:
1. Provide a comprehensive, detailed answer based ONLY on the textbook content above.
2. Include definitions, examples, and explanations from the textbook.
3. Use bullet points and numbered lists for clarity.
4. If the question asks for notes, provide structured exam notes.
5. If the question asks for questions/answers, provide them with detailed answers.
6. Do not add information not present in the textbook content.
7. Stay grounded in the selected chapter. Do not refuse merely because the student used an exercise number.
"""
                try:
                    response = self._generate(
                        user_prompt,
                        system_prompt,
                        max_output_tokens=8192,
                        timeout=60,
                        plan_tier=plan_tier,
                    )
                    yield {"type": "status", "stage": "caching", "message": "Saving answer for next time..."}
                    cache_service.learn_from_ai(
                        message=message,
                        answer=response.rstrip(),
                        context=context,
                        source=f"CDC Textbook — {subject.title()} — {chapter_title}",
                        model=_GEMINI_PAID_MODEL if plan_tier == "paid" else _GEMINI_FREE_MODEL,
                    )
                    yield {"type": "complete", "response": response, "source": f"CDC Textbook — {subject.title()} — {chapter_title}"}
                    return
                except Exception as e:
                    print(f"[AI] Provider failed (chapter path): {e}")
                    yield {"type": "complete", "response": "The AI service is currently unavailable. Please try again in a few minutes.", "source": "Error"}
                    return

        # ─── FALLBACK PATH: Cache → RAG → AI ───
        yield {"type": "status", "stage": "cache", "message": "Checking cache for similar questions..."}
        cache_decision = cache_service.inspect(message, context, user=user, plan_tier=plan_tier)
        if cache_decision.decision in {DECISION_CACHE_HIT, DECISION_KB_HIT}:
            yield {"type": "status", "stage": "cache_hit", "message": "Found cached answer!"}
            yield {"type": "complete", "response": cache_decision.answer, "source": cache_decision.source}
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
        system_prompt = f"""You are a Grade 10 CDC study assistant. Answer strictly in English.
Use the provided TEXTBOOK CONTEXT to answer the student's question accurately.
Do NOT invent facts outside the provided textbook context.
Format your answer with clear markdown headers, short paragraphs, and bullet points.
If the question is completely outside the CDC syllabus, reply exactly: {out_of_scope_response}
"""
        user_prompt = f"""Student Question: {message}

TEXTBOOK CONTEXT:
{rag_context}

CONVERSATION MEMORY:
{personal_context[-1500:] if personal_context else "None"}

INSTRUCTIONS:
1. Provide a direct, concise answer first.
2. Follow with clear, step-by-step explanations or bullet points.
3. Keep it within 500 words and highly token-efficient.
4. Do not use filler words. Be precise and exam-focused.
"""
        try:
            response = self._generate(
                user_prompt,
                system_prompt,
                max_output_tokens=2048,
                timeout=30,
                plan_tier=plan_tier,
            )
            yield {"type": "status", "stage": "caching", "message": "Saving answer for next time..."}
            cache_service.learn_from_ai(
                message=message,
                answer=response,
                context=context,
                source=source_info or "AI Generated",
                model=_GEMINI_PAID_MODEL if plan_tier == "paid" else _GEMINI_FREE_MODEL,
            )
            yield {"type": "complete", "response": response, "source": source_info if source_info else "General Knowledge"}
        except Exception as e:
            print(f"[AI] Provider failed: {e}")
            yield {"type": "complete", "response": "The AI service is currently unavailable. Please try again in a few minutes.", "source": "Error"}

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
