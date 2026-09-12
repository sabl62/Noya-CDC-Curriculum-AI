import json
import re
from typing import Dict, List, Tuple

from .models import KnowledgeBaseEntry
from .semantic_cache import (
    educational_fingerprint,
    embed_text,
    extract_topic,
    infer_intent,
    normalize_query,
    scope_filters,
)


CONTENT_PROCESSOR_SCHEMA_KEYS = [
    "subject",
    "grade",
    "chapter",
    "topic",
    "concept",
    "definition",
    "simple_explanation",
    "detailed_explanation",
    "important_points",
    "key_terms",
    "exam_notes",
    "one_line_revision",
    "common_exam_questions",
    "short_answer_questions",
    "long_answer_questions",
    "mcqs",
    "true_false",
    "fill_in_the_blanks",
    "memory_tips",
    "related_concepts",
    "difficulty_level",
    "curriculum_alignment_score",
    "source_type",
]


CONTENT_PROCESSOR_SYSTEM_PROMPT = """
You are an educational content processing engine for Noya, a Grade 10 CDC curriculum learning platform.

MISSION
Transform the provided textbook content into structured educational records.

CRITICAL RULES
1. The textbook is the source of truth.
2. Never invent facts that are not supported by the provided content.
3. Never add information from your own knowledge unless explicitly stated in the textbook content.
4. Preserve CDC terminology whenever possible.
5. Prioritize exam relevance and curriculum alignment.
6. Write explanations suitable for Grade 10 students.
7. If information is missing from the provided content, leave the field empty rather than hallucinating.
8. Output VALID JSON ONLY.
9. Do not include markdown.
10. Do not include explanations outside the JSON.

Required JSON Schema:
{
"subject": "",
"grade": "",
"chapter": "",
"topic": "",
"concept": "",
"definition": "",
"simple_explanation": "",
"detailed_explanation": "",
"important_points": [],
"key_terms": [],
"exam_notes": [],
"one_line_revision": "",
"common_exam_questions": [],
"short_answer_questions": [{"question": "", "answer": ""}],
"long_answer_questions": [{"question": "", "answer_outline": []}],
"mcqs": [{"question": "", "options": [], "correct_answer": "", "explanation": ""}],
"true_false": [{"statement": "", "answer": true, "explanation": ""}],
"fill_in_the_blanks": [{"question": "", "answer": ""}],
"memory_tips": [],
"related_concepts": [],
"difficulty_level": "",
"curriculum_alignment_score": 100,
"source_type": "cdc_textbook"
}
""".strip()


def build_content_processor_prompt(subject: str, grade: str, chapter: str, topic: str, raw_textbook_content: str) -> str:
    return f"""
INPUT
Subject: {subject}
Grade: {grade}
Chapter: {chapter}
Topic: {topic}

RAW TEXTBOOK CONTENT:
{raw_textbook_content}

Return ONLY a single valid JSON object matching the schema.
""".strip()


def extract_json_object(text: str) -> Dict:
    cleaned = str(text or "").strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("AI did not return a JSON object")
    return json.loads(cleaned[start:end + 1])


def normalize_processed_payload(payload: Dict, fallback: Dict) -> Dict:
    normalized = {key: payload.get(key, [] if key in {
        "important_points",
        "key_terms",
        "exam_notes",
        "common_exam_questions",
        "short_answer_questions",
        "long_answer_questions",
        "mcqs",
        "true_false",
        "fill_in_the_blanks",
        "memory_tips",
        "related_concepts",
    } else "") for key in CONTENT_PROCESSOR_SCHEMA_KEYS}

    normalized["subject"] = str(normalized.get("subject") or fallback.get("subject", "")).strip()
    normalized["grade"] = str(normalized.get("grade") or fallback.get("grade", "10")).strip()
    normalized["chapter"] = str(normalized.get("chapter") or fallback.get("chapter", "")).strip()
    normalized["topic"] = str(normalized.get("topic") or fallback.get("topic", "")).strip()
    normalized["source_type"] = normalized.get("source_type") or "cdc_textbook"
    try:
        normalized["curriculum_alignment_score"] = int(normalized.get("curriculum_alignment_score") or 100)
    except (TypeError, ValueError):
        normalized["curriculum_alignment_score"] = 100
    return normalized


