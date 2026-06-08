"""
File Parsers — extract text from PDF, DOCX, TXT, and JSON resume files,
and intelligently convert plain text resumes into structured data.

Handles a wide variety of real-world resume formats including:
  - Pipe/bullet/tab/multi-space delimited contact lines
  - Section headings with colons, underscores, dashes, mixed case
  - Inline section content ("Skills: Python, Java, SQL")
  - Grouped/categorised skills ("Programming: Python | Databases: SQL")
  - Multiple date formats (Jan 2021, 01/2021, 2021, Jan '21, etc.)
  - Various experience layouts (Title – Company, Company • Title, etc.)
  - Two-column PDF layouts, table-based DOCX resumes
  - PDF artefacts like (cid:NNN), replacement chars, ligatures
"""

from __future__ import annotations

import io
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Optional


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Upload validation (size + content-type sniffing)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Configurable via env (kept simple — no dependency on python-magic).
MAX_UPLOAD_BYTES = int(os.environ.get("CV_TAILOR_MAX_UPLOAD_BYTES", 5 * 1024 * 1024))
MAX_PDF_PAGES = int(os.environ.get("CV_TAILOR_MAX_PDF_PAGES", 15))

_ALLOWED_EXTS = {".pdf", ".docx", ".txt", ".json"}

# Magic byte signatures (first N bytes) keyed by canonical extension.
_MAGIC_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf":  (b"%PDF-",),
    # DOCX is a ZIP container — may start with PK\x03\x04 / PK\x05\x06 / PK\x07\x08.
    ".docx": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
}


class UnsafeUploadError(ValueError):
    """Raised when an uploaded file fails size / type / structural validation."""


def _sniff_extension(filename: str, head: bytes) -> str:
    """Return the canonical extension based on filename + magic bytes.

    Falls back to the filename extension only if the magic check is
    inconclusive (e.g. .txt / .json have no fixed signature).
    """
    name_ext = "".join(Path(filename).suffix).lower()
    if name_ext == ".doc":
        # Legacy .doc is not supported by our DOCX parser; reject explicitly.
        raise UnsafeUploadError(
            "Legacy .doc files are not supported — please save as .docx, PDF, or TXT."
        )
    if name_ext not in _ALLOWED_EXTS:
        raise UnsafeUploadError(
            f"Unsupported file type '{name_ext or '(none)'}' — "
            f"allowed: {', '.join(sorted(_ALLOWED_EXTS))}."
        )

    # For binary formats, require the magic bytes to match the claimed extension.
    for ext, sigs in _MAGIC_SIGNATURES.items():
        if any(head.startswith(s) for s in sigs):
            if name_ext == ext:
                return ext
            # Mismatched: filename says one thing, content says another.
            raise UnsafeUploadError(
                f"File content does not match extension '{name_ext}' — "
                f"refusing to process possible spoofed file."
            )

    # No magic match — must be a text format. Reject if filename claims binary.
    if name_ext in {".pdf", ".docx"}:
        raise UnsafeUploadError(
            f"File '{name_ext}' does not have a valid {name_ext.upper()} signature."
        )
    return name_ext


