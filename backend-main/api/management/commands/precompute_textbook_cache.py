import json
import os
import re
import subprocess
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from api.chapter_pdf_context import (
    NEPALI_PAGE_RANGES,
    SIMPLE_CHAPTER_TITLES,
    SIMPLE_PAGE_RANGES,
    get_pdf_path,
    SOCIAL_PAGE_RANGES,
    get_textbook_pages,
)
from api.content_processor import (
    CONTENT_PROCESSOR_SYSTEM_PROMPT,
    build_content_processor_prompt,
    build_entries_from_processed_payload,
    extract_json_object,
    normalize_processed_payload,
    save_processed_entries,
)
from api.models import KnowledgeBaseEntry


@dataclass
class ChapterJob:
    subject: str
    grade: str
    chapter: str
    topic: str
    start_page: int
    end_page: int
    unit: str = ""
    chapter_title: str = ""


SOCIAL_UNIT_TITLES = {
    1: "We and Our Society",
    2: "Development and Its Infrastructures",
    3: "Our Social Values and Norms",
    4: "Social Problems and Solutions",
    5: "Civic Awareness",
    6: "Our Earth",
    7: "Our Past",
    8: "Economic Activities",
    9: "International Relations, Cooperation and Organizations",
    10: "Population and Its Management",
}


SOCIAL_CHAPTER_TITLES = {
    (1, 1): "Socialization",
    (1, 2): "Our Identity",
    (1, 3): "Unity in Diversity",
    (1, 4): "National Pride",
    (2, 1): "Human Development Index",
    (2, 2): "Sustainable Development",
    (2, 3): "Federalism in Nepal",
    (2, 4): "Projects of National Pride",
    (3, 1): "National Heritage",
    (3, 2): "Folk Songs of Nepal",
    (3, 3): "Folk Instruments of Nepal",
    (3, 4): "Folk and Classical Dances",
    (3, 5): "National Days",
    (3, 6): "International Personalities",
    (3, 7): "Universal Brotherhood and Humanity",
    (3, 8): "Social Responsibility",
    (4, 1): "Human Trafficking",
    (4, 2): "Sexual Distortion and Anomalies",
    (4, 3): "Domestic Violence",
    (4, 4): "Corruption",
    (4, 5): "Superstition",
    (4, 6): "Problem Identification and Solving Skills",
    (4, 7): "Role of International Organizations",
    (5, 1): "Legislature",
    (5, 2): "Federal Executive",
    (5, 3): "Judiciary",
    (5, 4): "Political Parties",
    (5, 5): "Election Process and Citizen Role",
    (5, 6): "Human Rights",
    (5, 7): "Role of Organizations in Human Rights Protection",
    (5, 8): "Consumer Rights",
    (6, 1): "Climate and Its Affecting Factors",
    (6, 2): "Types of World Climate",
    (6, 3): "Tropical Zone",
    (6, 4): "Temperate Zone",
    (6, 5): "Polar Region",
    (6, 6): "World Climate: Relief Diversity and Effects",
    (6, 7): "North America",
    (6, 8): "South America",
    (6, 9): "Africa",
    (6, 10): "Earthquake",
    (6, 11): "Map Work",
    (6, 12): "Modern Map Technology",
    (7, 1): "Revolution of 2007 BS and Delhi Agreement",
    (7, 2): "Political Events from 2017 BS to 2046 BS",
    (7, 3): "Political Events from 2046 BS to 2063 BS",
    (7, 4): "Political Events from 2063 BS to 2079 BS",
    (7, 5): "World War I: Causes and Events",
    (7, 6): "Consequences of World War I",
    (7, 7): "World War II and Its Causes",
    (7, 8): "Consequences of World War II and Nepal's Role",
    (7, 9): "Identification and Preservation of Local Historical Sites",
    (8, 1): "Energy and Development",
    (8, 2): "Tourism Promotion",
    (8, 3): "Employment and Foreign Employment",
    (8, 4): "Financial Education",
    (8, 5): "Financial Instruments",
    (8, 6): "Cooperatives",
    (8, 7): "Revenue",
    (8, 8): "Periodic Plan",
    (9, 1): "Foreign Policy of Nepal",
    (9, 2): "United Nations",
    (9, 3): "Specialized Agencies of the United Nations",
    (9, 4): "Globalization and Localization",
    (9, 5): "Information and Communication Technology",
    (10, 1): "Population Size and Growth of Nepal",
    (10, 2): "Population Composition of Nepal",
    (10, 3): "Population Distribution",
    (10, 4): "Family Planning and Quality of Life",
    (10, 5): "Population and Environment Relationship",
    (10, 6): "Community Health",
}


