from django.test import TestCase

from .models import ChatMessage, ChatSession, KnowledgeBaseEntry, User
from .views import _reconcile_session_context
from .semantic_cache import (
    DECISION_AI_REQUIRED,
    DECISION_CACHE_HIT,
    DECISION_KB_HIT,
    _LRUCache,
    educational_fingerprint,
    embed_text,
    extract_exercise_ref,
    extract_exercise_refs,
    get_semantic_cache_service,
    infer_intent,
    normalize_query,
    extract_topic,
    scope_filters,
)


def make_quality_answer(marker: str) -> str:
    """Answer long/structured enough to pass learn_from_ai's quality gate (>= 0.74)."""
    parts = []
    for step in range(1, 7):
        parts.append(
            f"## Step {step}\n\n**Key result {step}:** {marker} "
            "This is the detailed working for the step, written out fully so the "
            "solution is clear and complete for the student to revise from."
        )
    return "\n\n".join(parts)


class ExtractExerciseRefTests(TestCase):
    def test_exercise_with_question_number(self):
        self.assertEqual(extract_exercise_ref("solve exercise 7.3 question 2"), "7.3#2")

    def test_exercise_only(self):
        self.assertEqual(extract_exercise_ref("explain exercise 7.1"), "7.1")

    def test_ex_abbreviation(self):
        self.assertEqual(extract_exercise_ref("solve ex. 7.2 no. 4"), "7.2#4")

    def test_number_before_question_word(self):
        self.assertEqual(extract_exercise_ref("7.1 q2 please"), "7.1#2")

    def test_question_word_alone_is_not_a_ref(self):
        self.assertEqual(extract_exercise_ref("solve question 5"), "")

    def test_no_ref_for_plain_question(self):
        self.assertEqual(extract_exercise_ref("what is photosynthesis"), "")

    def test_devanagari_digits(self):
        self.assertEqual(extract_exercise_ref("अभ्यास ७.३ प्रश्न २ समाधान गर्नुहोस्"), "7.3#2")

    def test_no_false_positive_inside_words(self):
        # "complex" contains "ex" — must NOT be treated as an exercise reference
        self.assertEqual(extract_exercise_ref("explain complex numbers question 2"), "")

    def test_multiple_refs_collected(self):
        refs = extract_exercise_refs("compare exercise 7.1 q2 with exercise 7.3 q2")
        self.assertEqual(refs, ["7.1#2", "7.3#2"])


