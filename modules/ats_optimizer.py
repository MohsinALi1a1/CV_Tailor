"""
CV Tailor — ATS Optimisation Module
======================================
Analyses a resume and produces an ATS compatibility score (0–100)
along with actionable improvement suggestions.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from config import ATS_STANDARD_SECTIONS, ATS_ACTION_VERBS
from utils.text_processing import (
    extract_keywords,
    match_keywords,
    match_keywords_against_text,
    parse_resume_sections,
    has_quantified_achievement,
    starts_with_action_verb,
    bullet_to_list,
    count_words,
    calculate_keyword_density,
)

logger = logging.getLogger(__name__)


@dataclass
class ATSReport:
    """Structured ATS analysis report."""
    overall_score: float = 0.0
    section_score: float = 0.0
    keyword_score: float = 0.0
    formatting_score: float = 0.0
    bullet_quality_score: float = 0.0
    length_score: float = 0.0

    sections_found: list[str] = field(default_factory=list)
    sections_missing: list[str] = field(default_factory=list)
    section_order: list[str] = field(default_factory=list)
    section_order_optimal: bool = True
    keyword_density: dict[str, float] = field(default_factory=dict)
    formatting_issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    total_words: int = 0
    total_bullets: int = 0
    bullets_with_numbers: int = 0
    bullets_with_action_verbs: int = 0

    # Spelling and industry (optional)
    spell_accuracy_pct: float = 100.0
    spell_issues: list[str] = field(default_factory=list)
    detected_industry: str = ""
    detected_industry_confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialise report to dict."""
        return {
            "overall_score": round(self.overall_score, 1),
            "breakdown": {
                "section_score": round(self.section_score, 1),
                "keyword_score": round(self.keyword_score, 1),
                "formatting_score": round(self.formatting_score, 1),
                "bullet_quality_score": round(self.bullet_quality_score, 1),
                "length_score": round(self.length_score, 1),
            },
            "sections_found": self.sections_found,
            "sections_missing": self.sections_missing,
            "section_order": self.section_order,
            "section_order_optimal": self.section_order_optimal,
            "formatting_issues": self.formatting_issues,
            "suggestions": self.suggestions,
            "stats": {
                "total_words": self.total_words,
                "total_bullets": self.total_bullets,
                "bullets_with_numbers": self.bullets_with_numbers,
                "bullets_with_action_verbs": self.bullets_with_action_verbs,
                "spell_accuracy_pct": round(self.spell_accuracy_pct, 1),
            },
            "spell_issues": self.spell_issues,
            "detected_industry": self.detected_industry,
            "detected_industry_confidence": round(self.detected_industry_confidence, 1),
        }

    def summary_text(self) -> str:
        """Return a human-readable summary."""
        lines = [
            f"═══════════════════════════════════════",
            f"  ATS COMPATIBILITY SCORE: {self.overall_score:.0f} / 100",
            f"═══════════════════════════════════════",
            f"",
            f"  Section Structure   : {self.section_score:.0f}/25",
            f"  Keyword Optimisation: {self.keyword_score:.0f}/25",
            f"  Formatting          : {self.formatting_score:.0f}/20",
            f"  Bullet Quality      : {self.bullet_quality_score:.0f}/20",
            f"  Resume Length        : {self.length_score:.0f}/10",
            f"",
            f"  Words: {self.total_words}  |  Bullets: {self.total_bullets}",
            f"  Quantified bullets: {self.bullets_with_numbers}/{self.total_bullets}",
            f"  Action-verb bullets: {self.bullets_with_action_verbs}/{self.total_bullets}",
            f"",
        ]
        if self.sections_missing:
            lines.append(f"  ⚠️  Missing sections: {', '.join(self.sections_missing)}")
        if self.section_order and not self.section_order_optimal:
            lines.append(f"  ⚠️  Section order: {' → '.join(self.section_order)}")
            lines.append(f"     Recommended: Summary → Skills → Experience → Education → Certs → Projects")
        if self.detected_industry:
            lines.append(f"  🏭 Detected industry: {self.detected_industry} ({self.detected_industry_confidence:.0f}% conf.)")
        if self.spell_accuracy_pct < 98:
            lines.append(f"  ✏️  Spell accuracy: {self.spell_accuracy_pct:.1f}%")
            if self.spell_issues:
                lines.append(f"     Issues: {'; '.join(self.spell_issues[:3])}")
        if self.formatting_issues:
            lines.append(f"  ⚠️  Formatting issues:")
            for issue in self.formatting_issues:
                lines.append(f"      • {issue}")
        if self.suggestions:
            lines.append(f"")
            lines.append(f"  💡 Suggestions:")
            for s in self.suggestions:
                lines.append(f"      • {s}")
        lines.append(f"═══════════════════════════════════════")
        return "\n".join(lines)