def safe_read_upload(uploaded_file) -> tuple[bytes, str]:
    """Read and validate a user-uploaded file.

    Returns ``(file_bytes, canonical_extension)``.

    Raises :class:`UnsafeUploadError` if the file exceeds the configured size
    limit or its content does not match a supported, expected format.
    """
    if uploaded_file is None:
        raise UnsafeUploadError("No file uploaded.")

    try:
        uploaded_file.seek(0)
    except Exception:
        pass
    raw = uploaded_file.read()
    try:
        uploaded_file.seek(0)
    except Exception:
        pass

    if not raw:
        raise UnsafeUploadError("Uploaded file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        mb = MAX_UPLOAD_BYTES / (1024 * 1024)
        raise UnsafeUploadError(
            f"File too large ({len(raw) / (1024 * 1024):.1f} MB) — limit is {mb:.0f} MB."
        )

    ext = _sniff_extension(getattr(uploaded_file, "name", "") or "", raw[:8])
    return raw, ext


def generate_resume_document(text: str, fmt: str = "pdf", template: str = "professional") -> tuple[bytes, str]:
    """
    Take plain text resume, parse it into structured data,
    and generate a proper ATS-friendly PDF or DOCX.

    Returns:
        (file_bytes, file_extension)
    """
    from modules.templates import export_pdf_template, export_docx_template

    data = text_to_resume_dict(text)

    tmp = tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        if fmt == "pdf":
            export_pdf_template(data, template_name=template, output_path=tmp_path)
        else:
            export_docx_template(data, template_name=template, output_path=tmp_path)
        return Path(tmp_path).read_bytes(), fmt
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file using pdfplumber.

    Uses layout-aware extraction when available, falls back to default.
    Also extracts text from tables to handle table-based resume layouts.
    """
    import pdfplumber

    text_parts: list[str] = []
    # In-memory open — no temp file is written to disk (prevents PII leakage
    # and lets us enforce a page-count cap before doing expensive work).
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        if len(pdf.pages) > MAX_PDF_PAGES:
            raise UnsafeUploadError(
                f"PDF has {len(pdf.pages)} pages — limit is {MAX_PDF_PAGES}."
            )
        for page in pdf.pages:
            # Try layout-aware extraction first (preserves column structure)
            try:
                page_text = page.extract_text(layout=True)
            except TypeError:
                page_text = page.extract_text()

            if page_text:
                text_parts.append(page_text)

            # Also extract table text (many resumes use tables for layout)
            try:
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            cells = [c.strip() for c in (row or []) if c and c.strip()]
                            if cells:
                                text_parts.append(" | ".join(cells))
            except Exception:
                # Table extraction is best-effort; never let it fail PDF parsing.
                pass

    return "\n".join(text_parts)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file using python-docx.

    Includes paragraphs *and* table cells, since many resumes use tables for
    layout. Adjacent duplicate cells (from merged cells) are collapsed.
    """
    import io

    doc = Document(io.BytesIO(file_bytes))

    parts: list[str] = []

    # Extract paragraphs
    for p in doc.paragraphs:
        text = p.text.strip()
        if text:
            parts.append(text)

    # Extract tables (many professional resumes use table layouts)
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                # Deduplicate adjacent identical cells (merged cells)
                deduped: list[str] = []
                for c in cells:
                    if not deduped or c != deduped[-1]:
                        deduped.append(c)
                parts.append(" | ".join(deduped))

    return "\n".join(parts)


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Decode a plain-text file."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return file_bytes.decode(encoding)
        except (UnicodeDecodeError, ValueError):
            continue
    return file_bytes.decode("utf-8", errors="replace")


def parse_json_resume(file_bytes: bytes) -> dict:
    """Parse a JSON resume file into a dict."""
    text = extract_text_from_txt(file_bytes)
    return json.loads(text)


def extract_text_from_upload(uploaded_file) -> str:
    """
    Universal extractor: accepts a Streamlit UploadedFile and returns plain text.
    Supports PDF, DOCX, TXT, and JSON. Validates size + format first.
    """
    file_bytes, ext = safe_read_upload(uploaded_file)

    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext == ".docx":
        return extract_text_from_docx(file_bytes)
    elif ext == ".json":
        data = parse_json_resume(file_bytes)
        return _json_resume_to_text(data)
    else:
        # Treat anything else as plain text
        return extract_text_from_txt(file_bytes)


def parse_upload_to_dict(uploaded_file) -> Optional[dict]:
    """
    Parse an uploaded file into a structured resume dict.
    Works for JSON, PDF, DOCX, and TXT files. Validates size + format first.
    """
    file_bytes, ext = safe_read_upload(uploaded_file)

    if ext == ".json":
        return parse_json_resume(file_bytes)

    if ext == ".pdf":
        text = extract_text_from_pdf(file_bytes)
    elif ext == ".docx":
        text = extract_text_from_docx(file_bytes)
    else:
        text = extract_text_from_txt(file_bytes)

    result = text_to_resume_dict(text)

    # Ensure name is never empty (Pydantic requires it)
    if not result.get("name"):
        result["name"] = "(Uploaded Resume)"

    return result


def _clean_pdf_artifacts(text: str) -> str:
    """Remove PDF rendering artifacts and normalise whitespace."""
    # Replace (cid:NNN) patterns with a bullet marker
    text = re.sub(r'\(cid:\d+\)', '•', text)
    # Unicode bullet variants
    text = re.sub(r'[\uf0b7\uf0a7\uf0d8\uf076\uf0fc]', '•', text)
    text = re.sub(r'\ufffd', '', text)          # replacement character
    # Collapse multiple bullets into one
    text = re.sub(r'•\s*•+', '•', text)
    # Fix ligatures that pdfplumber sometimes breaks
    text = text.replace('ﬁ', 'fi').replace('ﬂ', 'fl').replace('ﬀ', 'ff')
    text = text.replace('ﬃ', 'ffi').replace('ﬄ', 'ffl')
    # Normalise dashes
    text = text.replace('\u2013', '–').replace('\u2014', '—')
    # Normalise whitespace: collapse 4+ spaces to 3 (preserve 2-3 space gaps for column detection)
    text = re.sub(r' {4,}', '   ', text)
    # Remove zero-width chars
    text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
    # Strip common emoji/icon chars used as decoration in CVs (📧📱📍🔗💼🖥 etc.)
    text = re.sub(r'[\U0001F4E7\U0001F4F1\U0001F4CD\U0001F517\U0001F310\U0001F4BC\U0001F5A5\u260E\u2709\u2706\u2702]', '', text)
    # Also strip other dingbat/symbol prefixes: ✉ ☎ ✆
    text = re.sub(r'[\u2709\u260E\u2706]', '', text)
    return text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Section heading detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Canonical heading keywords (order matters for priority)
_HEADING_MAP: dict[str, str] = {}
for _canon, _aliases in {
    "summary": [
        "summary", "objective", "profile", "about me", "about",
        "professional summary", "career summary", "executive summary",
        "professional profile", "career objective", "personal statement",
        "career profile", "professional objective",
    ],
    "skills": [
        "skills", "technical skills", "core competencies", "technologies",
        "competencies", "technical competencies", "areas of expertise",
        "technical expertise", "key skills", "tools & technologies",
        "tools and technologies", "technical proficiencies",
        "programming skills", "it skills", "software skills",
        "skills & tools", "skills and tools", "proficiencies",
        "tech stack", "tools", "expertise",
    ],
    "experience": [
        "experience", "work experience", "professional experience",
        "employment", "employment history", "work history",
        "career history", "relevant experience", "professional background",
    ],
    "education": [
        "education", "academic", "qualifications", "academic background",
        "educational background", "academic qualifications",
        "education & training", "education and training",
    ],
    "certifications": [
        "certifications", "certification", "licenses", "license",
        "certificates", "professional certifications",
        "certifications & licenses", "certifications and licenses",
        "credentials", "professional development",
    ],
    "projects": [
        "projects", "project", "portfolio", "personal projects",
        "side projects", "key projects", "selected projects",
    ],
    "languages": [
        "languages", "language", "language skills",
        "foreign languages", "language proficiency",
    ],
    "achievements": [
        "achievements", "awards", "honors", "honours",
        "accomplishments", "recognition", "publications",
    ],
    "volunteer": [
        "volunteer", "volunteering", "volunteer experience",
        "community service", "extracurricular",
    ],
    "interests": [
        "interests", "hobbies", "activities",
    ],
    "references": [
        "references",
    ],
}.items():
    for _a in _aliases:
        _HEADING_MAP[_a] = _canon


def _normalise_heading(text: str) -> Optional[str]:
    """Return canonical section name if *text* looks like a heading, else None."""
    # Strip common decorators
    cleaned = text.strip()
    cleaned = re.sub(r'^[#=\-_*~\s]+|[#=\-_*~:\s]+$', '', cleaned)
    cleaned = cleaned.strip()
    key = cleaned.lower()
    # Direct lookup
    if key in _HEADING_MAP:
        return _HEADING_MAP[key]
    # Try without trailing 's'
    if key.endswith('s') and key[:-1] in _HEADING_MAP:
        return _HEADING_MAP[key[:-1]]
    return None


def _is_section_heading(text: str) -> bool:
    """Check if a line looks like a resume section heading."""
    return _normalise_heading(text) is not None


# Regex that detects a heading — standalone or with trailing colon/dash
_SECTION_LINE_RE = re.compile(
    r'^(?:[#=\-_*~\s]*)'
    r'(?P<heading>' + '|'.join(
        re.escape(alias) for alias in sorted(_HEADING_MAP.keys(), key=len, reverse=True)
    ) + r')'
    r'(?:[:\s\-_*~]*$)',
    re.IGNORECASE,
)

# Regex that detects inline heading: "Skills: Python, Java, SQL"
_INLINE_SECTION_RE = re.compile(
    r'^(?P<heading>' + '|'.join(
        re.escape(alias) for alias in sorted(_HEADING_MAP.keys(), key=len, reverse=True)
    ) + r')\s*[:–—\-]\s*(?P<content>.+)',
    re.IGNORECASE,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Contact regex helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
_PHONE_RE = re.compile(
    r'(?:\+?\d{1,3}[\s.-]?)?'       # country code
    r'(?:\(?\d{2,4}\)?[\s.-]?)?'     # area code
    r'\d{3,4}[\s.-]?\d{3,4}'         # main number
)
_LINKEDIN_RE = re.compile(r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+', re.IGNORECASE)
_URL_RE = re.compile(r'https?://[\w./?&=#%-]+', re.IGNORECASE)
_BARE_DOMAIN_RE = re.compile(r'\b[\w-]+\.(?:com|org|io|dev|net|co|me|info|tech|ai|app|xyz)\b', re.IGNORECASE)

# Date patterns
_DATE_RE = re.compile(
    r'(?:'
    # "Jan 2021", "January 2021", "Jan. 2021"
    r'(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
    r'jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
    r'\.?\s*\'?\d{2,4}'
    r'|'
    # "01/2021", "1-2021"
    r'\d{1,2}[/\-]\d{4}'
    r'|'
    # Bare year "2021"
    r'\d{4}'
    r')',
    re.IGNORECASE,
)
_DATE_RANGE_RE = re.compile(
    r'(?P<start>' + _DATE_RE.pattern + r')'
    r'\s*[-–—to]+\s*'
    r'(?P<end>' + _DATE_RE.pattern + r'|present|current|now|ongoing)',
    re.IGNORECASE,
)


def text_to_resume_dict(text: str) -> dict:
    """
    Intelligently parse plain-text resume into a structured dict.

    Handles a wide variety of real-world formats:
      - Pipe / bullet / tab / multi-space delimited contact info
      - ALL CAPS, Title Case, or mixed-case headings
      - Inline sections ("Skills: Python, Java, SQL")
      - Grouped skills ("Programming: Python, Java | Databases: SQL")
      - Various date formats and separators
      - PDF artefacts, ligature breakage, etc.
    """
    # ── Pre-process: clean PDF artifacts ──
    text = _clean_pdf_artifacts(text)

    lines = text.strip().splitlines()
    if not lines:
        return {"name": "", "summary": text}

    result: dict = {
        "name": "",
        "email": "",
        "phone": "",
        "linkedin": "",
        "location": "",
        "website": "",
        "summary": "",
        "skills": [],
        "experience": [],
        "education": [],
        "certifications": [],
        "projects": [],
        "languages": [],
    }

    # ── Extract contact info from first ~10 lines ──
    _extract_contact(lines, result)

    # ── Section splitting ──
    sections = _split_into_sections(lines)

    # ── Fill each field from sections ──
    if "summary" in sections:
        result["summary"] = " ".join(sections["summary"])

    if "skills" in sections:
        result["skills"] = _parse_skills_lines(sections["skills"])

    if "experience" in sections:
        result["experience"] = _parse_experience_lines(sections["experience"])

    if "education" in sections:
        result["education"] = _parse_education_lines(sections["education"])

    if "certifications" in sections:
        # Rejoin multi-line certifications that were split by PDF line wrapping
        # e.g., "Workshop on ML | Deep Neural Networks | NLP" may span 2-3 lines
        cert_joined: list[str] = []
        for line in sections["certifications"]:
            cleaned = re.sub(r'^[•\-–▪›○*●➢➤➣►\s]+', '', line).strip()
            if not cleaned:
                continue
            # If starts with lowercase, or starts with connector words, or starts with '|',
            # or the previous line ended with '|', join to previous
            if (cert_joined
                    and (cleaned[0].islower()
                         or cleaned.startswith('|')
                         or cleaned.startswith('using ')
                         or cleaned.startswith('and ')
                         or cert_joined[-1].rstrip().endswith('|'))):
                cert_joined[-1] = cert_joined[-1].rstrip() + ' ' + cleaned
            else:
                cert_joined.append(cleaned)
        result["certifications"] = [c.strip() for c in cert_joined if c.strip()]

        # Separate skill-like lines from actual certifications
        # Pattern: "Category Name | skill1, skill2" (has | followed by tech/skill items)
        skill_category_re = re.compile(r'^([A-Za-z][A-Za-z\s&/]+)\s*\|\s*(.+)$')
        actual_certs: list[str] = []
        extra_skills: list[str] = []
        for item in result["certifications"]:
            item = item.strip()
            if not item:
                continue
            m = skill_category_re.match(item)
            if m:
                cat_values = m.group(2).strip()
                # If the values have commas → skill list like "Python, JavaScript, C#"
                # OR it's a single short tech name (no cert keywords)
                is_cert = bool(re.search(
                    r'\b(Coursera|Udemy|edX|LinkedIn Learning|Codecademy|Workshop|'
                    r'Bootcamp|Certificate|Certified|BIIT|Aug |Sep |Oct |Nov |Dec |'
                    r'Jan |Feb |Mar |Apr |May |Jun |Jul )\b',
                    item, re.IGNORECASE
                ))
                if not is_cert and (',' in cat_values or len(cat_values.split()) <= 3):
                    # This is a skill category line, not a cert
                    for s in re.split(r'[,;]+', cat_values):
                        s = s.strip()
                        if s and len(s) >= 1:
                            extra_skills.append(s)
                    continue
            actual_certs.append(item)
        result["certifications"] = actual_certs
        # Append extracted skills to the skills list
        if extra_skills:
            existing = {s.lower() for s in result.get("skills", [])}
            for s in extra_skills:
                if s.lower() not in existing:
                    result["skills"].append(s)
                    existing.add(s.lower())

    if "projects" in sections:
        result["projects"] = _parse_project_lines(sections["projects"])

    if "languages" in sections:
        lang_text = " ".join(sections["languages"])
        raw = re.split(r'[,;|•·●▪\u2022\n]+', lang_text)
        result["languages"] = [l.strip().strip("-•·▪ ") for l in raw if l.strip().strip("-•·▪ ")]

    if "achievements" in sections:
        # Append achievements to certifications or create new field
        achv = [
            re.sub(r'^[•\-–▪›○*●\s]+', '', line).strip()
            for line in sections["achievements"]
            if re.sub(r'^[•\-–▪›○*●\s]+', '', line).strip()
        ]
        result.setdefault("achievements", []).extend(achv)

    if "volunteer" in sections:
        vol = [
            re.sub(r'^[•\-–▪›○*●\s]+', '', line).strip()
            for line in sections["volunteer"]
            if re.sub(r'^[•\-–▪›○*●\s]+', '', line).strip()
        ]
        result.setdefault("volunteer", []).extend(vol)

    if "interests" in sections:
        interests_text = " ".join(sections["interests"])
        raw = re.split(r'[,;|•·●▪\u2022\n]+', interests_text)
        result["interests"] = [i.strip().strip("-•·▪ ") for i in raw if i.strip().strip("-•·▪ ")]

    # ── Fallback: if nothing was parsed, put everything as summary ──
    if not result["summary"] and not result["skills"] and not result["experience"]:
        result["summary"] = text[:3000]

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Contact info extraction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _extract_contact(lines: list[str], result: dict) -> None:
    """Populate result with contact info from the first lines of the resume."""
    header_lines = lines[:10]
    name_set = False

    for line in header_lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Stop at first section heading
        if _is_section_heading(stripped):
            break

        # ── Email ──
        email_match = _EMAIL_RE.search(stripped)
        if email_match and not result["email"]:
            result["email"] = email_match.group()

        # ── Phone ──
        if not result["phone"]:
            phone_match = _PHONE_RE.search(stripped)
            if phone_match:
                candidate = phone_match.group().strip()
                # Must have at least 7 digits
                if sum(c.isdigit() for c in candidate) >= 7:
                    result["phone"] = candidate

        # ── LinkedIn ──
        li_match = _LINKEDIN_RE.search(stripped)
        if li_match and not result["linkedin"]:
            result["linkedin"] = li_match.group()

        # ── GitHub / Website ──
        if not result["website"]:
            gh_match = re.search(r'(?:github|portfolio|website)\s*:\s*(https?://[\w./?&=#%-]+)', stripped, re.IGNORECASE)
            if gh_match and 'linkedin' not in gh_match.group(1).lower():
                result["website"] = gh_match.group(1)
            else:
                # Detect bare github.com/username (no label prefix needed)
                gh_bare = re.search(r'github\.com/[\w.-]+', stripped, re.IGNORECASE)
                if gh_bare and 'linkedin' not in gh_bare.group().lower():
                    result["website"] = gh_bare.group()

        # ── Segments delimited by pipe, bullet, tab, or 2+ spaces ──
        # Also handle "Label: value" lines (e.g., "Email: ...", "Phone: ...", "Address: ...")
        label_match = re.match(r'^(?:email|phone|tel|mobile|address|location|city|linkedin|website|github|portfolio)\s*:\s*(.+)', stripped, re.IGNORECASE)
        if label_match:
            field_val = label_match.group(1).strip()
            # The value may itself be pipe-delimited or multi-space delimited:
            # "Email: foo@bar.com | Phone: +92..." or "Email: foo@bar.com   Phone: +92..."
            # Split by pipes OR 2+ spaces (which often separate label:value pairs)
            for seg_val in re.split(r'\s*\|\s*|\s{2,}', field_val):
                seg_val = seg_val.strip()
                lm2 = re.match(r'^(?:email|phone|tel|mobile|address|location|linkedin|website|github|portfolio)\s*:\s*(.+)', seg_val, re.IGNORECASE)
                actual_val = lm2.group(1).strip() if lm2 else seg_val
                if _EMAIL_RE.search(actual_val) and not result["email"]:
                    result["email"] = _EMAIL_RE.search(actual_val).group()
                elif _PHONE_RE.search(actual_val) and not result["phone"]:
                    cand = _PHONE_RE.search(actual_val).group().strip()
                    if sum(c.isdigit() for c in cand) >= 7:
                        result["phone"] = cand
                elif _LINKEDIN_RE.search(actual_val) and not result["linkedin"]:
                    result["linkedin"] = _LINKEDIN_RE.search(actual_val).group()
                elif _URL_RE.search(actual_val) and not result["website"] and "linkedin" not in actual_val.lower():
                    result["website"] = _URL_RE.search(actual_val).group()
                elif not result["location"] and re.search(r'[A-Za-z]+', actual_val):
                    # Only set location if it doesn't look like an email/URL/phone
                    if not _EMAIL_RE.search(actual_val) and not _URL_RE.search(actual_val):
                        if not (_PHONE_RE.search(actual_val) and sum(c.isdigit() for c in actual_val) >= 7):
                            result["location"] = actual_val
            continue

        segments = re.split(r'\s*[|•·\t]\s*|\s{2,}', stripped)
        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue
            # Skip if it's email / phone / linkedin
            if _EMAIL_RE.search(seg):
                continue
            if _LINKEDIN_RE.search(seg):
                continue
            if _PHONE_RE.search(seg) and sum(c.isdigit() for c in seg) >= 7:
                continue
            # Website (URL or bare domain)
            if not result["website"]:
                url_m = _URL_RE.search(seg)
                if url_m and "linkedin" not in url_m.group().lower():
                    result["website"] = url_m.group()
                    continue
                dom_m = _BARE_DOMAIN_RE.search(seg)
                if dom_m and "linkedin" not in dom_m.group().lower():
                    # Make sure this isn't the email domain
                    email_domain = result["email"].split("@")[-1] if result["email"] else ""
                    if dom_m.group().lower() != email_domain.lower():
                        result["website"] = dom_m.group()
                        continue
            # Location (has comma: "City, State")
            if "," in seg and not result["location"]:
                # Heuristic: looks like "City, STATE" or "City, Country"
                if re.search(r'[A-Za-z]+,\s*[A-Za-z]', seg):
                    result["location"] = seg
                    continue
            # Location fallback: bare city name (short, all-alpha, no URL/email/phone)
            # Only match if the segment is relatively short (city names are typically < 20 chars)
            # and the line also contains an email or phone (confirming it's a contact line)
            if (not result["location"]
                    and 2 < len(seg) < 25
                    and re.match(r'^[A-Za-z\s]+$', seg)
                    and not _is_section_heading(seg)
                    and seg.lower() not in ('present', 'current', 'remote')
                    and (result["email"] or result["phone"])):
                result["location"] = seg
                continue

        # ── Name: first non-contact, non-heading line ──
        if not name_set:
            cleaned = _EMAIL_RE.sub("", stripped)
            cleaned = _PHONE_RE.sub("", cleaned)
            cleaned = _LINKEDIN_RE.sub("", cleaned)
            cleaned = _URL_RE.sub("", cleaned)
            cleaned = _BARE_DOMAIN_RE.sub("", cleaned)
            cleaned = re.sub(r'[|•·\t,]', ' ', cleaned).strip()
            cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
            if cleaned and len(cleaned) > 1 and not cleaned.startswith(("http", "www")):
                if not _is_section_heading(cleaned):
                    # Must look like a name: mostly letters
                    alpha_ratio = sum(c.isalpha() or c == ' ' for c in cleaned) / max(len(cleaned), 1)
                    if alpha_ratio > 0.7:
                        result["name"] = cleaned
                        name_set = True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Section splitting
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _split_into_sections(lines: list[str]) -> dict[str, list[str]]:
    """Split resume lines into named sections.

    Detects headings by:
      1. Standalone heading line (e.g., "EXPERIENCE" or "Work Experience:")
      2. Inline heading with content (e.g., "Skills: Python, Java")
      3. ALL-CAPS lines that match known headings
    """
    sections: dict[str, list[str]] = {}
    current_section = "header"
    sections[current_section] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check standalone heading
        m = _SECTION_LINE_RE.match(stripped)
        if m:
            heading = m.group("heading").strip()
            canon = _normalise_heading(heading)
            if canon:
                current_section = canon
                sections.setdefault(current_section, [])
                continue

        # Check inline heading: "Skills: Python, Java, SQL"
        im = _INLINE_SECTION_RE.match(stripped)
        if im:
            heading = im.group("heading").strip()
            canon = _normalise_heading(heading)
            if canon:
                current_section = canon
                sections.setdefault(current_section, [])
                # Add the inline content
                content = im.group("content").strip()
                if content:
                    sections[current_section].append(content)
                continue

        # Check ALL-CAPS line that could be a heading
        if stripped.isupper() and len(stripped.split()) <= 4:
            canon = _normalise_heading(stripped)
            if canon:
                current_section = canon
                sections.setdefault(current_section, [])
                continue

        # Regular content line
        sections.setdefault(current_section, []).append(stripped)

    return sections


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Skills parsing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _parse_skills_lines(lines: list[str]) -> list[str]:
    """Parse skills section into a flat list of individual skills.

    Handles:
      - Comma/semicolon/pipe/bullet separated: "Python, Java, SQL"
      - Categorised: "Programming: Python, Java | Databases: SQL"
      - One-per-line with bullets: "• Python  • Java"
      - Multi-column PDF layouts: "Python   JavaScript   TypeScript"
      - Line-broken multi-word skills: "Computer\nVision" -> "Computer Vision"
    """
    # First, rejoin lines that were broken by PDF line wrapping
    # e.g., "Python | OpenAI API | Computer" + "Vision | OCR" -> single line
    joined_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # If prev line ends without a delimiter and this starts lowercase or continues, join
        if (joined_lines
                and not re.search(r'[,;|\u2022\u00b7\u25cf\u25aa]\s*$', joined_lines[-1])
                and not re.match(r'^[A-Z][a-z]+:', stripped)  # not a category header
                and not stripped[0].isupper()
                or (joined_lines and joined_lines[-1].rstrip().endswith('|'))):
            joined_lines[-1] = joined_lines[-1].rstrip() + ' ' + stripped
        else:
            joined_lines.append(stripped)
    
    # Detect if lines use "Category: value, value" format (one category per line)
    has_category_lines = sum(1 for l in joined_lines if re.match(r'^[A-Za-z\s&/]+:\s*.+', l.strip())) >= 2

    # Also try: if the full text has pipes, rejoin ALL lines first then split
    full_text = ' '.join(l.strip() for l in lines if l.strip())
    has_pipes = '|' in full_text
    has_commas = ',' in full_text
    
    skills: list[str] = []

    # If lines are in "Category: ..." format, process each line separately
    # so category headers are stripped per-line instead of mangled
    if has_category_lines:
        source_lines = joined_lines if joined_lines else lines
    elif has_pipes or has_commas:
        source_lines = [full_text]
    else:
        source_lines = joined_lines if joined_lines else lines

    for line in source_lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Remove leading bullets
        stripped = re.sub(r'^[•\-–▪›○*●►]\s*', '', stripped)

        # Check for categorised format: "Category: skill1, skill2"
        cat_match = re.match(r'^[A-Za-z\s&/]+:\s*(.+)', stripped)
        if cat_match:
            stripped = cat_match.group(1)

        # Split by common delimiters (comma, semicolon, pipe, bullet)
        raw = re.split(r'[,;|•·●▪\u2022]+', stripped)

        for item in raw:
            # Further split by tabs or 2+ spaces (multi-column PDF/DOCX layouts)
            sub_items = re.split(r'\t+|\s{2,}', item)
            for si in sub_items:
                cleaned = si.strip().strip("-•·▪►○ ")
                if cleaned and len(cleaned) >= 1:
                    # Skip if it looks like a category header only
                    if cleaned.endswith(':'):
                        continue
                    # Skip if it looks like a date or number
                    if re.match(r'^\d{4}$', cleaned):
                        continue
                    skills.append(cleaned)

        # If no skills found with delimiters, try space-separated on each line
        # (for formats like "Python Java SQL Docker")
        if not skills:
            for line in lines:
                stripped = line.strip()
                stripped = re.sub(r'^[•\-–▪›○*●►]\s*', '', stripped)
                cat_match = re.match(r'^[A-Za-z\s&/]+:\s*(.+)', stripped)
                if cat_match:
                    stripped = cat_match.group(1)
                words = re.split(r'\s+', stripped)
                for w in words:
                    w = w.strip().strip("-•·▪►○ ")
                    if w and len(w) >= 1 and not w.endswith(':'):
                        skills.append(w)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for s in skills:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)

    return unique


def _parse_experience_lines(lines: list[str]) -> list[dict]:
    """Parse experience section lines into structured entries.

    Handles a wide variety of real-world formats:
      - "Title – Company"  (dash separator)
      - "Title | Company | Jan 2021 – Present"  (pipe separator)
      - "Company Name"  followed by  "Title" on next line
      - "Title, Company" or "Company, Title"
      - "Title at Company"
      - Date lines: "Jan 2021 – Present", "2021 - 2023", "01/2021 - 12/2023"
      - Location lines: "San Francisco, CA"
      - Bullet points: •, -, –, ▪, ›, ○, *, ●, ►, ✓, ✔, ➤
      - Continuation lines from PDF line-wrapping
    """
    entries: list[dict] = []
    current: Optional[dict] = None

    # Bullet marker pattern — small bullets/dashes/checkmarks (NOT arrows like ➢➤➣ which are title markers)
    bullet_re = re.compile(r'^[\u2022\u2023\-\u2013\u25aa\u203a\u25cb*\u25cf\u25ba\u2713\u2714\u26ac\u25e6\u2043]+\s*')

    # Arrow/bullet prefix to strip from title lines (➢➤➣▶►)
    title_prefix_re = re.compile(r'^[\u27a2\u27a4\u27a3\u2794\u279c\u25ba\u25b6\u2022\u25cf]+\s*')

    # "at" separator: "Software Engineer at Google"
    at_re = re.compile(r'^(.+?)\s+(?:at|@)\s+(.+)', re.IGNORECASE)

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue

        # Strip leading arrow/bullet from the line for analysis
        stripped_clean = title_prefix_re.sub('', stripped).strip()
        # A line that's ONLY a bullet marker — skip
        if not stripped_clean:
            i += 1
            continue

        is_bullet = bool(bullet_re.match(stripped)) and len(stripped_clean) > 3

        # ── Bullet point ──
        if is_bullet:
            bullet_text = bullet_re.sub('', stripped).strip()
            # Also strip leading arrow markers (➢➤➣▶►▸) from bullet text
            bullet_text = re.sub(r'^[\u27a2\u27a4\u27a3\u2794\u279c\u25ba\u25b6\u25b8]+\s*', '', bullet_text).strip()
            # Also strip trailing lone bullet markers (PDF artefact)
            bullet_text = re.sub(r'\s*[\u2022\u25cf\u25ba\u27a2]\s*$', '', bullet_text).strip()
            if bullet_text and current:
                current["bullets"].append(bullet_text)
            i += 1
            continue

        # ── Check if line has a date range ──
        date_match = _DATE_RANGE_RE.search(stripped_clean)
        has_date = bool(date_match)

        # ── If it's purely a date/location line for existing entry ──
        if has_date and current and not current["start_date"]:
            _fill_dates_and_location(current, stripped_clean, date_match)
            i += 1
            continue

        # ── Non-bullet text line after a job entry with dates ──
        # In resumes without bullet markers, plain text lines are the bullets
        if (current and current["start_date"] and not has_date
                and not _looks_like_title(stripped_clean)
                and len(stripped_clean) < 200
                and '–' not in stripped_clean and '—' not in stripped_clean
                and '|' not in stripped_clean and '\t' not in stripped_clean):
            # Strip trailing bullet markers
            clean_bullet = re.sub(r'\s*[\u2022\u25cf\u25ba\u27a2]\s*$', '', stripped_clean).strip()
            if not clean_bullet:
                i += 1
                continue
            # If it looks like a sentence/achievement, add as a new bullet
            if len(clean_bullet) > 20:
                current["bullets"].append(clean_bullet)
            # Short orphan text — append to last bullet (line-wrap)
            elif current["bullets"]:
                current["bullets"][-1] += " " + clean_bullet
            else:
                current["bullets"].append(clean_bullet)
            i += 1
            continue

        # ── New entry: title/company line ──
        if not is_bullet:
            # Save previous entry
            if current and (current["title"] or current["bullets"]):
                entries.append(current)

            current = {
                "title": "",
                "company": "",
                "location": "",
                "start_date": "",
                "end_date": "",
                "bullets": [],
            }

            # Remove date from the line for title/company parsing
            line_no_date = stripped_clean
            if date_match:
                line_no_date = stripped_clean[:date_match.start()].strip().rstrip("|-–— ()\t")
                _fill_dates_and_location(current, stripped_clean, date_match)

            # Check if line_no_date has pipe-separated location: "Title – Company| Location"
            pipe_segs = re.split(r'\s*\|\s*', line_no_date)
            if len(pipe_segs) >= 2:
                # Last segment might be location if it's short and has no title words
                last_seg = pipe_segs[-1].strip()
                if last_seg and len(last_seg) < 30 and not _looks_like_title(last_seg):
                    current["location"] = last_seg
                    line_no_date = ' | '.join(pipe_segs[:-1]).strip()

            # Try various separators to split title/company
            parsed = _parse_title_company(line_no_date)
            current["title"] = parsed.get("title", "")
            current["company"] = parsed.get("company", "")
            # Set location from parser if not already set (e.g. 3-segment: Title  Company  City)
            if parsed.get("location") and not current["location"]:
                current["location"] = parsed["location"]

            # Peek at next line for date/location
            if not current["start_date"] and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                next_line_clean = title_prefix_re.sub('', next_line).strip()
                next_dm = _DATE_RANGE_RE.search(next_line_clean)
                next_is_bullet = bool(bullet_re.match(next_line))
                if next_dm and not next_is_bullet:
                    _fill_dates_and_location(current, next_line_clean, next_dm)
                    i += 1  # skip the date line

        i += 1

    if current and (current["title"] or current["bullets"]):
        entries.append(current)

    return entries


def _looks_like_title(text: str) -> bool:
    """Heuristic: does this text look like a job title or company name?"""
    title_words = {
        'engineer', 'developer', 'manager', 'lead', 'analyst', 'designer',
        'architect', 'director', 'intern', 'consultant', 'specialist',
        'coordinator', 'administrator', 'associate', 'senior', 'junior',
        'principal', 'staff', 'head', 'vp', 'president', 'officer',
        'scientist', 'researcher', 'technician', 'assistant', 'executive',
        'supervisor', 'strategist', 'planner', 'advisor', 'partner',
    }
    words = text.lower().split()
    return bool(set(words) & title_words) or '–' in text or '—' in text or '|' in text


def _parse_title_company(text: str) -> dict:
    """Parse a line into title and company using various separator patterns."""
    result = {"title": "", "company": ""}
    if not text.strip():
        return result

    text = text.strip()

    # Try dash separator: "Title – Company" or "Title — Company"
    parts = re.split(r'\s*[–—]\s*', text, maxsplit=1)
    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
        result["title"] = parts[0].strip()
        result["company"] = parts[1].strip()
        return result

    # Try pipe separator: "Title | Company"
    pipe_parts = re.split(r'\s*\|\s*', text)
    if len(pipe_parts) >= 2:
        result["title"] = pipe_parts[0].strip()
        result["company"] = pipe_parts[1].strip()
        return result

    # Try "at" separator: "Title at Company"
    at_match = re.match(r'^(.+?)\s+(?:at|@)\s+(.+)', text, re.IGNORECASE)
    if at_match:
        result["title"] = at_match.group(1).strip()
        result["company"] = at_match.group(2).strip()
        return result

    # Try multi-space separator: "Title   Company   Location" (2+ spaces, from PDF/DOCX layout)
    space_parts = re.split(r'\s{2,}', text)
    if len(space_parts) >= 2:
        # Filter out empty parts
        space_parts = [p.strip() for p in space_parts if p.strip()]
        if len(space_parts) >= 3:
            # 3+ segments: first=title, second=company, remaining=location (handled by caller)
            result["title"] = space_parts[0]
            result["company"] = space_parts[1]
            result["location"] = space_parts[2]
            return result
        elif len(space_parts) == 2:
            left = space_parts[0].strip()
            right = space_parts[1].strip()
            if _looks_like_title(left) and len(left) > 3 and len(right) > 2:
                result["title"] = left
                result["company"] = right
                return result

    # Try bullet/dot separator: "Title • Company" or "Title · Company"
    dot_parts = re.split(r'\s*[•·]\s*', text, maxsplit=1)
    if len(dot_parts) == 2 and dot_parts[0].strip() and dot_parts[1].strip():
        result["title"] = dot_parts[0].strip()
        result["company"] = dot_parts[1].strip()
        return result

    # Try comma separator if it looks like "Title, Company"
    comma_parts = text.split(',', 1)
    if len(comma_parts) == 2:
        left = comma_parts[0].strip()
        right = comma_parts[1].strip()
        # Only use comma split if neither part looks like a location (City, State)
        if not re.match(r'^[A-Z]{2}$', right) and len(left) > 3 and len(right) > 3:
            result["title"] = left
            result["company"] = right
            return result

    # Fallback: entire line is the title
    result["title"] = text
    return result


def _fill_dates_and_location(entry: dict, line: str, date_match: re.Match) -> None:
    """Fill start_date, end_date, and location from a line with dates."""
    entry["start_date"] = date_match.group("start").strip()
    entry["end_date"] = date_match.group("end").strip()

    # Location is everything before the date
    loc_part = line[:date_match.start()].strip().rstrip("|-–— \t")
    if loc_part and not entry["location"]:
        # Clean up location
        loc_part = re.sub(r'^[|•·\-–—]\s*', '', loc_part).strip()
        if loc_part:
            # Don't set location if the text looks like a job title
            if _looks_like_title(loc_part):
                return
            entry["location"] = loc_part


def _parse_education_lines(lines: list[str]) -> list[dict]:
    """Parse education section lines into structured entries.

    Handles many formats:
      - "B.S. Computer Science – University of California, Berkeley"
      - "University of California, Berkeley  |  B.S. Computer Science  |  2016"
      - "Bachelor of Science in Computer Science"
      - "MIT, Cambridge, MA — M.S. in AI, 2023"
      - Continuation lines with GPA, dates, location
      - Lines with degree keywords or university keywords
    """
    entries: list[dict] = []
    current: Optional[dict] = None

    degree_re = re.compile(
        r'\b('
        r'B\.?S\.?|B\.?A\.?|B\.?Sc\.?|B\.?E\.?|B\.?Eng\.?|B\.?Tech\.?|B\.?Com\.?|'
        r'M\.?S\.?|M\.?A\.?|M\.?Sc\.?|M\.?E\.?|M\.?Eng\.?|M\.?Tech\.?|M\.?Com\.?|M\.?B\.?A\.?|'
        r'Ph\.?D\.?|D\.?Phil\.?|Ed\.?D\.?|Psy\.?D\.?|J\.?D\.?|M\.?D\.?|'
        r'Bachelor|Master|Doctor|Diploma|Associate|Certificate|Postgraduate|'
        r'Bachelors|Masters|Doctorate|'
        r'Matric(?:ulation)?|Intermediate|'
        r'O[\s\-]?Levels?|A[\s\-]?Levels?|GCSE|IGCSE|'
        r'SSC|HSC|HSSC|FSc|F\.?A\.?|ICS|I\.?Com\.?|DAE'
        r')\b',
        re.IGNORECASE
    )
    university_re = re.compile(
        r'\b(University|College|Institute|School|Academy|Polytechnic|Universit[àéè])\b',
        re.IGNORECASE
    )
    year_re = re.compile(r'\b(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\.?\s*\'?)?\d{2,4}\b', re.IGNORECASE)
    gpa_re = re.compile(r'(?:GPA|CGPA|Grade)[:\s]*(\d\.\d+)', re.IGNORECASE)
    gpa_bare_re = re.compile(r'\b(\d\.\d{1,2})\s*/\s*\d\.\d{1,2}\b')  # 3.8/4.0
    bullet_re = re.compile(r'^[•\-–▪›○*●►]\s*')

    for line in lines:
        stripped = bullet_re.sub('', line.strip()).strip()
        if not stripped:
            continue

        has_degree = bool(degree_re.search(stripped))
        has_university = bool(university_re.search(stripped))

        # Skip "Key Courses:" / "Key Subjects:" lines — just extract GPA/percentage
        if re.match(r'^Key\s+(?:Courses?|Subjects?)\s*:', stripped, re.IGNORECASE):
            if current:
                g = gpa_re.search(stripped)
                if g and not current["gpa"]:
                    current["gpa"] = g.group(1)
                else:
                    g2 = gpa_bare_re.search(stripped)
                    if g2 and not current["gpa"]:
                        current["gpa"] = g2.group(1)
                # Also check for Percentage: NN%
                pct = re.search(r'(?:Percentage|Marks?)\s*:\s*(\d+(?:\.\d+)?)', stripped, re.IGNORECASE)
                if pct and not current["gpa"]:
                    current["gpa"] = pct.group(1) + "%"
            continue

        # If current entry exists and this line is institution-only (no degree keyword),
        # treat it as continuation rather than starting a new entry
        if has_university and not has_degree and current and not current["institution"]:
            # This is the institution line for the previous degree
            # Extract institution, possibly with location
            inst_parts = re.split(r'\s*\|\s*', stripped)
            # Find the part with the university keyword
            uni_idx = next((i for i, p in enumerate(inst_parts) if university_re.search(p)), 0)
            # Build institution from all relevant parts (may include abbreviation + full name)
            inst_name_parts = []
            for idx, p in enumerate(inst_parts):
                p = p.strip()
                if not p:
                    continue
                yr = year_re.search(p)
                if yr and not current["graduation_date"]:
                    current["graduation_date"] = yr.group().strip()
                else:
                    inst_name_parts.append(p)
            current["institution"] = " | ".join(inst_name_parts) if inst_name_parts else inst_parts[uni_idx].strip()
            continue

        # Start new entry if line has degree keyword OR (university keyword and no current entry)
        if has_degree or (has_university and not current):
            if current:
                entries.append(current)
            current = {
                "degree": "",
                "institution": "",
                "graduation_date": "",
                "gpa": "",
            }

            # Extract dates first (before splitting) — store full range for education
            dr = _DATE_RANGE_RE.search(stripped)
            if dr:
                start_yr = dr.group("start").strip()
                end_yr = dr.group("end").strip()
                # For education, show full range if both years are just years (e.g. "2022 – 2026")
                if (len(start_yr) == 4 and start_yr.isdigit()
                        and len(end_yr) == 4 and end_yr.isdigit()):
                    current["graduation_date"] = f"{start_yr} - {end_yr}"
                else:
                    current["graduation_date"] = end_yr
                # Remove date range from line for cleaner parsing
                clean_line = (stripped[:dr.start()] + stripped[dr.end():]).strip()
                # Also remove trailing/leading tabs and pipe/dash separators
                clean_line = re.sub(r'[\t]+', ' ', clean_line).strip().rstrip("|-–— ")
            else:
                clean_line = re.sub(r'[\t]+', ' ', stripped).strip()
                y = year_re.search(clean_line)
                if y:
                    current["graduation_date"] = y.group().strip()
                    # Remove lone year from line
                    clean_line = (clean_line[:y.start()] + clean_line[y.end():]).strip().rstrip("|-–— ")

            # Extract GPA / CGPA
            g = gpa_re.search(stripped)
            if g:
                current["gpa"] = g.group(1)
            else:
                g2 = gpa_bare_re.search(stripped)
                if g2:
                    current["gpa"] = g2.group(1)

            # Now split the cleaned line by common separators
            # Split by ALL dashes, then reassemble meaningful parts
            all_parts = re.split(r'\s*[–—]\s*', clean_line)
            # Filter out empty parts and parts that are just years/GPA/CGPA
            meaningful: list[str] = []
            for p in all_parts:
                p = p.strip()
                if not p:
                    continue
                # Skip standalone years ("2022", "2026")
                if re.match(r'^\d{4}$', p):
                    continue
                # Skip standalone GPA/CGPA values
                if re.match(r'^(?:C?GPA)\s*:\s*\d', p, re.IGNORECASE):
                    continue
                meaningful.append(p)

            if len(meaningful) >= 2:
                # Figure out which part is the degree and which is the institution
                if degree_re.search(meaningful[0]):
                    current["degree"] = meaningful[0].strip()
                    current["institution"] = meaningful[1].strip()
                elif degree_re.search(meaningful[1]):
                    current["institution"] = meaningful[0].strip()
                    current["degree"] = meaningful[1].strip()
                else:
                    current["degree"] = meaningful[0].strip()
                    current["institution"] = meaningful[1].strip()
            elif len(meaningful) == 1:
                # Only one meaningful segment after dash split — try pipe split
                pass

            if not current["degree"] or (not current["institution"] and len(meaningful) < 2):
                pipe_parts = re.split(r'\s*\|\s*', stripped)
                if len(pipe_parts) >= 2:
                    # Find which part has degree and which has institution
                    deg_idx = next((i for i, p in enumerate(pipe_parts) if degree_re.search(p)), 0)
                    inst_idx = next((i for i, p in enumerate(pipe_parts) if university_re.search(p) and i != deg_idx), -1)
                    current["degree"] = pipe_parts[deg_idx].strip()
                    if inst_idx >= 0:
                        current["institution"] = pipe_parts[inst_idx].strip()
                    elif len(pipe_parts) > 1 and deg_idx == 0:
                        current["institution"] = pipe_parts[1].strip()
                    # Check remaining parts for date
                    for p in pipe_parts:
                        if p.strip() != current["degree"] and p.strip() != current["institution"]:
                            y = year_re.search(p)
                            if y:
                                current["graduation_date"] = y.group().strip()
                elif has_degree and has_university:
                    # Both on same line, no separator — try to split intelligently
                    deg_m = degree_re.search(stripped)
                    uni_m = university_re.search(stripped)
                    if deg_m and uni_m:
                        if deg_m.start() < uni_m.start():
                            # degree comes first
                            # find where institution starts (word before university keyword)
                            pre_uni = stripped[:uni_m.start()].strip()
                            # Check for "in" or comma
                            in_split = re.split(r'\s+(?:in|at|from)\s+|,\s*', pre_uni, maxsplit=1)
                            if len(in_split) >= 1:
                                current["degree"] = in_split[0].strip()
                            current["institution"] = stripped[max(0, uni_m.start()-20):].strip()
                            # Trim "in" or comma from institution start
                            current["institution"] = re.sub(r'^(?:in|at|from|,)\s*', '', current["institution"]).strip()
                        else:
                            current["institution"] = stripped[:deg_m.start()].strip().rstrip(",- ")
                            current["degree"] = stripped[deg_m.start():].strip()
                    else:
                        current["degree"] = stripped
                elif has_degree:
                    current["degree"] = stripped
                elif has_university:
                    current["institution"] = stripped

            # Clean institution/degree if they absorbed date ranges
            if current["institution"]:
                inst_dr = _DATE_RANGE_RE.search(current["institution"])
                if inst_dr:
                    current["institution"] = current["institution"][:inst_dr.start()].strip().rstrip("| -–—")
            if current["degree"]:
                deg_dr = _DATE_RANGE_RE.search(current["degree"])
                if deg_dr:
                    current["degree"] = current["degree"][:deg_dr.start()].strip().rstrip("| -–—")

        elif current:
            # Continuation line for the current education entry
            y = year_re.search(stripped)
            if y and not current["graduation_date"]:
                current["graduation_date"] = y.group().strip()

            g = gpa_re.search(stripped)
            if g and not current["gpa"]:
                current["gpa"] = g.group(1)
            else:
                g2 = gpa_bare_re.search(stripped)
                if g2 and not current["gpa"]:
                    current["gpa"] = g2.group(1)
                else:
                    pct = re.search(r'(?:Percentage|Marks?)\s*:\s*(\d+(?:\.\d+)?)', stripped, re.IGNORECASE)
                    if pct and not current["gpa"]:
                        current["gpa"] = pct.group(1) + "%"

            # Check for location
            loc_match = re.search(r'([A-Z][a-zA-Z\s]+,\s*[A-Z]{2})', stripped)
            if loc_match:
                current.setdefault("location", loc_match.group(1))

            # If institution is still empty, this line might be it
            if not current["institution"] and university_re.search(stripped):
                current["institution"] = stripped
            elif not current["institution"] and not has_degree:
                # Could be institution without university keyword
                if len(stripped) > 5 and not stripped[0].isdigit():
                    current["institution"] = stripped
        else:
            # No current entry — start a new one
            current = {"degree": stripped, "institution": "", "graduation_date": "", "gpa": ""}
            y = year_re.search(stripped)
            if y:
                current["graduation_date"] = y.group().strip()

    if current:
        entries.append(current)

    return entries


def _parse_project_lines(lines: list[str]) -> list[dict]:
    """Parse project section lines into structured entries.

    Handles formats:
      - "ProjectName (Tech1, Tech2, Tech3)"
        "Description text..."
      - "ProjectName – Description"
      - Bullet description lines
    """
    entries: list[dict] = []
    current: Optional[dict] = None

    bullet_re = re.compile(r'^[•\-–▪›○*●►]\s*')
    # Arrow/bullet prefix to strip from project title lines (➢➤➣▶►▸)
    proj_prefix_re = re.compile(r'^[➢➤➣▶►▸•●]+\s*')
    # Pattern for project title with tech stack in parentheses
    tech_paren_re = re.compile(r'^(.+?)\s*\(([^)]+)\)\s*$')

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Strip leading arrows/bullets from line for analysis
        stripped = proj_prefix_re.sub('', stripped).strip()
        if not stripped:
            continue

        is_bullet = bool(bullet_re.match(stripped)) and len(stripped) > 2

        if is_bullet and current:
            desc = bullet_re.sub('', stripped).strip()
            if current["description"]:
                current["description"] += " " + desc
            else:
                current["description"] = desc
        elif is_bullet and not current:
            # Orphan bullet — skip
            continue
        else:
            # Check if this is a title line or a description continuation
            # A title line usually:
            #   - Has parenthesised tech: "ProjectName (Python, React)"
            #   - Or starts with a capitalised name and is short-ish
            #   - Or follows an empty gap
            tech_match = tech_paren_re.match(stripped)

            if tech_match:
                paren_content = tech_match.group(2).strip()
                # Distinguish real tech (has comma or multiple words with tech names)
                # from labels like (FYP) or (Healthcare)
                is_real_tech = (',' in paren_content
                    or len(paren_content.split()) >= 2
                    and any(t in paren_content.lower() for t in ['python', 'java', 'react', 'node', 'sql', 'api', 'docker', 'aws']))
                if current:
                    entries.append(current)
                if is_real_tech:
                    current = {
                        "name": tech_match.group(1).strip(),
                        "description": "",
                        "technologies": paren_content,
                    }
                else:
                    # Parenthesized text is a label/type, not tech
                    current = {
                        "name": f"{tech_match.group(1).strip()} ({paren_content})",
                        "description": "",
                        "technologies": "",
                    }
            elif current and current["name"] and not current["description"]:
                # This is a description line for the current project
                current["description"] = stripped
            elif current and current["description"]:
                # Check if this looks like a NEW project (Name: description format)
                # before treating it as a continuation
                colon_match = re.match(r'^([^:]{5,60}):\s+(.{10,})', stripped)
                if colon_match:
                    entries.append(current)
                    current = {
                        "name": colon_match.group(1).strip(),
                        "description": colon_match.group(2).strip(),
                        "technologies": "",
                    }
                    continue
                # Check if this looks like a new project TITLE line:
                # - Starts with uppercase
                # - Doesn't start with common description verbs
                # - Has parenthesised tech/label or is a distinct heading
                _desc_verb_re = re.compile(
                    r'^(?:Built|Designed|Developed|Implemented|Integrated|Created|Managed|'
                    r'Gathered|Conducted|Performed|Deployed|Extracted|Prepared|Collaborated|'
                    r'Supported|Optimized|Worked|Assisted|Customized|Fine-tuned|Trained|'
                    r'Led|Established|Achieved|Improved|Reduced|Increased|Delivered|'
                    r'Maintained|Monitored|Automated|Architected|Configured|Coordinated|'
                    r'Facilitated|Generated|Handled|Launched|Oversaw|Pioneered|Resolved|'
                    r'Spearheaded|Streamlined|Utilized|Validated|Wrote)\b',
                    re.IGNORECASE
                )
                _has_paren = bool(tech_paren_re.match(stripped))
                if (_has_paren
                        or (stripped[0].isupper()
                            and not _desc_verb_re.match(stripped)
                            and len(stripped) < 80
                            and not stripped.endswith('.'))):
                    # This looks like a new project title
                    entries.append(current)
                    if _has_paren:
                        pm = tech_paren_re.match(stripped)
                        paren_content = pm.group(2).strip()
                        is_real_tech = (',' in paren_content
                            or len(paren_content.split()) >= 2
                            and any(t in paren_content.lower() for t in ['python', 'java', 'react', 'node', 'sql', 'api', 'docker', 'aws']))
                        if is_real_tech:
                            current = {
                                "name": pm.group(1).strip(),
                                "description": "",
                                "technologies": paren_content,
                            }
                        else:
                            current = {
                                "name": f"{pm.group(1).strip()} ({paren_content})",
                                "description": "",
                                "technologies": "",
                            }
                    else:
                        current = {
                            "name": stripped,
                            "description": "",
                            "technologies": "",
                        }
                    continue
                # Continuation of description
                current["description"] += " " + stripped
            else:
                # New project without tech parens
                if current:
                    entries.append(current)
                # Try splitting "Name: description" (single-line project)
                colon_match = re.match(r'^([^:]{5,60}):\s+(.{10,})', stripped)
                if colon_match:
                    current = {
                        "name": colon_match.group(1).strip(),
                        "description": colon_match.group(2).strip(),
                        "technologies": "",
                    }
                    continue
                # Try splitting "Name – description"
                parts = re.split(r'\s*[–—]\s*', stripped, maxsplit=1)
                if len(parts) == 2 and len(parts[0]) < 60:
                    current = {
                        "name": parts[0].strip(),
                        "description": parts[1].strip(),
                        "technologies": "",
                    }
                else:
                    current = {
                        "name": stripped,
                        "description": "",
                        "technologies": "",
                    }

    if current:
        entries.append(current)

    # Post-process: extract technologies from descriptions if not already set
    # Post-process: extract technologies from descriptions if not already set
    _TECH_NAMES = [
        'Python', 'JavaScript', 'TypeScript', 'Java', r'C#', r'C\+\+', 'Dart', 'Go', 'Rust', 'Ruby', 'Swift', 'Kotlin',
        'React', 'Angular', 'Vue', r'Next\.js', r'Node\.js', 'Express', 'Django', 'Flask', 'FastAPI', 'Spring',
        'Flutter', 'PyTorch', 'TensorFlow', 'Keras', 'OpenCV', r'YOLOv\d+', 'YOLO',
        'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'SQL', 'SQLite',
        'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP', 'Firebase',
        'Git', 'GitHub', 'GitLab', 'Jenkins',
        r'REST(?:ful)?\s*APIs?', 'GraphQL', 'gRPC',
        'LiveKit', 'Eleven Labs', r'OpenAI(?:\s+GPT)?', 'LangChain', r'GPT-?\d*',
        'Streamlit', 'Gradio', 'RoboFlow', 'Jupyter',
    ]
    _tech_pattern = re.compile(
        r'\b(' + '|'.join(_TECH_NAMES) + r')\b',
        re.IGNORECASE
    )
    for entry in entries:
        if not entry.get("technologies") and entry.get("description"):
            found = _tech_pattern.findall(entry["description"])
            if found:
                # De-duplicate while preserving order
                seen: set[str] = set()
                techs: list[str] = []
                for t in found:
                    t_lower = t.lower()
                    if t_lower not in seen:
                        seen.add(t_lower)
                        techs.append(t)
                entry["technologies"] = ", ".join(techs)

    return entries


def _json_resume_to_text(data: dict) -> str:
    """Convert a JSON resume dict to readable plain text."""
    lines: list[str] = []

    if data.get("name"):
        lines.append(data["name"])
    contact_parts = []
    for key in ("email", "phone", "linkedin", "location"):
        if data.get(key):
            contact_parts.append(data[key])
    if contact_parts:
        lines.append(" | ".join(contact_parts))

    if data.get("summary"):
        lines.extend(["", "Summary", data["summary"]])

    if data.get("skills"):
        skills = data["skills"]
        if isinstance(skills, list):
            lines.extend(["", "Skills", ", ".join(skills)])
        else:
            lines.extend(["", "Skills", str(skills)])

    if data.get("experience"):
        lines.extend(["", "Experience"])
        for exp in data["experience"]:
            title = exp.get("title", "")
            company = exp.get("company", "")
            start = exp.get("start_date", "")
            end = exp.get("end_date", "")
            lines.append(f"{title} | {company} | {start} - {end}")
            for bullet in exp.get("bullets", []):
                lines.append(f"- {bullet}")

    if data.get("education"):
        lines.extend(["", "Education"])
        for edu in data["education"]:
            degree = edu.get("degree", "")
            inst = edu.get("institution", "")
            year = edu.get("graduation_date", edu.get("year", ""))
            lines.append(f"{degree} | {inst} | {year}")

    if data.get("projects"):
        lines.extend(["", "Projects"])
        for proj in data["projects"]:
            name = proj.get("name", "")
            desc = proj.get("description", "")
            lines.append(f"{name} - {desc}")

    return "\n".join(lines)


def diagnose_parse(text: str) -> dict:
    """Diagnostic function: returns both the parsed dict and the raw extracted text.

    Useful for debugging what the parser sees vs. what it extracts.
    """
    cleaned = _clean_pdf_artifacts(text)
    parsed = text_to_resume_dict(text)

    # Find which sections were detected
    sections = _split_into_sections(cleaned.strip().splitlines())
    section_names = [k for k in sections.keys() if k != "header"]

    return {
        "raw_text": cleaned,
        "raw_text_lines": len(cleaned.strip().splitlines()),
        "raw_text_chars": len(cleaned),
        "sections_detected": section_names,
        "parsed": parsed,
        "field_summary": {
            "name": bool(parsed.get("name")),
            "email": bool(parsed.get("email")),
            "phone": bool(parsed.get("phone")),
            "location": bool(parsed.get("location")),
            "linkedin": bool(parsed.get("linkedin")),
            "website": bool(parsed.get("website")),
            "summary": bool(parsed.get("summary")),
            "skills_count": len(parsed.get("skills", [])),
            "experience_count": len(parsed.get("experience", [])),
            "total_bullets": sum(len(e.get("bullets", [])) for e in parsed.get("experience", [])),
            "education_count": len(parsed.get("education", [])),
            "certifications_count": len(parsed.get("certifications", [])),
            "projects_count": len(parsed.get("projects", [])),
            "languages_count": len(parsed.get("languages", [])),
        },
    }