class ExerciseRefCacheIsolationTests(TestCase):
    """Regression tests for cross-exercise cache contamination.

    Bug: asking about exercise 7.3 repeatedly, then asking about 7.1,
    returned the cached 7.3 answer because normalize_query() strips the
    dot ("7.3" -> "7 3") making the queries near-identical to the fuzzy tier.
    """

    def setUp(self):
        self.service = get_semantic_cache_service()
        self.service.clear()
        self.context = {
            "grade": "10",
            "subject": "math",
            "unit": "",
            "chapter": "7",
            "chapter_title": "Trigonometry",
        }
        self.scope = scope_filters(self.context)

    def _learn(self, message, answer):
        return self.service.learn_from_ai(
            message=message,
            answer=answer,
            context=self.context,
            source="CDC Textbook — Math — Trigonometry",
            model="gemini-2.5-flash",
        )

    def test_learned_entry_stores_exercise_ref(self):
        cache = self._learn("solve exercise 7.3 question 2", make_quality_answer("Exercise 7.3 question 2"))
        self.assertIsNotNone(cache)
        cache.refresh_from_db()
        self.assertEqual(cache.exercise_ref, "7.3#2")

    def test_no_cross_exercise_contamination_after_repeated_queries(self):
        """The original bug scenario: hammer 7.3, then ask 7.1."""
        answer_73 = make_quality_answer("Exercise 7.3 question 2")
        answer_71 = make_quality_answer("Exercise 7.1 question 2")

        self._learn("solve exercise 7.3 question 2", answer_73)

        # Repeat 7.3 a few times — must keep hitting its own cache
        for _ in range(3):
            decision = self.service.inspect(
                "solve exercise 7.3 question 2", self.context, plan_tier="free"
            )
            self.assertEqual(decision.decision, DECISION_CACHE_HIT)
            self.assertIn("7.3", decision.answer)

        # Now ask 7.1 — must NOT return the 7.3 answer
        decision = self.service.inspect(
            "solve exercise 7.1 question 2", self.context, plan_tier="free"
        )
        self.assertEqual(
            decision.decision,
            DECISION_AI_REQUIRED,
            "7.1 query must not be served from the 7.3 cache entry",
        )

        # After learning 7.1, both must resolve to their own answers
        self._learn("solve exercise 7.1 question 2", answer_71)
        for message, marker in (
            ("solve exercise 7.1 question 2", "Exercise 7.1"),
            ("solve exercise 7.3 question 2", "Exercise 7.3"),
        ):
            decision = self.service.inspect(message, self.context, plan_tier="free")
            self.assertEqual(decision.decision, DECISION_CACHE_HIT)
            self.assertIn(marker, decision.answer)

    def test_no_cross_question_contamination_within_same_exercise(self):
        """7.3 q2 vs 7.3 q5 share 5 of 6 tokens — must stay isolated too."""
        self._learn("solve exercise 7.3 question 2", make_quality_answer("Exercise 7.3 question 2"))
        decision = self.service.inspect(
            "solve exercise 7.3 question 5", self.context, plan_tier="free"
        )
        self.assertEqual(decision.decision, DECISION_AI_REQUIRED)

    def test_refless_query_does_not_match_ref_entry(self):
        """Ambiguous follow-ups fall through to AI rather than guessing an exercise."""
        self._learn("solve exercise 7.3 question 2", make_quality_answer("Exercise 7.3 question 2"))
        decision = self.service.inspect(
            "solve the trigonometry sum", self.context, plan_tier="free"
        )
        self.assertEqual(decision.decision, DECISION_AI_REQUIRED)

    def test_kb_entries_hard_filtered_by_ref(self):
        query = "solve exercise 7.3 question 2"
        topic = extract_topic(query, self.context)
        intent = infer_intent(query)
        normalized = normalize_query(query)
        embedding = embed_text(
            f"{self.scope.get('chapter_title', '')} {topic} {intent} {normalized}"
        )
        KnowledgeBaseEntry.objects.create(
            subject="math",
            grade="10",
            chapter="7",
            chapter_title="Trigonometry",
            topic=topic,
            question_type=intent,
            intent=intent,
            normalized_query=normalized,
            exercise_ref="7.3#2",
            answer=make_quality_answer("Exercise 7.3 question 2"),
            source_type="precomputed",
            quality_score=0.9,
            textbook_alignment_score=0.9,
            hallucination_risk_score=0.08,
            embedding=embedding,
        )
        decision = self.service.inspect(
            "solve exercise 7.1 question 2", self.context, plan_tier="free"
        )
        self.assertEqual(decision.decision, DECISION_AI_REQUIRED)

        decision = self.service.inspect(query, self.context, plan_tier="free")
        self.assertEqual(decision.decision, DECISION_KB_HIT)


class SessionContextReconcileTests(TestCase):
    """Session record is authoritative over stale client context payloads."""

    def setUp(self):
        self.user = User.objects.create_user(username="student", password="x")
        self.session = ChatSession.objects.create(
            user=self.user,
            subject="Optional Mathematics",
            chapter="7. Trigonometry",
        )

    def test_stale_subject_and_foreign_chapter_dropped(self):
        """Client sends compulsory math subject+chapter into an omaths session."""
        context = _reconcile_session_context(
            self.session,
            {"subject": "Mathematics", "chapter": "1. Sets", "grade": "10"},
        )
        self.assertEqual(context["subject"], "Optional Mathematics")
        self.assertEqual(context["chapter"], "7. Trigonometry")

    def test_legit_chapter_change_is_persisted(self):
        context = _reconcile_session_context(
            self.session,
            {"subject": "Optional Mathematics", "chapter": "8. Coordinate Geometry"},
        )
        self.assertEqual(context["chapter"], "8. Coordinate Geometry")
        self.session.refresh_from_db()
        self.assertEqual(self.session.chapter, "8. Coordinate Geometry")

    def test_stale_payload_does_not_persist_foreign_chapter(self):
        _reconcile_session_context(
            self.session,
            {"subject": "Mathematics", "chapter": "1. Sets"},
        )
        self.session.refresh_from_db()
        self.assertEqual(self.session.subject, "Optional Mathematics")
        self.assertEqual(self.session.chapter, "7. Trigonometry")

    def test_missing_chapter_in_stale_payload_clears_chapter(self):
        """No session chapter + stale subject → no chapter, not a foreign one."""
        self.session.chapter = ""
        self.session.save()
        context = _reconcile_session_context(
            self.session,
            {"subject": "Mathematics", "chapter": "1. Sets"},
        )
        self.assertEqual(context["subject"], "Optional Mathematics")
        self.assertEqual(context.get("chapter", ""), "")

    def test_empty_context_is_passthrough(self):
        context = _reconcile_session_context(self.session, {})
        self.assertEqual(context, {})

    def test_subject_backfilled_on_legacy_session(self):
        legacy = ChatSession.objects.create(user=self.user, subject="", chapter="")
        context = _reconcile_session_context(
            legacy, {"subject": "Science", "chapter": "7. Motion and Force"}
        )
        self.assertEqual(context["subject"], "Science")
        legacy.refresh_from_db()
        self.assertEqual(legacy.subject, "Science")
        self.assertEqual(legacy.chapter, "7. Motion and Force")


