import re
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


# ─── Devanagari numeral helpers ─────────────────────────────

_DEVANAGARI_DIGITS = "०१२३४५६७८९"
_ARABIC_DIGITS = "0123456789"


def _devanagari_to_arabic(s: str) -> str:
    """Convert Devanagari numerals in a string to Arabic numerals."""
    return s.translate(str.maketrans(_DEVANAGARI_DIGITS, _ARABIC_DIGITS))


def _leading_unit_chapter(title: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse leading numerals from chapter titles.

    Examples:
        "3. Living Beings..."          -> (None, 3)
        "3 Living Beings..."             -> (None, 3)
        "१.१ हामी र हाम्रो समाज"        -> (1, 1)
        "1.1 Our Society"                -> (1, 1)
    """
    if not title:
        return None, None

    normalized = _devanagari_to_arabic(title.strip())

    # Try "X.Y Title" (unit.chapter) — e.g. "1.1", "१.१"
    m = re.match(r"^(\d+)\.(\d+)[\s\.\-]+", normalized)
    if m:
        return int(m.group(1)), int(m.group(2))

    # Try single leading number — e.g. "3. Title", "3 Title"
    m = re.match(r"^(\d+)[\s\.\-]+", normalized)
    if m:
        return None, int(m.group(1))

    return None, None


# ─── OCR cache helpers ──────────────────────────────────────

def _get_cached_ocr_page_text(subject: str, page_no: int) -> Optional[str]:
    """Retrieves text for a specific page from the pre-computed OCR cache if available."""
    subject = (subject or "").lower()
    base_dir = Path(__file__).resolve().parent.parent
    cache_dir = base_dir / "ocr_cache" / "class_10"
    if not cache_dir.exists():
        return None

    prefix = f"{subject}_"
    for file_path in cache_dir.glob(f"{prefix}*.txt"):
        try:
            parts = file_path.stem.split("_")
            if len(parts) >= 3 and parts[-1].startswith("p"):
                range_str = parts[-1][1:]
                start_str, end_str = range_str.split("-")
                if int(start_str) <= page_no <= int(end_str):
                    content = file_path.read_text(encoding="utf-8")
                    page_marker = f"[Page {page_no}]"
                    next_page_marker = f"[Page {page_no + 1}]"

                    start_idx = content.find(page_marker)
                    if start_idx != -1:
                        start_idx += len(page_marker)
                        end_idx = content.find(next_page_marker, start_idx)
                        if end_idx == -1:
                            return content[start_idx:].strip()
                        return content[start_idx:end_idx].strip()
        except Exception:
            continue
    return None


# ─── Page-range maps ────────────────────────────────────────

SIMPLE_PAGE_RANGES: Dict[str, Dict[int, Tuple[int, int]]] = {
    "english": {
        1: (9, 24), 2: (25, 42), 3: (43, 59), 4: (60, 76), 5: (77, 93),
        6: (94, 110), 7: (111, 126), 8: (127, 143), 9: (144, 159),
        10: (160, 178), 11: (179, 197), 12: (198, 212), 13: (213, 231),
        14: (232, 248), 15: (249, 264), 16: (265, 280), 17: (281, 297),
        18: (298, 312),
    },
    "math": {
        1: (5, 29), 2: (30, 50), 3: (51, 69), 4: (70, 83), 5: (84, 133),
        6: (134, 155), 7: (156, 176), 8: (177, 184), 9: (185, 197),
        10: (198, 213), 11: (214, 224), 12: (225, 242), 13: (243, 274),
        14: (275, 297),
    },
    "omaths": {
        1: (5, 17), 2: (18, 29), 3: (30, 39), 4: (40, 54),
        5: (55, 59), 6: (60, 88), 7: (89, 142), 8: (143, 178),
        9: (179, 220), 10: (221, 245), 11: (246, 278), 12: (279, 297),
    },
    "science": {
        1: (5, 19), 2: (20, 64), 3: (65, 78), 4: (79, 116),
        5: (117, 147), 6: (148, 172), 7: (173, 202), 8: (203, 229),
        9: (230, 247), 10: (248, 307), 11: (308, 333), 12: (334, 344),
        13: (345, 368), 14: (369, 386), 15: (387, 400), 16: (401, 420),
        17: (421, 431), 18: (432, 447), 19: (448, 465),
    },
    "social": {
        # Unit 1: We and Our Society
        1: (8, 12), 2: (13, 16), 3: (17, 20), 4: (21, 26),
        # Unit 2: Development and Infrastructure
        5: (28, 30), 6: (31, 35), 7: (36, 40), 8: (41, 44),
        # Unit 3: Social Values and Norms
        9: (46, 52), 10: (53, 57), 11: (58, 61), 12: (62, 66),
        13: (67, 70), 14: (71, 74), 15: (75, 77), 16: (78, 82),
        # Unit 4: Social Problems and Solutions
        17: (84, 89), 18: (90, 92), 19: (93, 94), 20: (95, 97),
        21: (98, 100), 22: (101, 104), 23: (105, 108),
        # Unit 5: Civic Awareness
        24: (110, 114), 25: (115, 118), 26: (119, 123), 27: (124, 128),
        28: (129, 133), 29: (134, 137), 30: (138, 140), 31: (141, 144),
        # Unit 6: Our Earth
        32: (146, 150), 33: (151, 154), 34: (155, 160), 35: (161, 164),
        36: (165, 168), 37: (169, 172), 38: (173, 176), 39: (177, 180),
        40: (181, 184), 41: (185, 188), 42: (189, 192), 43: (193, 196),
        # Unit 7: Our Past
        44: (198, 202), 45: (203, 207), 46: (208, 212), 47: (213, 216),
        48: (217, 219), 49: (220, 224), 50: (225, 228), 51: (229, 233),
        52: (234, 238), 53: (239, 242),
        # Unit 8: Economic Activities
        54: (244, 248), 55: (249, 253), 56: (254, 257), 57: (258, 262),
        58: (263, 267), 59: (268, 271), 60: (272, 275), 61: (276, 280),
        62: (281, 285),
        # Unit 9: International Relations
        63: (287, 290), 64: (291, 294), 65: (295, 299), 66: (300, 304),
        67: (305, 308), 68: (309, 312),
        # Unit 10: Population and Health
        69: (314, 318), 70: (319, 323), 71: (324, 328), 72: (329, 333),
        73: (334, 338), 74: (339, 342),
    },
}

SIMPLE_CHAPTER_TITLES: Dict[str, Dict[int, str]] = {
    "english": {
        1: "Current Affairs and Issues", 2: "Festivals and Celebrations",
        3: "Health and Wellness", 4: "Work and Leisure",
        5: "Science and Experiment", 6: "Food and Cuisine",
        7: "Cyber Security", 8: "Hobbies and Interests",
        9: "History and Culture", 10: "Games and Sports",
        11: "Ethics and Morality", 12: "Nature and Development",
        13: "Population and Migration", 14: "Travel and Adventure",
        15: "People and Places", 16: "Success and Celebration",
        17: "Countries and Towns", 18: "Media and Entertainment",
    },
    "math": {
        1: "Sets", 2: "Compound Interest", 3: "Growth and Depreciation",
        4: "Currency and Exchange Rate", 5: "Area and Volume",
        6: "Sequence and Series", 7: "Quadratic Equation",
        8: "Algebraic Fraction", 9: "Indices",
        10: "Triangles and Quadrilaterals", 11: "Construction",
        12: "Circle", 13: "Statistics", 14: "Probability",
    },
    "omaths": {
        1: "Function", 2: "Polynomial", 3: "Linear Programming",
        4: "Quadratic Equation", 5: "Surd", 6: "Matrix and Determinant",
        7: "Trigonometry", 8: "Coordinate Geometry",
        9: "Transformation", 10: "Vector", 11: "Statistics",
        12: "Continuity",
    },
    "science": {
        1: "Scientific Learning", 2: "Classification of Living Beings",
        3: "Honey Bee", 4: "Heredity",
        5: "Physiological Structure and Life Process",
        6: "Nature and Environment", 7: "Motion and Force",
        8: "Pressure", 9: "Heat", 10: "Wave",
        11: "Electricity and Magnetism", 12: "Universe",
        13: "Information and Communication Technology",
        14: "Classification of Elements", 15: "Chemical Reaction",
        16: "Gases", 17: "Metals and Non-metals",
        18: "Hydrocarbon and its Compounds",
        19: "Chemicals Used in Daily Life",
    },
    "social": {
        # Unit 1
        1: "Socialization", 2: "Our Identity", 3: "Unity in Diversity", 4: "Our National Pride",
        # Unit 2
        5: "Human Development Index", 6: "Sustainable Development", 7: "Federalism in Nepal", 8: "National Pride Projects",
        # Unit 3
        9: "National Heritage", 10: "Folk Songs", 11: "Folk Instruments", 12: "Folk and Classical Dances",
        13: "National Days", 14: "International Personalities", 15: "World Brotherhood and Humanity", 16: "Social Responsibility",
        # Unit 4
        17: "Human Trafficking", 18: "Sexual Misconduct", 19: "Domestic Violence", 20: "Corruption",
        21: "Superstition", 22: "Problem Solving Skills", 23: "Role of International Organizations",
        # Unit 5
        24: "Legislature", 25: "Federal Executive", 26: "Judiciary", 27: "Political Parties",
        28: "Election and Citizens", 29: "Human Rights", 30: "Human Rights Organizations", 31: "Consumer Rights",
        # Unit 6
        32: "Factors Affecting Climate", 33: "Tropical Zone", 34: "Temperate Zone", 35: "Polar Region",
        36: "North America", 37: "South America", 38: "Africa",
        39: "Natural Disasters", 40: "Earthquake", 41: "Map Work", 42: "Modern Map Technology",
        # Unit 7
        43: "Revolution of 2007 BS", 44: "Delhi Agreement", 45: "Democracy and Panchayat", 46: "People's Movement",
        47: "Political Events", 48: "World War I", 49: "World War II", 50: "Global Political Events",
        51: "Historical Thinking", 52: "Historical Sources",
        # Unit 8
        53: "Energy", 54: "Tourism", 55: "Employment", 56: "Foreign Employment",
        57: "Financial Literacy", 58: "Cooperatives", 59: "Insurance", 60: "Revenue and Tax",
        # Unit 9
        61: "Foreign Policy", 62: "United Nations", 63: "UN Agencies", 64: "Globalization",
        65: "Localization", 66: "ICT",
        # Unit 10
        67: "Population", 68: "Population Composition", 69: "Family Planning", 70: "Quality of Life",
        71: "Community Health", 72: "Environment and Health",
    },
}

PDF_FILENAMES = {
    "english": "english.pdf",
    "math": "math.pdf",
    "omaths": "omaths.pdf",
    "science": "science.pdf",
    "social": "social.pdf",
}


# ─── Public API ─────────────────────────────────────────────

def get_pdf_path(subject: str) -> Optional[Path]:
    subject = (subject or "").lower()
    filename = PDF_FILENAMES.get(subject)
    if not filename:
        return None
    base_dir = Path(__file__).resolve().parent.parent
    pdf_path = base_dir / "cdc_curriculum" / "class_10" / filename
    return pdf_path if pdf_path.exists() else None


def get_page_range_for_selection(
    subject: str, unit=None, chapter=None, title: str = ""
) -> Optional[Tuple[int, int]]:
    subject = (subject or "").lower()

    # Social studies: resolve by unit + chapter first
    if subject == "social":
        unit_no = _to_int(unit) if unit else None
        chapter_no = _to_int(chapter) if chapter else None
        # If no explicit params, try parsing from title (e.g. "१.१ हामी...")
        if not unit_no and not chapter_no and title:
            unit_no, chapter_no = _leading_unit_chapter(title)
        if unit_no and chapter_no:
            page_map = _build_social_page_map()
            key = (unit_no, chapter_no)
            if key in page_map:
                return page_map[key]
        # Fall back to title-based keyword lookup
        if title:
            return _infer_page_range_from_title(subject, title)
        return None

    # Non-social: try explicit chapter param first
    if chapter:
        chapter_no = _to_int(chapter)
        if chapter_no and subject in SIMPLE_PAGE_RANGES:
            return SIMPLE_PAGE_RANGES[subject].get(chapter_no)

    # Try parsing from title (e.g. "3. Living Beings...")
    if title:
        unit_no, chapter_no = _leading_unit_chapter(title)
        if chapter_no and subject in SIMPLE_PAGE_RANGES:
            return SIMPLE_PAGE_RANGES[subject].get(chapter_no)
        # Fall back to keyword inference from title text
        return _infer_page_range_from_title(subject, title)

    return None


def get_chapter_text_for_selection(
    subject: str, title: str = "", max_chars: int = 4500
) -> str:
    """Extract textbook text for a chapter identified by its title string.

    This is the primary zero-hallucination path: when the frontend tells us
    the exact chapter title, we resolve it to a page range and return the
    raw PDF text for that range.
    """
    if not PYPDF_AVAILABLE:
        return ""

    page_range = get_page_range_for_selection(subject, title=title)
    if not page_range:
        return ""

    pdf_path = get_pdf_path(subject)
    if not pdf_path:
        return ""

    start_page, end_page = page_range
    text = _extract_pages(pdf_path, start_page, end_page, max_chars=max_chars)
    if not text.strip():
        return ""

    return (
        f"SCANNED PDF CHAPTER CONTEXT ({pdf_path.name}, pages {start_page}-{end_page}):\n"
        f"{text}\n\n"
        "Use this scanned PDF chapter context as the primary source. "
        "The hardcoded curriculum data is only a locator and support outline."
    )


def get_textbook_pages(subject: str, start_page: int, end_page: int) -> list:
    if not PYPDF_AVAILABLE:
        return []
    pdf_path = get_pdf_path(subject)
    if not pdf_path:
        return []

    reader = PdfReader(str(pdf_path))
    pages = []
    for page_no in range(max(1, start_page), min(end_page, len(reader.pages)) + 1):
        text = ""
        cached_text = _get_cached_ocr_page_text(subject, page_no)

        if cached_text:
            text = _clean_text(cached_text)
            text_status = "readable"
            note = ""
        else:
            try:
                text = reader.pages[page_no - 1].extract_text() or ""
            except Exception:
                text = ""
            text = _clean_text(text)
            text_status = "readable"
            note = ""
            if _should_hide_extracted_text(subject, text):
                text_status = "legacy_font"
                note = (
                    "This page uses a legacy/non-Unicode font, so automatic text extraction "
                    "would show corrupted characters. View the PDF image above for the page."
                )
                text = ""
            elif not text:
                text_status = "no_text"
                note = "No selectable text was extracted from this page. View the PDF image."

        pages.append({
            "page": page_no,
            "text": text,
            "text_status": text_status,
            "note": note,
        })
    return pages


def get_chapter_pdf_context(subject: str, message: str, max_chars: int = 4500) -> str:
    if not PYPDF_AVAILABLE:
        return ""

    subject = (subject or "").lower()
    page_range = _find_page_range(subject, message)
    if not page_range:
        return ""

    filename = PDF_FILENAMES.get(subject)
    pdf_path = get_pdf_path(subject)
    if not filename or not pdf_path:
        return ""

    start_page, end_page = page_range
    text = _extract_pages(pdf_path, start_page, end_page, max_chars=max_chars)
    if not text.strip():
        return ""

    return (
        f"SCANNED PDF CHAPTER CONTEXT ({filename}, pages {start_page}-{end_page}):\n"
        f"{text}\n\n"
        "Use this scanned PDF chapter context as the primary source. "
        "The hardcoded curriculum data is only a locator and support outline."
    )


# ─── Internal helpers ───────────────────────────────────────

def _build_social_page_map() -> Dict[Tuple[int, int], Tuple[int, int]]:
    """Build a (unit, chapter) -> (start_page, end_page) map for social studies."""
    mapping = {}
    # Unit 1
    mapping[(1, 1)] = (8, 12)
    mapping[(1, 2)] = (13, 16)
    mapping[(1, 3)] = (17, 20)
    mapping[(1, 4)] = (21, 26)
    # Unit 2
    mapping[(2, 1)] = (28, 30)
    mapping[(2, 2)] = (31, 35)
    mapping[(2, 3)] = (36, 40)
    mapping[(2, 4)] = (41, 44)
    # Unit 3
    mapping[(3, 1)] = (46, 52)
    mapping[(3, 2)] = (53, 57)
    mapping[(3, 3)] = (58, 61)
    mapping[(3, 4)] = (62, 66)
    mapping[(3, 5)] = (67, 70)
    mapping[(3, 6)] = (71, 74)
    mapping[(3, 7)] = (75, 77)
    mapping[(3, 8)] = (78, 82)
    # Unit 4
    mapping[(4, 1)] = (84, 89)
    mapping[(4, 2)] = (90, 92)
    mapping[(4, 3)] = (93, 94)
    mapping[(4, 4)] = (95, 97)
    mapping[(4, 5)] = (98, 100)
    mapping[(4, 6)] = (101, 104)
    mapping[(4, 7)] = (105, 108)
    # Unit 5
    mapping[(5, 1)] = (110, 114)
    mapping[(5, 2)] = (115, 118)
    mapping[(5, 3)] = (119, 123)
    mapping[(5, 4)] = (124, 128)
    mapping[(5, 5)] = (129, 133)
    mapping[(5, 6)] = (134, 137)
    mapping[(5, 7)] = (138, 140)
    mapping[(5, 8)] = (141, 144)
    # Unit 6
    mapping[(6, 1)] = (146, 150)
    mapping[(6, 2)] = (151, 154)
    mapping[(6, 3)] = (155, 160)
    mapping[(6, 4)] = (161, 164)
    mapping[(6, 5)] = (165, 168)
    mapping[(6, 6)] = (169, 172)
    mapping[(6, 7)] = (173, 176)
    mapping[(6, 8)] = (177, 180)
    mapping[(6, 9)] = (181, 184)
    mapping[(6, 10)] = (185, 188)
    mapping[(6, 11)] = (189, 192)
    mapping[(6, 12)] = (193, 196)
    # Unit 7
    mapping[(7, 1)] = (198, 202)
    mapping[(7, 2)] = (203, 207)
    mapping[(7, 3)] = (208, 212)
    mapping[(7, 4)] = (213, 216)
    mapping[(7, 5)] = (217, 219)
    mapping[(7, 6)] = (220, 224)
    mapping[(7, 7)] = (225, 228)
    mapping[(7, 8)] = (229, 233)
    mapping[(7, 9)] = (234, 238)
    mapping[(7, 10)] = (239, 242)
    # Unit 8
    mapping[(8, 1)] = (244, 248)
    mapping[(8, 2)] = (249, 253)
    mapping[(8, 3)] = (254, 257)
    mapping[(8, 4)] = (258, 262)
    mapping[(8, 5)] = (263, 267)
    mapping[(8, 6)] = (268, 271)
    mapping[(8, 7)] = (272, 275)
    mapping[(8, 8)] = (276, 280)
    mapping[(8, 9)] = (281, 285)
    # Unit 9
    mapping[(9, 1)] = (287, 290)
    mapping[(9, 2)] = (291, 294)
    mapping[(9, 3)] = (295, 299)
    mapping[(9, 4)] = (300, 304)
    mapping[(9, 5)] = (305, 308)
    mapping[(9, 6)] = (309, 312)
    # Unit 10
    mapping[(10, 1)] = (314, 318)
    mapping[(10, 2)] = (319, 323)
    mapping[(10, 3)] = (324, 328)
    mapping[(10, 4)] = (329, 333)
    mapping[(10, 5)] = (334, 338)
    mapping[(10, 6)] = (339, 342)
    return mapping


def _find_page_range(subject: str, message: str) -> Optional[Tuple[int, int]]:
    unit, chapter = _unit_chapter_numbers(message)
    chapter_no = chapter

    # For social studies, prefer unit+chapter lookup
    if subject == "social" and unit and chapter:
        page_map = _build_social_page_map()
        key = (unit, chapter)
        if key in page_map:
            return page_map[key]

    if chapter_no and subject in SIMPLE_PAGE_RANGES:
        return SIMPLE_PAGE_RANGES[subject].get(chapter_no)
    return _infer_page_range_from_title(subject, message)


def _unit_chapter_numbers(text: str) -> tuple:
    text = text or ""
    unit = None
    chapter = None
    unit_match = re.search(r"(?:unit)\s*(\d+)", text, re.IGNORECASE)
    chapter_match = re.search(r"(?:chapter|lesson)\s*(\d+)", text, re.IGNORECASE)
    if unit_match:
        unit = _to_int(unit_match.group(1))
    if chapter_match:
        chapter = _to_int(chapter_match.group(1))

    # Fallback: parse leading numerals from title (e.g. "3. Living Beings...", "१.१ हामी...")
    if not unit and not chapter:
        unit, chapter = _leading_unit_chapter(text)

    return unit, chapter


def _infer_page_range_from_title(subject: str, message: str) -> Optional[Tuple[int, int]]:
    text = (message or "").lower()
    if subject == "social":
        # Try matching against known social chapter titles
        social_titles = {
            "socialization": 1, "our identity": 2, "unity in diversity": 3, "our national pride": 4,
            "human development index": 5, "sustainable development": 6, "federalism in nepal": 7,
            "national pride projects": 8, "national heritage": 9, "folk songs": 10,
            "folk instruments": 11, "folk and classical dances": 12, "national days": 13,
            "international personalities": 14, "world brotherhood": 15, "social responsibility": 16,
            "human trafficking": 17, "sexual misconduct": 18, "domestic violence": 19,
            "corruption": 20, "superstition": 21, "problem solving": 22,
            "international organizations": 23, "legislature": 24, "federal executive": 25,
            "judiciary": 26, "political parties": 27, "election": 28, "human rights": 29,
            "consumer rights": 31, "climate": 32, "tropical zone": 33, "temperate zone": 34,
            "polar region": 35, "north america": 36, "south america": 37, "africa": 38,
            "natural disaster": 39, "earthquake": 40, "map work": 41, "modern map": 42,
            "revolution of 2007": 43, "delhi agreement": 44, "democracy and panchayat": 45,
            "people's movement": 46, "political events": 47, "world war i": 48,
            "world war ii": 49, "global political": 50, "historical thinking": 51,
            "historical sources": 52, "energy": 53, "tourism": 54, "employment": 55,
            "financial literacy": 57, "cooperatives": 58, "insurance": 59,
            "revenue": 60, "foreign policy": 61, "united nations": 62,
            "globalization": 64, "localization": 65, "ict": 66,
            "population": 67, "family planning": 69, "community health": 71,
        }
        for keyword, chapter_no in social_titles.items():
            if keyword in text:
                return SIMPLE_PAGE_RANGES.get("social", {}).get(chapter_no)

    if subject in SIMPLE_CHAPTER_TITLES:
        for chapter_no, title in SIMPLE_CHAPTER_TITLES[subject].items():
            if _topic_matches(text, [title]):
                return SIMPLE_PAGE_RANGES[subject].get(chapter_no)

    return None


def _topic_matches(text: str, topics) -> bool:
    for topic in topics:
        topic_lower = (topic or "").lower()
        if topic_lower and topic_lower in text:
            return True
    return False


def _to_int(value: str) -> Optional[int]:
    digits = re.sub(r"\D", "", value or "")
    return int(digits) if digits else None


def _extract_pages(pdf_path: Path, start_page: int, end_page: int, max_chars: int) -> str:
    subject = pdf_path.stem.lower()
    reader = PdfReader(str(pdf_path))
    parts = []
    running_len = 0
    sep_len = 2  # "\n\n"
    for page_no in range(start_page, min(end_page, len(reader.pages)) + 1):
        cached_text = _get_cached_ocr_page_text(subject, page_no)
        if cached_text:
            text = _clean_text(cached_text)
        else:
            try:
                text = reader.pages[page_no - 1].extract_text() or ""
            except Exception:
                text = ""
            text = _clean_text(text)

        if not text:
            continue

        part = f"[Page {page_no}]\n{text}"
        part_len = len(part) + (sep_len if parts else 0)
        if running_len + part_len > max_chars:
            break
        parts.append(part)
        running_len += part_len
    return "\n\n".join(parts)


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[\x01-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _should_hide_extracted_text(subject: str, text: str) -> bool:
    return False
