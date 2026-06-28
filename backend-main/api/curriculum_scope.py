import re
from typing import Dict, Iterable, List, Optional


OUT_OF_SCOPE_RESPONSE = (
    "This question is not related to the Grade 10 curriculum that I am "
    "designed to teach. Please ask a question from the CDC Grade 10 subjects such "
    "as Mathematics, Optional Mathematics, Science, Social Studies, or English."
)


SUBJECT_ALIASES = {
    "math": {"math", "mathematics"},
    "omaths": {"omaths", "optional mathematics", "optional math"},
    "science": {"science", "science and technology"},
    "english": {"english"},
    "social": {
        "social",
        "social studies",
        "samajik adhyayan",
        "सामाजिक अध्ययन",
        "samaajik",
        "social science",
        "samajik",
    },
}


CURRICULUM_TOPICS: Dict[str, List[str]] = {
    "math": [
        "sets", "cardinality", "venn diagram", "compound interest", "growth",
        "depreciation", "currency", "exchange rate", "area", "volume",
        "sequence", "series", "quadratic equation", "algebraic fraction",
        "indices", "triangles", "quadrilaterals", "construction", "circle",
        "statistics", "probability",
    ],
    "omaths": [
        "function", "composite function", "inverse function", "polynomial",
        "remainder theorem", "factor theorem", "linear programming",
        "quadratic equation", "surd", "matrix", "determinant", "trigonometry",
        "coordinate geometry", "transformation", "vector", "statistics",
        "continuity",
    ],
    "science": [
        "scientific learning", "classification of living beings", "honey bee",
        "heredity", "physiological structure", "life process", "nature",
        "environment", "motion", "force", "pressure", "heat", "wave",
        "electricity", "magnetism", "universe", "information technology",
        "communication technology", "classification of elements",
        "chemical reaction", "gases", "metal", "non metal", "hydrocarbon",
        "chemicals used in daily life", "cell", "organ", "system",
        "photosynthesis", "respiration", "blood", "heart", "reproduction",
        "ecosystem", "pollution", "climate change", "gravity", "newton",
        "acceleration", "current", "voltage", "resistance", "ohm",
        "classification", "living beings", "taxonomy", "taxonomic",
        "kingdom", "monera", "protista", "fungi", "plantae", "animalia",
        "virus", "bacteria", "protozoa", "algae", "key characteristics of algae",
        "mushroom", "fern", "gymnosperm", "angiosperm", "dicot", "monocot",
        "phylum", "phyla", "subphylum", "sub phylum", "sub phylums",
        "sub phyla", "chordata", "subphyla of chordata", "protochordata",
        "urochordata", "cephalochordata", "vertebrata", "vertebrate",
        "invertebrate", "porifera", "coelenterata", "cnidaria",
        "platyhelminthes", "aschelminthes", "annelida", "arthropoda",
        "mollusca", "echinodermata", "pisces", "amphibia", "reptilia",
        "aves", "mammalia",
    ],
    "english": [
        "current affairs", "driverless cars", "open letter", "reported speech",
        "newspaper article", "festivals", "celebrations", "thanksgiving",
        "essay", "news story", "health", "wellness", "healthy diet",
        "imperatives", "email", "speech", "work", "leisure", "modal verbs",
        "job application", "science experiment", "conditional sentences",
        "instructions", "letter of complaint", "food", "cuisine",
        "connectives", "present continuous", "recipe", "cyber security",
        "internet safety", "articles", "hobbies", "active voice",
        "passive voice", "history", "culture", "past tense", "games",
        "sports", "present perfect", "ethics", "morality", "negation",
        "subject verb agreement", "nature", "development", "future tense",
        "report", "notice", "population", "migration", "charts",
        "travelogue", "question tag", "relative clause", "preposition",
        "biography", "prepositional phrase", "adjectives", "adverbs",
        "film review", "causative verbs",
    ],
    "social": [
        "socialization", "our identity", "unity in diversity", "national pride",
        "human development index", "sustainable development", "federalism",
        "national pride projects", "national heritage", "folk songs",
        "folk instruments", "folk dances", "classical dances", "national days",
        "international personalities", "world brotherhood", "humanity",
        "social responsibility", "human trafficking", "sexual misconduct",
        "domestic violence", "corruption", "superstition", "problem solving",
        "international organizations", "legislature", "federal executive",
        "judiciary", "political parties", "election", "citizens",
        "human rights", "consumer rights", "climate", "tropical zone",
        "temperate zone", "polar region", "north america", "south america",
        "africa", "natural disasters", "earthquake", "map work",
        "modern map technology", "revolution of 2007", "delhi agreement",
        "democracy", "panchayat", "people's movement", "political events",
        "world war", "global political events", "historical thinking",
        "historical sources", "energy", "tourism", "employment",
        "foreign employment", "financial literacy", "cooperatives", "insurance",
        "revenue", "tax", "foreign policy", "united nations", "un agencies",
        "globalization", "localization", "ict", "population",
        "population composition", "family planning", "quality of life",
        "community health", "environment and health",
    ],
}