NEPALI_CHAPTER_TITLES = {
    1: "Ujyalo Yatra",
    2: "Ghar Jhagada",
    3: "Chikitsa Bigyan ra Ayurveda Chikitsa",
    4: "Yasto Kahilyai Nahos",
    5: "Laxmi Prasad Devkota",
    6: "Adhikar Thulo ki Kartavya Thulo",
    7: "Shatru",
    8: "Nepali Hamro Shram ra Sip",
    9: "Mero Deshko Shiksha",
    10: "Byabasayik Chithi",
    11: "Kartavya",
    12: "Pablo Picasso",
    13: "Parkhanuhos",
    14: "Ghar ko Maya",
    15: "Gaunmathi Euta Kabita",
    16: "Aayam",
    17: "Sanduk Ruit",
}


def build_jobs(subjects: Iterable[str]) -> List[ChapterJob]:
    jobs = []
    wanted = {subject.strip().lower() for subject in subjects if subject.strip()}

    if "math" in wanted:
        for chapter, page_range in SIMPLE_PAGE_RANGES["math"].items():
            title = SIMPLE_CHAPTER_TITLES["math"].get(chapter, f"Chapter {chapter}")
            jobs.append(ChapterJob("math", "10", str(chapter), title, *page_range, chapter_title=title))

    if "science" in wanted:
        for chapter, page_range in SIMPLE_PAGE_RANGES["science"].items():
            title = SIMPLE_CHAPTER_TITLES["science"].get(chapter, f"Chapter {chapter}")
            jobs.append(ChapterJob("science", "10", str(chapter), title, *page_range, chapter_title=title))

    if "social" in wanted:
        for (unit, chapter), page_range in SOCIAL_PAGE_RANGES.items():
            title = SOCIAL_CHAPTER_TITLES.get((unit, chapter), f"Unit {unit} Chapter {chapter}")
            topic = f"{SOCIAL_UNIT_TITLES.get(unit, f'Unit {unit}')} - {title}"
            jobs.append(ChapterJob("social", "10", str(chapter), topic, *page_range, unit=str(unit), chapter_title=title))

    if "nepali" in wanted:
        for chapter, page_range in NEPALI_PAGE_RANGES.items():
            title = NEPALI_CHAPTER_TITLES.get(chapter, f"Chapter {chapter}")
            jobs.append(ChapterJob("nepali", "10", str(chapter), title, *page_range, chapter_title=title))

    return jobs


def extract_chapter_text(job: ChapterJob) -> tuple:
    pages = get_textbook_pages(job.subject, job.start_page, job.end_page)
    readable = []
    statuses = {"readable": 0, "legacy_font": 0, "no_text": 0}
    for page in pages:
        status = page.get("text_status", "no_text")
        statuses[status] = statuses.get(status, 0) + 1
        text = str(page.get("text") or "").strip()
        if text:
            readable.append(f"[Page {page['page']}]\n{text}")
    return "\n\n".join(readable).strip(), statuses


def cached_ocr_path(cache_dir: str, job: ChapterJob) -> Path:
    unit = f"_u{job.unit}" if job.unit else ""
    filename = f"{job.subject}{unit}_c{job.chapter}_p{job.start_page}-{job.end_page}.txt"
    return Path(cache_dir) / filename