def render_processed_answer(payload: Dict, answer_type: str) -> str:
    topic = payload.get("topic") or payload.get("concept") or ""
    lines = []
    if topic:
        lines.append(str(topic))

    if answer_type == "definition":
        if payload.get("definition"):
            lines.append(f"Definition: {payload['definition']}")
        if payload.get("simple_explanation"):
            lines.append(f"Simple explanation: {payload['simple_explanation']}")
    elif answer_type == "explain":
        if payload.get("simple_explanation"):
            lines.append(f"Simple explanation: {payload['simple_explanation']}")
        if payload.get("detailed_explanation"):
            lines.append(f"Detailed explanation: {payload['detailed_explanation']}")
        if payload.get("important_points"):
            lines.append("Important points:")
            lines.extend([f"- {item}" for item in payload["important_points"]])
    elif answer_type == "exam_notes":
        lines.append("Exam notes:")
        lines.extend([f"- {item}" for item in payload.get("exam_notes", [])])
        if payload.get("one_line_revision"):
            lines.append(f"One-line revision: {payload['one_line_revision']}")
    elif answer_type == "important_questions":
        lines.append("Common exam questions:")
        lines.extend([f"- {item}" for item in payload.get("common_exam_questions", [])])
        for item in payload.get("short_answer_questions", []):
            question = item.get("question", "")
            answer = item.get("answer", "")
            if question:
                lines.append(f"Q: {question}")
            if answer:
                lines.append(f"A: {answer}")
        for item in payload.get("long_answer_questions", []):
            question = item.get("question", "")
            outline = item.get("answer_outline", [])
            if question:
                lines.append(f"Long answer: {question}")
            lines.extend([f"- {point}" for point in outline])
    elif answer_type == "quiz":
        for item in payload.get("mcqs", []):
            question = item.get("question", "")
            if question:
                lines.append(f"MCQ: {question}")
            for option in item.get("options", []):
                lines.append(f"- {option}")
            if item.get("correct_answer"):
                lines.append(f"Correct answer: {item['correct_answer']}")
            if item.get("explanation"):
                lines.append(f"Explanation: {item['explanation']}")
        for item in payload.get("true_false", []):
            statement = item.get("statement", "")
            if statement:
                lines.append(f"True/False: {statement}")
                lines.append(f"Answer: {'True' if item.get('answer') else 'False'}")
            if item.get("explanation"):
                lines.append(f"Explanation: {item['explanation']}")
    elif answer_type == "summary":
        if payload.get("one_line_revision"):
            lines.append(payload["one_line_revision"])
        if payload.get("important_points"):
            lines.extend([f"- {item}" for item in payload["important_points"]])

    return "\n".join([line for line in lines if str(line).strip()]).strip()


def build_entries_from_processed_payload(payload: Dict, context: Dict = None) -> List[KnowledgeBaseEntry]:
    context = context or {}
    scope = scope_filters({
        "subject": payload.get("subject") or context.get("subject", ""),
        "grade": payload.get("grade") or context.get("grade", "10"),
        "unit": context.get("unit", ""),
        "chapter": payload.get("chapter") or context.get("chapter", ""),
        "chapter_title": context.get("chapter_title", "") or payload.get("topic", ""),
    })
    difficulty = str(payload.get("difficulty_level") or "easy").lower() or "easy"
    topic = payload.get("topic") or payload.get("concept") or extract_topic(payload.get("detailed_explanation", ""), scope)
    alignment = max(0.0, min(1.0, float(payload.get("curriculum_alignment_score", 100)) / 100))

    answer_types = ["definition", "explain", "exam_notes", "important_questions", "quiz", "summary"]
    entries = []
    for answer_type in answer_types:
        answer = render_processed_answer(payload, answer_type)
        if len(answer) < 40:
            continue
        normalized = normalize_query(f"{topic} {answer_type} {payload.get('concept', '')}")
        intent = infer_intent(answer_type, answer_type)
        fingerprint = educational_fingerprint(scope, intent, topic, normalized)
        embedding = embed_text(f"{scope.get('chapter_title', '')} {topic} {intent} {normalized} {answer[:800]}")
        entries.append(KnowledgeBaseEntry(
            subject=scope["subject"],
            grade=scope["grade"],
            unit=scope["unit"],
            chapter=scope["chapter"],
            chapter_title=scope["chapter_title"],
            topic=topic,
            learning_objective=payload.get("concept", ""),
            question_type=intent,
            difficulty=difficulty,
            intent=intent,
            normalized_query=normalized,
            query_fingerprint=fingerprint,
            embedding=embedding,
            answer=answer,
            source_type="precomputed",
            source_reference=payload.get("source_type", "cdc_textbook"),
            quality_score=round(0.82 + (alignment * 0.14), 4),
            textbook_alignment_score=alignment,
            hallucination_risk_score=round(max(0.03, 0.18 - alignment * 0.1), 4),
            metadata={"processed_payload": payload},
            is_active=True,
        ))
    return entries


def save_processed_entries(entries: List[KnowledgeBaseEntry]) -> Tuple[int, List[int]]:
    saved_ids = []
    for entry in entries:
        saved, _ = KnowledgeBaseEntry.objects.update_or_create(
            query_fingerprint=entry.query_fingerprint,
            subject=entry.subject,
            grade=entry.grade,
            unit=entry.unit,
            chapter=entry.chapter,
            question_type=entry.question_type,
            defaults={
                "chapter_title": entry.chapter_title,
                "topic": entry.topic,
                "learning_objective": entry.learning_objective,
                "difficulty": entry.difficulty,
                "intent": entry.intent,
                "normalized_query": entry.normalized_query,
                "embedding": entry.embedding,
                "answer": entry.answer,
                "source_type": entry.source_type,
                "source_reference": entry.source_reference,
                "quality_score": entry.quality_score,
                "textbook_alignment_score": entry.textbook_alignment_score,
                "hallucination_risk_score": entry.hallucination_risk_score,
                "metadata": entry.metadata,
                "is_active": True,
            },
        )
        saved_ids.append(saved.id)
    return len(saved_ids), saved_ids