ACADEMIC_TERMS = {
    "define", "definition", "explain", "summary", "summarize", "difference",
    "compare", "example", "examples", "formula", "solve", "find", "prove",
    "derive", "calculate", "question", "answer", "exercise", "unit", "lesson",
    "chapter", "grammar", "writing", "reading",
    "what", "why", "how", "when", "where", "who", "characteristics", "features", 
    "types", "function", "importance", "uses", "describe", "list", "notes", "revise"
}

MATH_SIGNAL_RE = re.compile(r"[\d=+\-*/^√()]|\frac|\sqrt|x\^|y\^")
LESSON_SIGNAL_RE = re.compile(r"(unit|lesson|chapter)\s*(\d+)", re.IGNORECASE)


def normalize_subject(subject: Optional[str]) -> str:
    value = (subject or "").strip().lower()
    for canonical, aliases in SUBJECT_ALIASES.items():
        if value in aliases:
            return canonical
    return value


def _tokens(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _topic_matches(text: str, topics: Iterable[str]) -> List[str]:
    lowered = text.lower()
    token_set = _tokens(lowered)
    matches = []
    for topic in topics:
        topic_lower = topic.lower()
        topic_tokens = _tokens(topic_lower)
        if topic_lower in lowered or (topic_tokens and topic_tokens <= token_set):
            matches.append(topic)
    return matches


def infer_subject(message: str, selected_subject: Optional[str] = None) -> str:
    selected = normalize_subject(selected_subject)
    if selected in CURRICULUM_TOPICS:
        return selected

    text = message.lower()
    for subject, aliases in SUBJECT_ALIASES.items():
        if any(alias in text for alias in aliases):
            return subject

    scored = [
        (subject, len(_topic_matches(text, topics)))
        for subject, topics in CURRICULUM_TOPICS.items()
    ]
    subject, score = max(scored, key=lambda item: item[1])
    return subject if score > 0 else ""


def get_scope_summary(subject: Optional[str] = None) -> str:
    selected = normalize_subject(subject)
    subjects = [selected] if selected in CURRICULUM_TOPICS else list(CURRICULUM_TOPICS.keys())
    lines = []
    for key in subjects:
        title = {
            "math": "Mathematics",
            "omaths": "Optional Mathematics",
            "science": "Science and Technology",
            "english": "English",
            "social": "Social Studies",
        }.get(key, key.title())
        lines.append(f"{title}: {', '.join(CURRICULUM_TOPICS[key])}")
    return "\n".join(lines)


def find_curriculum_focus(message: str, subject: Optional[str] = None) -> Optional[str]:
    return None


def response_language_for_subject(subject: Optional[str] = None) -> str:
    return "english"


def out_of_scope_response_for_subject(subject: Optional[str] = None) -> str:
    return OUT_OF_SCOPE_RESPONSE


def is_curriculum_query(message: str, subject: Optional[str] = None) -> bool:
    text = (message or "").strip().lower()
    if not text:
        return False

    selected = infer_subject(text, subject)
    if not selected:
        return False

    # Softened CDC Safeguard: Trust the LLM to handle out-of-scope queries
    # by guiding the student back gracefully, instead of hard-rejecting here.
    return True