def extract_chapter_text_with_ocr(
    job: ChapterJob,
    tesseract_path: str,
    pdftoppm_path: str,
    lang: str,
    dpi: int,
    cache_dir: str,
    force_ocr: bool = False,
) -> tuple:
    cache_file = cached_ocr_path(cache_dir, job)
    if cache_file.exists() and not force_ocr:
        text = cache_file.read_text(encoding="utf-8").strip()
        return text, {"ocr_cached": 1, "readable": 0, "legacy_font": 0, "no_text": 0}

    pdf_path = get_pdf_path(job.subject)
    if not pdf_path:
        return "", {"ocr_error": 1, "readable": 0, "legacy_font": 0, "no_text": 0}

    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    parts = []
    statuses = {"ocr_pages": 0, "ocr_error": 0, "readable": 0, "legacy_font": 0, "no_text": 0}
    with tempfile.TemporaryDirectory(prefix="noya_ocr_") as temp_dir:
        temp_path = Path(temp_dir)
        for page_no in range(job.start_page, job.end_page + 1):
            prefix = temp_path / f"page_{page_no}"
            try:
                subprocess.run(
                    [
                        pdftoppm_path,
                        "-f",
                        str(page_no),
                        "-l",
                        str(page_no),
                        "-r",
                        str(dpi),
                        "-png",
                        str(pdf_path),
                        str(prefix),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=90,
                )
                image_files = sorted(temp_path.glob(f"page_{page_no}-*.png"))
                if not image_files:
                    statuses["ocr_error"] += 1
                    continue
                result = subprocess.run(
                    [
                        tesseract_path,
                        str(image_files[0]),
                        "stdout",
                        "-l",
                        lang,
                        "--psm",
                        "6",
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=120,
                )
                text = clean_ocr_text(result.stdout, job.subject)
                if text:
                    parts.append(f"[Page {page_no}]\n{text}")
                    statuses["ocr_pages"] += 1
            except (subprocess.SubprocessError, OSError):
                statuses["ocr_error"] += 1

    text = "\n\n".join(parts).strip()
    if text:
        cache_file.write_text(text, encoding="utf-8")
    return text, statuses


def clean_ocr_text(text: str, subject: str = "") -> str:
    subject = (subject or "").lower()
    text = unicodedata.normalize("NFC", text or "").replace("\x0c", " ")
    text = text.replace("\u200c", "").replace("\u200d", "")
    lines = []
    for line in text.splitlines():
        line = clean_ocr_line(line, subject)
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


def clean_ocr_line(line: str, subject: str = "") -> str:
    line = " ".join((line or "").split())
    if not line:
        return ""

    if subject in {"social", "nepali"}:
        line = clean_devanagari_ocr_line(line)
    else:
        line = clean_english_ocr_line(line)

    line = re.sub(r"\s+([।,.;:!?%)])", r"\1", line)
    line = re.sub(r"([(])\s+", r"\1", line)
    line = re.sub(r"\s{2,}", " ", line).strip()
    return line


def clean_devanagari_ocr_line(line: str) -> str:
    devanagari = sum("\u0900" <= char <= "\u097f" for char in line)
    ascii_letters = sum(("a" <= char.lower() <= "z") for char in line)
    junk = sum(char in "@#$%^&*+=<>~\\|_{}[]" for char in line)
    total = max(1, len(line))

    if devanagari == 0 and (ascii_letters > 0 or junk > 0):
        return ""
    if devanagari < 3 and (ascii_letters + junk) / total > 0.35:
        return ""

    line = re.sub(r"[A-Za-z]{1,12}", " ", line)
    line = re.sub(r"[#@$%^&*+=<>~\\|_{}[\]¢:]", " ", line)
    line = re.sub(r"[“”\"`]+", " ", line)
    line = re.sub(r"\b[0-9]{1,4}\b", " ", line)
    line = re.sub(r"\s+[।|]\s*$", " ।", line)
    line = re.sub(r"^[।|,.;:!?()\\/-]+$", "", line)
    return " ".join(line.split())


def clean_english_ocr_line(line: str) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,;:!?()[]+-=/%°'\" ")
    junk = sum(char not in allowed and not ("\u0900" <= char <= "\u097f") for char in line)
    if junk / max(1, len(line)) > 0.35:
        return ""
    line = re.sub(r"[#@$^~`{}<>\\|¢]+", " ", line)
    return " ".join(line.split())


def clean_cached_ocr_text(text: str, subject: str = "") -> str:
    parts = []
    current_page = None
    buffer = []

    def flush():
        if current_page and buffer:
            cleaned = clean_ocr_text("\n".join(buffer), subject)
            if cleaned:
                parts.append(f"[Page {current_page}]\n{cleaned}")

    for raw_line in (text or "").splitlines():
        match = re.match(r"^\[Page\s+(\d+)\]\s*$", raw_line.strip())
        if match:
            flush()
            current_page = match.group(1)
            buffer = []
        else:
            buffer.append(raw_line)
    flush()
    if not parts:
        return clean_ocr_text(text, subject)
    return "\n\n".join(parts).strip()


def ocr_subject_from_filename(path: Path) -> str:
    name = path.name.lower()
    if name.startswith("social"):
        return "social"
    if name.startswith("nepali"):
        return "nepali"
    if name.startswith("science"):
        return "science"
    return ""


def trim_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    trimmed = text[:max_chars]
    last_break = trimmed.rfind("\n[Page ")
    if last_break > max_chars * 0.65:
        trimmed = trimmed[:last_break]
    return trimmed.strip()


class Command(BaseCommand):
    help = "Precompute Grade 10 textbook KnowledgeBaseEntry records from local CDC PDFs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--subjects",
            default="social,science,math,nepali",
            help="Comma-separated subjects: social, science, math, nepali.",
        )
        parser.add_argument("--limit", type=int, default=0, help="Process at most N chapters.")
        parser.add_argument("--dry-run", action="store_true", help="Audit extraction without calling AI or saving.")
        parser.add_argument("--skip-existing", action="store_true", help="Skip chapters with active precomputed entries.")
        parser.add_argument("--min-chars", type=int, default=600, help="Minimum readable textbook characters required.")
        parser.add_argument("--max-chars", type=int, default=22000, help="Maximum textbook characters sent per chapter.")
        parser.add_argument("--ocr", action="store_true", help="Use Tesseract OCR when PDF text extraction is insufficient.")
        parser.add_argument("--force-ocr", action="store_true", help="Ignore cached OCR text and re-extract pages.")
        parser.add_argument("--ocr-cache-dir", default="backend-main/ocr_cache/class_10", help="Directory for one-time OCR text.")
        parser.add_argument("--ocr-lang", default="", help="Tesseract language override, for example eng or nep+eng.")
        parser.add_argument("--ocr-dpi", type=int, default=170, help="OCR render DPI.")
        parser.add_argument("--tesseract-path", default=os.environ.get("TESSERACT_PATH", "tesseract"))
        parser.add_argument("--pdftoppm-path", default=os.environ.get("PDFTOPPM_PATH", "pdftoppm"))
        parser.add_argument("--raw-only", action="store_true", help="Store safe raw textbook entries without AI processing.")
        parser.add_argument("--clean-ocr-cache", action="store_true", help="Clean existing cached OCR text files and exit.")
        parser.add_argument(
            "--raw-fallback",
            action="store_true",
            help="If AI processing fails, store a safe raw textbook chapter entry instead.",
        )

    def handle(self, *args, **options):
        subjects = [item.strip().lower() for item in options["subjects"].split(",")]
        unknown = sorted(set(subjects) - {"social", "science", "math", "nepali", ""})
        if unknown:
            raise CommandError(f"Unknown subjects: {', '.join(unknown)}")

        if options["clean_ocr_cache"]:
            self._clean_ocr_cache(options["ocr_cache_dir"], subjects, options["dry_run"])
            return

        jobs = build_jobs(subjects)
        if options["limit"]:
            jobs = jobs[: options["limit"]]

        if not jobs:
            raise CommandError("No textbook chapters matched the selected subjects.")

        service = None
        summary = {"saved": 0, "generated": 0, "skipped": 0, "failed": 0, "needs_ocr": 0}
        failures = []

        for index, job in enumerate(jobs, start=1):
            label = self._label(job)
            if options["skip_existing"] and self._has_existing(job):
                summary["skipped"] += 1
                self.stdout.write(f"[{index}/{len(jobs)}] SKIP existing: {label}")
                continue

            raw_text, statuses = extract_chapter_text(job)
            readable_chars = len(raw_text)
            if options["ocr"] and readable_chars < options["min_chars"]:
                lang = options["ocr_lang"] or ("nep+eng" if job.subject in {"social", "nepali"} else "eng")
                self.stdout.write(f"[{index}/{len(jobs)}] OCR: {label} ({lang})")
                raw_text, statuses = extract_chapter_text_with_ocr(
                    job,
                    options["tesseract_path"],
                    options["pdftoppm_path"],
                    lang,
                    options["ocr_dpi"],
                    options["ocr_cache_dir"],
                    options["force_ocr"],
                )
                readable_chars = len(raw_text)
            status_text = ", ".join(f"{key}={value}" for key, value in sorted(statuses.items()))

            if readable_chars < options["min_chars"]:
                summary["needs_ocr"] += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"[{index}/{len(jobs)}] NEEDS OCR: {label} "
                        f"({readable_chars} chars; {status_text})"
                    )
                )
                continue

            if options["raw_only"]:
                if options["dry_run"]:
                    summary["skipped"] += 1
                    self.stdout.write(
                        f"[{index}/{len(jobs)}] RAW READY: {label} "
                        f"({readable_chars} chars; {status_text})"
                    )
                    continue
                saved_count = self._save_raw_fallback(job, raw_text, statuses)
                summary["saved"] += saved_count
                summary["generated"] += 1
                self.stdout.write(self.style.SUCCESS(f"[{index}/{len(jobs)}] RAW SAVED {saved_count}: {label}"))
                continue

            if options["dry_run"]:
                summary["skipped"] += 1
                self.stdout.write(
                    f"[{index}/{len(jobs)}] READY: {label} "
                    f"({readable_chars} chars; {status_text})"
                )
                continue

            if service is None:
                from api.ai_service import AIService

                service = AIService()

            payload = {
                "subject": job.subject,
                "grade": job.grade,
                "unit": job.unit,
                "chapter": job.chapter,
                "chapter_title": job.chapter_title,
                "topic": job.topic,
                "raw_textbook_content": trim_text(raw_text, options["max_chars"]),
            }

            try:
                raw_response = service._generate_with_fallbacks(
                    build_content_processor_prompt(
                        payload["subject"],
                        payload["grade"],
                        payload["chapter"],
                        payload["topic"],
                        payload["raw_textbook_content"],
                    ),
                    CONTENT_PROCESSOR_SYSTEM_PROMPT,
                )
                processed = normalize_processed_payload(extract_json_object(raw_response), payload)
                entries = build_entries_from_processed_payload(processed, payload)
                saved_count, _saved_ids = save_processed_entries(entries)
                summary["saved"] += saved_count
                summary["generated"] += 1
                self.stdout.write(self.style.SUCCESS(f"[{index}/{len(jobs)}] SAVED {saved_count}: {label}"))
            except Exception as exc:
                if options["raw_fallback"]:
                    saved_count = self._save_raw_fallback(job, raw_text, statuses)
                    summary["saved"] += saved_count
                    summary["generated"] += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"[{index}/{len(jobs)}] RAW FALLBACK {saved_count}: {label} ({exc})"
                        )
                    )
                    continue
                summary["failed"] += 1
                failures.append({"chapter": label, "error": str(exc)})
                self.stdout.write(self.style.ERROR(f"[{index}/{len(jobs)}] FAILED: {label} ({exc})"))

        self.stdout.write(self.style.SUCCESS("Precompute summary:"))
        self.stdout.write(json.dumps(summary, indent=2))
        if failures:
            self.stdout.write(self.style.ERROR("Failures:"))
            self.stdout.write(json.dumps(failures, indent=2))

    def _label(self, job: ChapterJob) -> str:
        unit = f" Unit {job.unit}" if job.unit else ""
        return f"{job.subject.title()}{unit} Chapter {job.chapter}: {job.chapter_title or job.topic}"

    def _has_existing(self, job: ChapterJob) -> bool:
        return KnowledgeBaseEntry.objects.filter(
            subject=job.subject,
            grade=job.grade,
            unit=job.unit,
            chapter=job.chapter,
            source_type="precomputed",
            is_active=True,
        ).exists()

    def _clean_ocr_cache(self, cache_dir: str, subjects: List[str], dry_run: bool) -> None:
        wanted = {subject for subject in subjects if subject}
        files = sorted(Path(cache_dir).glob("*.txt"))
        updated = 0
        before_chars = 0
        after_chars = 0
        before_noise = 0
        after_noise = 0

        for path in files:
            subject = ocr_subject_from_filename(path)
            if wanted and subject not in wanted:
                continue
            original = path.read_text(encoding="utf-8")
            cleaned = clean_cached_ocr_text(original, subject)
            before_chars += len(original)
            after_chars += len(cleaned)
            before_noise += self._noise_count(original, subject)
            after_noise += self._noise_count(cleaned, subject)
            if cleaned != original:
                updated += 1
                if not dry_run:
                    path.write_text(cleaned + "\n", encoding="utf-8")

        self.stdout.write(json.dumps({
            "files_checked": len(files),
            "files_updated": updated,
            "before_chars": before_chars,
            "after_chars": after_chars,
            "before_noise": before_noise,
            "after_noise": after_noise,
            "dry_run": dry_run,
        }, indent=2))

    def _noise_count(self, text: str, subject: str) -> int:
        if subject in {"social", "nepali"}:
            return sum(("a" <= char.lower() <= "z") or char in "@#$%^&*+=<>~\\|_{}[]¢" for char in text)
        return sum(char in "@#$^~`{}<>\\|¢" for char in text)

    def _save_raw_fallback(self, job: ChapterJob, raw_text: str, statuses: dict) -> int:
        from api.semantic_cache import educational_fingerprint, embed_text, normalize_query, scope_filters

        scope = scope_filters({
            "subject": job.subject,
            "grade": job.grade,
            "unit": job.unit,
            "chapter": job.chapter,
            "chapter_title": job.chapter_title,
        })
        normalized = normalize_query(f"{job.topic} textbook chapter source")
        fingerprint = educational_fingerprint(scope, "explain", job.topic, normalized)
        answer = (
            f"{job.topic}\n\n"
            "Textbook source extract:\n"
            f"{trim_text(raw_text, 12000)}\n\n"
            f"Source pages: {job.start_page}-{job.end_page}"
        )
        entry, _ = KnowledgeBaseEntry.objects.update_or_create(
            query_fingerprint=fingerprint,
            subject=job.subject,
            grade=job.grade,
            unit=job.unit,
            chapter=job.chapter,
            question_type="explain",
            defaults={
                "chapter_title": job.chapter_title,
                "topic": job.topic,
                "learning_objective": "Textbook-grounded chapter source",
                "difficulty": "easy",
                "intent": "explain",
                "normalized_query": normalized,
                "embedding": embed_text(f"{job.topic} {normalized} {answer[:800]}"),
                "answer": answer,
                "source_type": "precomputed",
                "source_reference": f"cdc_textbook pages {job.start_page}-{job.end_page}",
                "quality_score": 0.72,
                "textbook_alignment_score": 1.0,
                "hallucination_risk_score": 0.02,
                "last_verified_at": timezone.now(),
                "metadata": {
                    "precompute_mode": "raw_fallback",
                    "page_statuses": statuses,
                    "source_pages": [job.start_page, job.end_page],
                },
                "is_active": True,
            },
        )
        return 1 if entry else 0