class ATSOptimizer:
    """Analyses a resume for ATS compatibility and produces a scored report.

    Scoring breakdown (total 100):
        - Section structure: 25 pts
        - Keyword optimisation: 25 pts
        - Formatting (ATS-safe): 20 pts
        - Bullet quality: 20 pts
        - Resume length: 10 pts

    Based on industry research from Jobscan, ResumeWorded, and ATS vendor docs:
        - 76.4% of recruiters filter by skills
        - 59.7% filter by education
        - 55.3% filter by job titles
        - 50.6% filter by certifications
        - Resumes with job title in headline get 10.6x more interviews (Jobscan)
    """

    REQUIRED_SECTIONS = {"Experience", "Education", "Skills"}
    RECOMMENDED_SECTIONS = {"Summary", "Certifications", "Projects"}

    # Optimal section order for ATS (based on recruiter studies)
    OPTIMAL_ORDER = ["summary", "skills", "experience", "education", "certifications", "projects"]

    def __init__(self) -> None:
        pass

    def analyse(
        self,
        resume_text: str,
        job_description: str | None = None,
        run_spell_check: bool = True,
        detect_industry_for_jd: bool = True,
    ) -> ATSReport:
        """Run full ATS analysis on a resume.

        Args:
            resume_text: Plain-text resume.
            job_description: Optional JD for keyword matching.
            run_spell_check: Run a lightweight spell check pass.
            detect_industry_for_jd: Detect target industry from JD (if provided).

        Returns:
            ATSReport with scores and suggestions.
        """
        report = ATSReport()
        report.total_words = count_words(resume_text)

        # ── 1. Section structure (25 pts) ─────────────────────
        report.section_score = self._score_sections(resume_text, report)

        # ── 2. Keyword optimisation (25 pts) ──────────────────
        report.keyword_score = self._score_keywords(resume_text, job_description, report)

        # ── 3. Formatting (20 pts) ────────────────────────────
        report.formatting_score = self._score_formatting(resume_text, report)

        # ── 4. Bullet quality (20 pts) ────────────────────────
        report.bullet_quality_score = self._score_bullets(resume_text, report)

        # ── 5. Length (10 pts) ────────────────────────────────
        report.length_score = self._score_length(resume_text, report)

        # ── Optional: spell-check pass (advisory only) ────────
        if run_spell_check:
            try:
                from modules.spell_check import spell_check
                spell_result = spell_check(resume_text, max_issues=20)
                report.spell_accuracy_pct = spell_result.accuracy_pct
                report.spell_issues = [
                    f"'{i.word}' (line {i.line})"
                    + (f" → {i.suggestions[0]}" if i.suggestions else "")
                    for i in spell_result.issues[:10]
                ]
                if spell_result.misspelled_count > 5:
                    report.suggestions.append(
                        f"Spell check flagged {spell_result.misspelled_count} potential issues. "
                        f"Review: {', '.join([i.word for i in spell_result.issues[:5]])}"
                    )
            except Exception as e:
                logger.debug("Spell check skipped: %s", e)

        # ── Optional: industry detection from JD ──────────────
        if detect_industry_for_jd and job_description:
            try:
                from modules.industry_intel import detect_industry
                ind = detect_industry(job_description)
                report.detected_industry = ind.primary_industry_name
                report.detected_industry_confidence = ind.confidence
                if ind.industry_keywords_missing:
                    top_missing = ind.industry_keywords_missing[:5]
                    report.suggestions.append(
                        f"For {ind.primary_industry_name} roles, consider mentioning: "
                        f"{', '.join(top_missing)}"
                    )
            except Exception as e:
                logger.debug("Industry detection skipped: %s", e)

        # ── Overall ──
        report.overall_score = (
            report.section_score
            + report.keyword_score
            + report.formatting_score
            + report.bullet_quality_score
            + report.length_score
        )

        logger.info("ATS analysis complete — score: %.0f/100", report.overall_score)
        return report

    # ── Scoring helpers ───────────────────────────────────────

    def _score_sections(self, text: str, report: ATSReport) -> float:
        """Score based on presence of standard resume sections."""
        sections = parse_resume_sections(text)
        found_names = {s.lower() for s in sections.keys()}

        # Check ATS standard sections via heading detection
        for heading in ATS_STANDARD_SECTIONS:
            if heading.lower() in found_names or any(heading.lower() in f for f in found_names):
                report.sections_found.append(heading)

        # --- Fallback: content-based detection ---
        # If heading-based detection missed key sections, look at actual content
        text_lower = text.lower()

        # Experience: look for job-like patterns (title at company, date ranges)
        _found_lower = {s.lower() for s in report.sections_found}
        if not any("experience" in f for f in _found_lower):
            exp_patterns = [
                re.search(r'\b(?:present|current|\d{4})\b.*\b(?:present|current|\d{4})\b', text_lower),
                re.search(r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{4}\s*[-\u2013]', text_lower),
                re.search(r'(?:developer|engineer|manager|analyst|designer|consultant|intern|lead|director|specialist)\b', text_lower),
            ]
            if sum(1 for p in exp_patterns if p) >= 2:
                report.sections_found.append("Experience")

        _found_lower = {s.lower() for s in report.sections_found}
        if not any("education" in f for f in _found_lower):
            edu_patterns = [
                re.search(r'\b(?:bachelor|master|b\.?s\.?|m\.?s\.?|b\.?e\.?|m\.?e\.?|phd|diploma|degree|university|college|institute)\b', text_lower),
                re.search(r'\b(?:gpa|cgpa|magna|cum laude|honors?)\b', text_lower),
            ]
            if any(edu_patterns):
                report.sections_found.append("Education")

        _found_lower = {s.lower() for s in report.sections_found}
        if not any("skills" in f or "competencies" in f for f in _found_lower):
            # Count technical-looking terms
            tech_terms = re.findall(
                r'\b(?:python|java|javascript|react|node|sql|aws|docker|kubernetes|'
                r'git|linux|html|css|typescript|angular|vue|django|flask|tensorflow|'
                r'pytorch|mongodb|postgresql|redis|graphql|api|rest|agile|scrum|'
                r'c\+\+|c#|ruby|php|swift|kotlin|go|rust|scala|matlab|r\b|excel|'
                r'machine\s+learning|deep\s+learning|data\s+science|nlp|computer\s+vision|'
                r'devops|ci/cd|microservices|cloud)\b', text_lower)
            if len(tech_terms) >= 4:
                report.sections_found.append("Skills")

        _found_lower = {s.lower() for s in report.sections_found}
        if not any("summary" in f or "profile" in f or "objective" in f for f in _found_lower):
            # Check if there's a paragraph-like block at the top (summary)
            lines = text.strip().splitlines()
            for line in lines[:10]:
                stripped = line.strip()
                if len(stripped) > 80 and not re.match(r'^[\s\-•*➢►]', stripped):
                    report.sections_found.append("Summary")
                    break

        _found_lower = {s.lower() for s in report.sections_found}
        if not any("project" in f for f in _found_lower):
            if re.search(r'\b(?:project|github\.com|repository|built\s+a|developed\s+a)\b', text_lower):
                report.sections_found.append("Projects")

        if not any("certification" in f for f in _found_lower):
            if re.search(r'\b(?:certif|certified|certificate|credential|accredit)\b', text_lower):
                report.sections_found.append("Certifications")

        # Determine missing required sections
        _found_lower = {s.lower() for s in report.sections_found}
        for req in self.REQUIRED_SECTIONS:
            if not any(req.lower() in f for f in _found_lower):
                report.sections_missing.append(req)
                report.suggestions.append(f"Add a '{req}' section — required by most ATS systems.")

        # Determine missing recommended sections
        for rec in self.RECOMMENDED_SECTIONS:
            if not any(rec.lower() in f for f in _found_lower):
                report.suggestions.append(f"Consider adding a '{rec}' section for completeness.")

        # Score: 25 pts max
        required_found = len(self.REQUIRED_SECTIONS) - len(
            [s for s in self.REQUIRED_SECTIONS if s in report.sections_missing]
        )
        score = (required_found / len(self.REQUIRED_SECTIONS)) * 18

        # Bonus for recommended
        rec_found = sum(
            1 for rec in self.RECOMMENDED_SECTIONS
            if any(rec.lower() in f for f in _found_lower)
        )
        score += (rec_found / len(self.RECOMMENDED_SECTIONS)) * 4

        # ── Section order check (3 pts) ──
        # Detect actual order of canonical sections in the resume
        actual_order = self._detect_section_order(text)
        report.section_order = actual_order
        # Check whether actual order matches OPTIMAL_ORDER (skipping missing)
        optimal_subseq = [s for s in self.OPTIMAL_ORDER if s in actual_order]
        report.section_order_optimal = actual_order == optimal_subseq
        if report.section_order_optimal:
            score += 3
        elif actual_order and len(actual_order) >= 3:
            # Award partial credit for being mostly right
            correct_pairs = sum(
                1 for i in range(len(optimal_subseq) - 1)
                if i + 1 < len(actual_order)
                and actual_order.index(optimal_subseq[i]) < actual_order.index(optimal_subseq[i + 1])
            )
            ratio = correct_pairs / max(len(optimal_subseq) - 1, 1)
            score += ratio * 3
            report.suggestions.append(
                "Reorder sections for ATS-optimal flow: "
                + " → ".join(s.title() for s in self.OPTIMAL_ORDER if s in actual_order)
            )

        return min(score, 25)

    def _detect_section_order(self, text: str) -> list[str]:
        """Detect order of canonical sections by their first occurrence in text.

        Returns canonical section keys in the order they appear in the resume.
        """
        text_lower = text.lower()
        # Map heading variants to canonical keys
        canonical_map: dict[str, list[str]] = {
            "summary": ["summary", "professional summary", "profile", "objective", "about"],
            "skills": ["skills", "technical skills", "core competencies", "key skills"],
            "experience": ["experience", "work experience", "professional experience", "employment"],
            "education": ["education", "academic background", "academics"],
            "certifications": ["certifications", "licenses & certifications", "credentials"],
            "projects": ["projects", "key projects", "selected projects"],
        }
        positions: list[tuple[int, str]] = []
        for canonical, variants in canonical_map.items():
            best_pos = -1
            for v in variants:
                # Match as heading line (start/end with whitespace or punctuation)
                m = re.search(rf"(?:^|\n)\s*{re.escape(v)}\s*[:\n]", text_lower)
                if m and (best_pos == -1 or m.start() < best_pos):
                    best_pos = m.start()
            if best_pos >= 0:
                positions.append((best_pos, canonical))
        positions.sort(key=lambda x: x[0])
        return [c for _, c in positions]

    def _score_keywords(
        self, text: str, job_description: str | None, report: ATSReport
    ) -> float:
        """Score keyword alignment with job description."""
        if not job_description:
            # Without a JD, give a baseline score based on having technical terms
            resume_kw = extract_keywords(text, top_n=20)
            if len(resume_kw) >= 10:
                report.suggestions.append(
                    "Provide a job description for detailed keyword analysis."
                )
                return 15  # decent baseline
            else:
                report.suggestions.append(
                    "Your resume has few identifiable keywords. Add more technical terms."
                )
                return 8

        job_kw = extract_keywords(job_description, top_n=25)
        # Use text-based matching for accurate scoring (not keyword-list vs keyword-list)
        match_result = match_keywords_against_text(text, job_kw)

        rate = match_result["match_rate"]
        report.keyword_density = calculate_keyword_density(text, job_kw[:10])

        if match_result["missing"]:
            report.suggestions.append(
                f"Missing keywords: {', '.join(match_result['missing'][:8])}"
            )

        # 25 pts scaled by match rate
        return min((rate / 100) * 25, 25)

    def _score_formatting(self, text: str, report: ATSReport) -> float:
        """Score based on ATS-safe formatting practices (industry standard checks).

        Based on Jobscan/Indeed/SHRM research:
        - No tables, images, charts, text boxes
        - Simple bullet points (solid circle, dash)
        - Contact info NOT in header/footer
        - Standard fonts (Calibri, Arial, Helvetica, Georgia)
        - Consistent date format (Month YYYY)
        - Single-column layout
        - No fancy Unicode symbols
        - Standard section headings
        """
        score = 20.0  # start at max, deduct for issues

        # Check for tables (markdown-style or ASCII)
        if re.search(r"\|.*\|.*\|", text):
            score -= 4
            report.formatting_issues.append("Table-like formatting detected — ATS may not parse tables.")

        # Check for excessive special characters
        special_count = len(re.findall(r"[★☆●◆▪︎■□▸►➤➜→↗✦✧⚡🔹🔸]", text))
        if special_count > 3:
            score -= 3
            report.formatting_issues.append(
                f"Found {special_count} fancy symbols — use simple bullets (-, *) instead."
            )

        # Check for images / embedded content references
        if re.search(r"\.(png|jpg|jpeg|gif|svg|bmp)", text, re.IGNORECASE):
            score -= 4
            report.formatting_issues.append("Image references found — ATS cannot read images.")

        # Check for proper date formatting
        good_dates = re.findall(
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b",
            text, re.IGNORECASE,
        )
        slash_dates = re.findall(r"\d{1,2}/\d{1,2}/\d{2,4}", text)
        if slash_dates:
            score -= 2
            report.formatting_issues.append(
                "Use 'Month Year' date format (e.g., 'Jan 2024') — avoid numeric dates like 01/15/2024."
            )
        elif not good_dates:
            score -= 1
            report.formatting_issues.append(
                "No standard date formats found. Use 'Mon YYYY - Mon YYYY' or 'Mon YYYY - Present'."
            )

        # Check for standard section headings (critical for ATS parsing)
        text_lower = text.lower()
        standard_headings = {
            'professional summary': ['summary', 'professional summary', 'profile', 'objective'],
            'professional experience': ['experience', 'professional experience', 'work experience', 'employment'],
            'education': ['education', 'academic'],
            'skills': ['skills', 'technical skills', 'core competencies', 'key skills'],
        }
        missing_standard = []
        for std_name, variants in standard_headings.items():
            found = False
            for v in variants:
                # Check if it appears as a heading (on its own line)
                if re.search(rf'^\s*{re.escape(v)}\s*$', text, re.IGNORECASE | re.MULTILINE):
                    found = True
                    break
            if not found:
                # Check if content exists but heading is missing/non-standard
                if std_name == 'professional experience' and re.search(r'\b(?:developer|engineer|manager|analyst)\b', text_lower):
                    missing_standard.append(std_name)
        if missing_standard:
            score -= min(len(missing_standard) * 1, 3)
            report.formatting_issues.append(
                f"Use standard ATS headings: {', '.join(missing_standard)}."
            )

        # Check line length
        long_lines = [l for l in text.splitlines() if len(l) > 150]
        if len(long_lines) > 3:
            score -= 1
            report.formatting_issues.append(
                f"{len(long_lines)} lines exceed 150 chars — consider shorter bullets."
            )

        # Check for email and phone presence
        has_email = bool(re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text))
        has_phone = bool(re.search(r'[\(\+]?\d[\d\s\-\.\(\)]{7,}\d', text))
        if not has_email:
            score -= 1
            report.formatting_issues.append("No email address detected — essential for ATS.")
        if not has_phone:
            score -= 1
            report.formatting_issues.append("No phone number detected — recommended for ATS.")

        if not report.formatting_issues:
            report.suggestions.append("✅ Formatting looks ATS-compatible!")

        return max(score, 0)

    def _score_bullets(self, text: str, report: ATSReport) -> float:
        """Score bullet-point quality (action verbs, quantification)."""
        bullets = bullet_to_list(text)
        report.total_bullets = len(bullets)

        if not bullets:
            report.suggestions.append("Use bullet points for experience descriptions.")
            return 5  # minimal score

        with_numbers = sum(1 for b in bullets if has_quantified_achievement(b))
        with_verbs = sum(1 for b in bullets if starts_with_action_verb(b))

        report.bullets_with_numbers = with_numbers
        report.bullets_with_action_verbs = with_verbs

        total = len(bullets)
        number_ratio = with_numbers / total
        verb_ratio = with_verbs / total

        score = (number_ratio * 10) + (verb_ratio * 10)

        if number_ratio < 0.3:
            report.suggestions.append(
                f"Only {with_numbers}/{total} bullets have quantified results. "
                "Add numbers, percentages, or $ values."
            )
        if verb_ratio < 0.5:
            report.suggestions.append(
                f"Only {with_verbs}/{total} bullets start with action verbs. "
                "Start each bullet with a strong verb (Led, Built, Improved, etc.)."
            )

        return min(score, 20)

    def _score_length(self, text: str, report: ATSReport) -> float:
        """Score based on resume length.

        Industry standards:
        - 1-page resume (0-10 years): 400-800 words ideal
        - 2-page resume (10+ years): 800-1200 words acceptable
        - Entry level: 300-500 words
        - Senior/executive: up to 1200 words
        """
        words = report.total_words

        if 400 <= words <= 800:
            return 10
        elif 300 <= words < 400:
            report.suggestions.append(
                "Resume is a bit short (~{} words). Aim for 400–800 words. "
                "Add more detail to experience bullets with quantified achievements.".format(words)
            )
            return 7
        elif 800 < words <= 1200:
            report.suggestions.append(
                "Resume is {} words — acceptable for senior roles (2 pages). "
                "For mid-level roles, aim for under 800 words (1 page).".format(words)
            )
            return 8  # More lenient for 2-page resumes
        elif words < 300:
            report.suggestions.append(
                "Resume is too short ({} words). Add more detail: "
                "quantified achievements, technical skills, and project descriptions.".format(words)
            )
            return 4
        else:
            report.suggestions.append(
                f"Resume is {words} words — too long for most ATS reviewers. "
                "Trim to 1–2 pages maximum. Focus on the last 10-15 years of experience."
            )
            return 5

    # ── Convenience: analyse from data dict ───────────────────

    def analyse_from_data(
        self,
        resume_data: dict[str, Any],
        job_description: str | None = None,
    ) -> ATSReport:
        """Run ATS analysis on structured resume data.

        Args:
            resume_data: Structured resume dictionary.
            job_description: Optional JD text.

        Returns:
            ATSReport.
        """
        from utils.file_export import resume_data_to_text
        text = resume_data_to_text(resume_data)
        return self.analyse(text, job_description)