class MigrationBackfillTests(TestCase):
    """The 0009 backfill logic must never restore a foreign chapter."""

    def test_backfill_skips_polluted_messages(self):
        user = User.objects.create_user(username="student2", password="x")
        session = ChatSession.objects.create(user=user, subject="Optional Mathematics")
        # Polluted message: compulsory math chapter saved in omaths session
        ChatMessage.objects.create(
            user=user, session=session, message="q1", response="a1",
            context={"subject": "Mathematics", "chapter": "1. Sets"},
        )
        # Good message: correct subject + chapter
        ChatMessage.objects.create(
            user=user, session=session, message="q2", response="a2",
            context={"subject": "Optional Mathematics", "chapter": "7. Trigonometry"},
        )
        # Re-run the backfill logic directly against the models
        from django.apps import apps as global_apps
        ChatSessionModel = global_apps.get_model("api", "ChatSession")
        ChatMessageModel = global_apps.get_model("api", "ChatMessage")
        for s in ChatSessionModel.objects.all().iterator():
            if (s.chapter or "").strip():
                continue
            subject = (s.subject or "").strip()
            if not subject:
                continue
            chapter = ""
            for message in (
                ChatMessageModel.objects.filter(session_id=s.id)
                .order_by("-created_at").only("context").iterator()
            ):
                message_context = message.context or {}
                if (
                    str(message_context.get("subject") or "").strip() == subject
                    and str(message_context.get("chapter") or "").strip()
                ):
                    chapter = str(message_context["chapter"]).strip()[:255]
                    break
            if chapter:
                s.chapter = chapter
                s.save(update_fields=["chapter"])
        session.refresh_from_db()
        self.assertEqual(session.chapter, "7. Trigonometry")


class FingerprintAndLRURefTests(TestCase):
    def test_fingerprint_separates_exercises(self):
        scope = scope_filters({"grade": "10", "subject": "math", "chapter": "7"})
        fp1 = educational_fingerprint(scope, "solved_exercise", "trigonometry", "solve exercise 7 1 question 2", "7.1#2")
        fp3 = educational_fingerprint(scope, "solved_exercise", "trigonometry", "solve exercise 7 3 question 2", "7.3#2")
        self.assertNotEqual(fp1, fp3)

    def test_lru_key_separates_exercises(self):
        cache = _LRUCache()
        scope = {"grade": "10", "subject": "math", "unit": "", "chapter": "7"}
        cache.put(scope, "solved_exercise", "solve exercise 7 3 question 2", "answer 7.3", 0.95, exercise_ref="7.3#2")
        # Same normalized tokens, different exercise ref — must miss
        hit = cache.get(scope, "solved_exercise", "solve exercise 7 3 question 2", exercise_ref="7.1#2")
        self.assertIsNone(hit)
        # Correct ref — must hit
        hit = cache.get(scope, "solved_exercise", "solve exercise 7 3 question 2", exercise_ref="7.3#2")
        self.assertEqual(hit[0], "answer 7.3")
