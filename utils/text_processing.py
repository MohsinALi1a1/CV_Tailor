"""
CV Tailor — Text Processing Utilities
=======================================
NLP helpers for keyword extraction, text cleaning, and resume parsing.
Uses spaCy for NLP; falls back to regex/NLTK when spaCy is unavailable.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

# ── Optional spaCy import ────────────────────────────────────
try:
    import spacy

    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        logger.info("Downloading spaCy model 'en_core_web_sm'…")
        from spacy.cli import download as spacy_download

        spacy_download("en_core_web_sm")
        nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except ImportError:
    nlp = None
    SPACY_AVAILABLE = False
    logger.warning("spaCy not available – falling back to regex keyword extraction.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Keyword Extraction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def extract_keywords(text: str, top_n: int = 30) -> list[str]:
    """Extract the most relevant keywords / noun phrases from text.

    Uses a hybrid approach:
      1. Known tech terms / skills (high-value exact matches)
      2. spaCy noun chunks (filtered for quality)
      3. Regex fallback for individual terms

    Args:
        text: Input text (job description or resume).
        top_n: Number of keywords to return.

    Returns:
        List of keywords sorted by frequency (descending).
    """
    text_lower = text.lower()
    keywords: list[str] = []

    # 1. Extract known tech/skill terms first (highest quality)
    known = _extract_known_terms(text_lower)
    keywords.extend(known)

    # 2. spaCy extraction (filtered)
    if SPACY_AVAILABLE and nlp is not None:
        spacy_kws = _extract_keywords_spacy(text, top_n * 2)
        keywords.extend(spacy_kws)
    else:
        regex_kws = _extract_keywords_regex(text, top_n * 2)
        keywords.extend(regex_kws)

    # 3. Also extract individual meaningful words (2+ chars, not stopwords)
    words = re.findall(r'\b[a-zA-Z][a-zA-Z+#.\-]{1,30}\b', text_lower)
    stopwords = _get_basic_stopwords()
    for w in words:
        if w not in stopwords and len(w) > 2:
            keywords.append(w)

    # Deduplicate while preserving order by frequency
    counter = Counter(keywords)
    seen: set[str] = set()
    result: list[str] = []
    for kw, _ in counter.most_common(top_n * 3):
        kw_clean = kw.strip()
        if kw_clean and kw_clean not in seen and len(kw_clean) > 1:
            # Skip ultra-generic terms
            if kw_clean in {'good', 'well', 'new', 'high', 'low', 'make', 'use',
                           'time', 'year', 'day', 'way', 'part', 'long', 'first',
                           'last', 'great', 'little', 'right', 'old', 'big', 'look',
                           'work', 'team', 'company', 'join', 'position', 'must',
                           'candidate', 'will', 'working', 'required', 'preferred',
                           'looking', 'ideal', 'based', 'best', 'strong', 'ability',
                           'job', 'role', 'need', 'needs', 'experience', 'minimum',
                           'years', 'plus', 'etc', 'related', 'relevant', 'including'}:
                continue
            seen.add(kw_clean)
            result.append(kw_clean)
            if len(result) >= top_n:
                break
    return result


# ── Known tech/skill term extraction ──────────────────────────

_KNOWN_TECH_TERMS = {
    # Programming languages
    "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "go",
    "golang", "rust", "swift", "kotlin", "scala", "php", "perl", "r",
    "matlab", "dart", "lua", "haskell", "elixir", "clojure", "groovy",
    "objective-c", "assembly", "cobol", "fortran", "julia", "zig",
    # Web frameworks
    "react", "angular", "vue", "vue.js", "next.js", "nextjs", "nuxt",
    "django", "flask", "fastapi", "express", "express.js", "spring",
    "spring boot", "rails", "ruby on rails", "laravel", "asp.net", ".net",
    "node.js", "nodejs", "svelte", "gatsby", "remix", "astro", "htmx",
    "solid.js", "qwik", "deno", "bun", "hono", "elysia",
    # Data / ML / AI (expanded 2024-2026)
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "tensorflow", "pytorch", "keras", "scikit-learn",
    "pandas", "numpy", "scipy", "matplotlib", "jupyter", "spark",
    "hadoop", "data science", "data analysis", "data engineering",
    "data pipeline", "etl", "data warehouse", "big data", "ai",
    "artificial intelligence", "llm", "gpt", "neural network",
    "generative ai", "langchain", "llamaindex", "hugging face",
    "transformers", "rag", "retrieval augmented generation",
    "fine-tuning", "prompt engineering", "mlops", "mlflow",
    "feature engineering", "a/b testing", "statistical analysis",
    "reinforcement learning", "time series", "recommendation systems",
    "openai", "anthropic", "claude", "chatgpt", "copilot",
    "stable diffusion", "midjourney", "vector database", "pinecone",
    "weaviate", "chromadb", "embeddings", "semantic search",
    "data visualization", "power bi", "tableau", "looker", "dbt",
    "airflow", "apache airflow", "kafka", "apache kafka", "flink",
    "snowflake", "databricks", "redshift", "bigquery",
    # Cloud / DevOps (expanded)
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
    "terraform", "ansible", "jenkins", "ci/cd", "github actions",
    "circleci", "gitlab", "devops", "microservices", "serverless",
    "lambda", "ec2", "s3", "cloudformation", "helm", "istio",
    "argo", "argocd", "pulumi", "crossplane", "opentofu",
    "prometheus", "grafana", "datadog", "new relic", "splunk",
    "elastic", "elk stack", "observability", "sre",
    "site reliability", "infrastructure as code", "iac",
    "cloud native", "service mesh", "api gateway",
    "load balancing", "auto scaling", "high availability",
    "disaster recovery", "blue-green deployment", "canary deployment",
    # Databases (expanded)
    "sql", "mysql", "postgresql", "postgres", "mongodb", "redis",
    "elasticsearch", "dynamodb", "cassandra", "oracle", "sqlite",
    "neo4j", "graphql", "nosql", "firebase", "supabase",
    "cockroachdb", "planetscale", "timescaledb", "clickhouse",
    "mariadb", "couchdb", "influxdb", "druid",
    # Tools & practices
    "git", "github", "jira", "agile", "scrum", "kanban", "rest",
    "restful", "api", "apis", "graphql", "grpc", "oauth", "jwt",
    "linux", "unix", "bash", "powershell", "testing", "unit testing",
    "tdd", "bdd", "selenium", "cypress", "jest", "pytest",
    "playwright", "vitest", "mocha", "chai",
    "confluence", "slack", "notion", "asana", "trello",
    "postman", "swagger", "openapi", "api design",
    # Soft skills / business
    "leadership", "communication", "project management", "stakeholder",
    "cross-functional", "mentoring", "problem solving", "analytical",
    "strategic", "budgeting", "planning", "negotiation",
    "team management", "decision making", "critical thinking",
    "presentation", "collaboration", "time management",
    "conflict resolution", "emotional intelligence",
    # Other tech
    "html", "css", "sass", "webpack", "vite", "tailwind", "bootstrap",
    "figma", "sketch", "adobe", "photoshop", "illustrator",
    "tableau", "power bi", "excel", "sap", "salesforce",
    "blockchain", "web3", "solidity", "crypto",
    "ios", "android", "mobile", "react native", "flutter",
    "security", "cybersecurity", "encryption", "compliance",
    "networking", "tcp/ip", "dns", "http", "https",
    "oauth 2.0", "saml", "sso", "single sign-on",
    "owasp", "penetration testing", "vulnerability assessment",
    # Project management & methodologies
    "pmp", "prince2", "six sigma", "lean", "waterfall",
    "safe", "scaled agile", "okr", "kpi",
    # Design & UX
    "ui/ux", "user experience", "user interface", "wireframing",
    "prototyping", "usability testing", "design thinking",
    "accessibility", "wcag", "responsive design",
    # Finance / Business
    "financial modeling", "forecasting", "roi", "p&l",
    "business intelligence", "crm", "erp",
}


# ── Skill synonym / abbreviation mapping ──────────────────────
# Maps common abbreviations and variations to their canonical forms.
# This enables matching "JS" in a resume to "javascript" in a JD.
_SKILL_SYNONYMS: dict[str, set[str]] = {
    "javascript": {"js", "java script", "ecmascript", "es6", "es2015"},
    "typescript": {"ts"},
    "python": {"py", "python3", "python 3"},
    "kubernetes": {"k8s", "kube"},
    "docker": {"containerization", "containers"},
    "react": {"reactjs", "react.js"},
    "angular": {"angularjs", "angular.js"},
    "vue": {"vuejs", "vue.js"},
    "node.js": {"nodejs", "node"},
    "next.js": {"nextjs", "next"},
    "postgresql": {"postgres", "psql"},
    "mongodb": {"mongo"},
    "elasticsearch": {"elastic", "es"},
    "amazon web services": {"aws"},
    "google cloud platform": {"gcp", "google cloud"},
    "microsoft azure": {"azure"},
    "machine learning": {"ml"},
    "deep learning": {"dl"},
    "artificial intelligence": {"ai"},
    "natural language processing": {"nlp"},
    "computer vision": {"cv"},
    "continuous integration": {"ci", "ci/cd", "cicd"},
    "continuous deployment": {"cd", "ci/cd", "cicd"},
    "ci/cd": {"cicd", "continuous integration", "continuous deployment"},
    "rest": {"restful", "rest api", "restful api"},
    "graphql": {"graph ql"},
    "sql": {"structured query language"},
    "nosql": {"no-sql"},
    "html": {"html5"},
    "css": {"css3"},
    "c++": {"cpp", "cplusplus"},
    "c#": {"csharp", "c sharp"},
    "objective-c": {"objc", "obj-c"},
    ".net": {"dotnet", "dot net"},
    "scikit-learn": {"sklearn"},
    "infrastructure as code": {"iac"},
    "site reliability engineering": {"sre"},
    "user experience": {"ux"},
    "user interface": {"ui"},
    "ui/ux": {"ux/ui", "ui ux", "ux ui"},
    "project management": {"pm"},
    "agile": {"agile methodology", "agile methodologies"},
    "scrum": {"scrum master", "scrum methodology"},
    "test driven development": {"tdd"},
    "behavior driven development": {"bdd"},
    "single sign-on": {"sso"},
    "application programming interface": {"api"},
    "software development life cycle": {"sdlc"},
    "object oriented programming": {"oop"},
    "software as a service": {"saas"},
    "platform as a service": {"paas"},
    "infrastructure as a service": {"iaas"},
    "extract transform load": {"etl"},
    "retrieval augmented generation": {"rag"},
    "large language model": {"llm", "llms"},
}


def _extract_known_terms(text_lower: str) -> list[str]:
    """Extract known tech terms that appear in text."""
    found: list[str] = []
    # Check multi-word terms first (longer matches take priority)
    multi_word = sorted(
        [t for t in _KNOWN_TECH_TERMS if ' ' in t or '.' in t or '/' in t],
        key=len, reverse=True
    )
    for term in multi_word:
        if term in text_lower:
            found.append(term)
    # Then single-word terms
    text_words = set(re.findall(r'\b[a-z][a-z+#.\-]{0,30}\b', text_lower))
    for term in _KNOWN_TECH_TERMS:
        if ' ' not in term and '.' not in term and '/' not in term:
            if term in text_words:
                found.append(term)
    return found


def _extract_keywords_spacy(text: str, top_n: int) -> list[str]:
    """SpaCy-based keyword extraction using noun chunks and named entities."""
    doc = nlp(text.lower())

    keywords: list[str] = []

    # Noun chunks
    for chunk in doc.noun_chunks:
        clean = chunk.text.strip()
        if len(clean) > 2 and not _is_stopword(clean):
            keywords.append(clean)

    # Named entities
    for ent in doc.ents:
        if ent.label_ in ("ORG", "PRODUCT", "SKILL", "GPE", "WORK_OF_ART"):
            keywords.append(ent.text.strip().lower())

    # Individual nouns / proper nouns
    for token in doc:
        if token.pos_ in ("NOUN", "PROPN") and not token.is_stop and len(token.text) > 2:
            keywords.append(token.lemma_)

    counter = Counter(keywords)
    return [kw for kw, _ in counter.most_common(top_n)]


def _extract_keywords_regex(text: str, top_n: int) -> list[str]:
    """Fallback regex-based keyword extraction."""
    # Simple tokenisation — keep multi-word technical terms
    words = re.findall(r"\b[a-zA-Z][a-zA-Z+#.\-]{1,30}\b", text.lower())
    stopwords = _get_basic_stopwords()
    filtered = [w for w in words if w not in stopwords and len(w) > 2]
    counter = Counter(filtered)
    return [kw for kw, _ in counter.most_common(top_n)]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Keyword Matching
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def match_keywords(
    resume_keywords: list[str],
    job_keywords: list[str],
) -> dict[str, Any]:
    """Compare resume keywords against job description keywords.

    Uses smart matching:
      - Exact match
      - Substring containment (e.g. "python" matches "python development")
      - Word-overlap for multi-word phrases
      - Case-insensitive

    Returns:
        Dict with matched, missing, match_rate (0–100).
    """
    if not job_keywords:
        return {"matched": [], "missing": [], "match_rate": 100.0}

    # Build a single lowercased blob from resume keywords + original text will
    # be handled at call-site; here we work purely with keyword lists.
    resume_lower = {kw.lower().strip() for kw in resume_keywords if kw.strip()}
    job_lower = {kw.lower().strip() for kw in job_keywords if kw.strip()}

    # Build a flat text from all resume keywords for substring search
    resume_blob = " | ".join(resume_lower)

    matched: set[str] = set()
    missing: set[str] = set()

    for jk in job_lower:
        if _keyword_matches(jk, resume_lower, resume_blob):
            matched.add(jk)
        else:
            missing.add(jk)

    total = len(job_lower) if job_lower else 1
    return {
        "matched": sorted(matched),
        "missing": sorted(missing),
        "match_rate": round((len(matched) / total) * 100, 1),
    }


def _keyword_matches(job_kw: str, resume_set: set[str], resume_blob: str) -> bool:
    """Check if a job keyword is present in the resume using smart matching.

    Includes synonym/abbreviation matching for higher accuracy.
    """
    # 1. Exact match
    if job_kw in resume_set:
        return True

    # 2. Job keyword appears as substring in any resume keyword
    for rk in resume_set:
        if job_kw in rk or rk in job_kw:
            return True

    # 3. Check if job keyword appears in the blob (handles "python" in "python developer")
    if job_kw in resume_blob:
        return True

    # 4. Word-overlap for multi-word phrases: "data analysis" matches "data" + "analysis"
    jk_words = set(job_kw.split())
    if len(jk_words) > 1:
        # If all significant words of the job keyword appear in resume keywords
        matched_words = sum(1 for w in jk_words if len(w) > 2 and w in resume_blob)
        if matched_words >= len([w for w in jk_words if len(w) > 2]):
            return True

    # 5. Single-word job keyword: check if it appears as a word in any resume keyword
    if len(jk_words) == 1 and len(job_kw) > 2:
        for rk in resume_set:
            rk_words = set(rk.split())
            if job_kw in rk_words:
                return True

    # 6. Synonym / abbreviation matching
    synonyms_to_check = _SKILL_SYNONYMS.get(job_kw, set())
    # Also check reverse (if job_kw is an abbreviation)
    for canonical, syns in _SKILL_SYNONYMS.items():
        if job_kw in syns:
            synonyms_to_check = synonyms_to_check | {canonical}
    for syn in synonyms_to_check:
        if syn in resume_set or syn in resume_blob:
            return True

    # 7. Plural/singular fallback
    if job_kw.endswith('s') and job_kw[:-1] in resume_blob:
        return True
    if job_kw + 's' in resume_blob:
        return True

    return False


def match_keywords_against_text(
    text: str,
    job_keywords: list[str],
) -> dict[str, Any]:
    """Match job keywords directly against full resume text (more accurate).

    This checks if each job keyword literally appears in the resume text,
    giving much more reliable results than keyword-list-vs-keyword-list matching.
    Also checks skill synonyms/abbreviations for smarter matching.
    """
    if not job_keywords:
        return {"matched": [], "missing": [], "match_rate": 100.0}

    text_lower = text.lower()
    # Also build a word set for single-word matching
    text_words = set(re.findall(r'\b[a-z][a-z+#.\-]{0,30}\b', text_lower))

    # Build reverse synonym map: abbreviation -> canonical forms
    _reverse_synonyms: dict[str, set[str]] = {}
    for canonical, syns in _SKILL_SYNONYMS.items():
        for syn in syns:
            _reverse_synonyms.setdefault(syn, set()).add(canonical)
        _reverse_synonyms.setdefault(canonical, set()).update(syns)

    matched: list[str] = []
    missing: list[str] = []

    for kw in job_keywords:
        kw_clean = kw.lower().strip()
        if not kw_clean:
            continue

        found = False

        # 1. Direct substring
        if kw_clean in text_lower:
            found = True
        # 2. Single word check in word set
        elif kw_clean in text_words:
            found = True
        # 3. Multi-word: check all significant words present
        elif len(kw_clean.split()) > 1:
            kw_parts = [w for w in kw_clean.split() if len(w) > 2]
            if kw_parts and all(w in text_lower for w in kw_parts):
                found = True

        # 4. Synonym / abbreviation matching
        if not found:
            # Check if kw has synonyms that appear in the text
            synonyms_to_check = _reverse_synonyms.get(kw_clean, set())
            # Also check if kw IS a canonical form with known synonyms
            if kw_clean in _SKILL_SYNONYMS:
                synonyms_to_check = synonyms_to_check | _SKILL_SYNONYMS[kw_clean]
            for syn in synonyms_to_check:
                if syn in text_lower or syn in text_words:
                    found = True
                    break

        # 5. Plural/singular matching: "apis" -> "api", "microservices" -> "microservice"
        if not found:
            if kw_clean.endswith('s') and kw_clean[:-1] in text_lower:
                found = True
            elif kw_clean + 's' in text_lower:
                found = True

        if found:
            matched.append(kw_clean)
        else:
            missing.append(kw_clean)

    total = len(job_keywords) if job_keywords else 1
    return {
        "matched": sorted(set(matched)),
        "missing": sorted(set(missing)),
        "match_rate": round((len(set(matched)) / total) * 100, 1),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Text Cleaning & Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def clean_text(text: str) -> str:
    """Normalise whitespace and strip junk characters."""
    text = re.sub(r"[^\S\n]+", " ", text)  # collapse horizontal whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)  # max 2 consecutive newlines
    return text.strip()


def count_words(text: str) -> int:
    """Return the word count of a text string."""
    return len(text.split())


def bullet_to_list(text: str) -> list[str]:
    """Parse a block of bulleted text into a list of strings."""
    lines = text.strip().splitlines()
    bullets: list[str] = []
    for line in lines:
        # Strip leading whitespace, bullet markers (•-*►▸▹‣⁃●➢➤→↗■□◆▪︎☐), and numbered prefixes
        cleaned = re.sub(r"^[\s•\-\*►▸▹‣⁃●➢➤→↗■□◆▪︎☐]+", "", line).strip()
        # Also handle numbered bullets like "1." or "1)"
        cleaned = re.sub(r"^\d+[.)\]]\s*", "", cleaned).strip()
        if cleaned and len(cleaned) > 3:
            bullets.append(cleaned)
    return bullets


def list_to_bullet(items: list[str], marker: str = "•") -> str:
    """Join a list of strings into a bulleted text block."""
    return "\n".join(f"{marker} {item}" for item in items)


def calculate_keyword_density(text: str, keywords: list[str]) -> dict[str, float]:
    """Calculate keyword density (%) in text.

    Returns:
        Dict mapping each keyword to its density percentage.
    """
    words = text.lower().split()
    total = len(words) if words else 1
    density: dict[str, float] = {}
    for kw in keywords:
        count = text.lower().count(kw.lower())
        density[kw] = round((count / total) * 100, 2)
    return density


def has_quantified_achievement(bullet: str) -> bool:
    """Check if a bullet point contains a quantified achievement.

    Detects: percentages, dollar/currency amounts, numbers with context,
    K/M/B notation, ordinals, time units, multipliers, and more.
    """
    return bool(re.search(
        r"\d+[%$+]|\$\d|#?\d+\s*(million|billion|thousand|%|x\b)"
        r"|\b\d{2,}\b"
        r"|\b\d+[KkMmBb]\+?\b"
        r"|\b\d+\.\d+"
        r"|\b\d+\s*(weeks?|days?|months?|hours?|minutes?|seconds?|years?|clients?|users?|customers?|teams?|members?|engineers?|developers?|projects?|features?|endpoints?|requests?|transactions?)\b"
        r"|\b[£€¥₹]\s*\d"
        r"|\b\d+\s*[-–]\s*\d+\s*%"
        r"|\b(\d+(?:st|nd|rd|th))\b"
        r"|(\d+x|\d+X)\s"
        r"|top\s*\d+"
        r"|\b\d+\+\b"
        r"|\b\d+/\d+\b",
        bullet,
        re.IGNORECASE,
    ))


def starts_with_action_verb(bullet: str) -> bool:
    """Check if a bullet starts with an action verb (heuristic)."""
    from config import ATS_ACTION_VERBS

    words = bullet.strip().split()
    if not words:
        return False
    first_word = words[0].lower().rstrip(".,;:")
    # Direct match
    if first_word in ATS_ACTION_VERBS:
        return True
    # Try stemmed forms: remove common suffixes (-ed, -ing, -s, -es, -tion)
    stems = {first_word}
    if first_word.endswith("ed"):
        stems.add(first_word[:-2])  # developed -> develop
        stems.add(first_word[:-1])  # managed -> manag -> manage via next
        if first_word.endswith("ied"):
            stems.add(first_word[:-3] + "y")  # identified -> identify
    if first_word.endswith("ing"):
        stems.add(first_word[:-3])  # building -> build
        stems.add(first_word[:-3] + "e")  # managing -> manage
    if first_word.endswith("s") and not first_word.endswith("ss"):
        stems.add(first_word[:-1])  # leads -> lead
    if first_word.endswith("es"):
        stems.add(first_word[:-2])  # manages -> manag -> handled below
    return bool(stems & set(ATS_ACTION_VERBS))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Resume Text → Dict Parser (simple heuristic)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION_PATTERN = re.compile(
    r"^\s*"
    r"(?:=+|-+|_+)?\s*"
    r"(summary|professional\s+summary|career\s+summary|executive\s+summary|profile|objective|career\s+objective"
    r"|experience|work\s+experience|professional\s+experience|employment(?:\s+history)?"
    r"|education|academic(?:\s+background)?"
    r"|skills|technical\s+skills|core\s+competencies|competencies|areas?\s+of\s+expertise|key\s+skills"
    r"|certifications?|licenses?(?:\s+(?:and|&)\s+certifications?)?"
    r"|projects|personal\s+projects|key\s+projects|academic\s+projects"
    r"|languages|technical\s+proficiency"
    r"|volunteer(?:\s+experience)?|community\s+(?:service|involvement)"
    r"|awards(?:\s+(?:and|&)\s+honors)?|achievements|honors"
    r"|publications|research"
    r"|interests|hobbies"
    r"|references"
    r"|training(?:\s+(?:and|&)\s+development)?"
    r"|additional\s+information|other)"
    r"\s*[:.]?\s*"
    r"(?:=+|-+|_+)?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def parse_resume_sections(text: str) -> dict[str, str]:
    """Parse plain-text resume into sections by heading.

    Returns:
        Dict mapping section name → section body.
    """
    matches = list(SECTION_PATTERN.finditer(text))
    if not matches:
        return {"Full Resume": text}

    sections: dict[str, str] = {}
    for i, match in enumerate(matches):
        heading = match.group(0).strip().title()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections[heading] = body

    return sections


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Stopwords fallback
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _is_stopword(text: str) -> bool:
    return text.lower() in _get_basic_stopwords()


def _get_basic_stopwords() -> set[str]:
    return {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "shall", "can", "need",
        "dare", "ought", "used", "it", "its", "it's", "this", "that", "these",
        "those", "i", "me", "my", "mine", "we", "us", "our", "ours", "you",
        "your", "yours", "he", "him", "his", "she", "her", "hers", "they",
        "them", "their", "theirs", "what", "which", "who", "whom", "when",
        "where", "why", "how", "all", "each", "every", "both", "few", "more",
        "most", "other", "some", "such", "no", "nor", "not", "only", "own",
        "same", "so", "than", "too", "very", "just", "about", "above", "after",
        "again", "between", "into", "through", "during", "before", "below",
        "up", "down", "out", "off", "over", "under", "further", "then", "once",
        "here", "there", "any", "also", "etc", "able", "using", "including",
        "role", "responsibilities", "required", "preferred", "minimum",
        "candidate", "must", "strong", "ideal", "looking", "join", "team",
        "company", "position", "opportunity", "plus", "years", "experience",
        "based", "related", "relevant", "work", "working", "day", "full",
        "time", "part", "apply", "description", "qualified", "equal",
        "employer", "benefit", "salary", "please", "submit", "resume",
    }
