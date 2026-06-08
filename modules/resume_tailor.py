"""
CV Tailor — Resume Tailoring Engine
======================================
Takes an existing resume + job description and produces a tailored version
optimised for ATS keyword matching and human readability.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from utils.text_processing import (
    extract_keywords,
    match_keywords,
    match_keywords_against_text,
    clean_text,
)

logger = logging.getLogger(__name__)


class ResumeTailor:
    """Tailors a resume to a specific job description.

    Workflow:
        1. Extract keywords from the job description.
        2. Compare with the resume.
        3. Rewrite / reorder content to improve alignment.
        4. Return tailored resume + gap report.
    """

    def __init__(self) -> None:
        self._claude = None

    def _get_claude(self):
        if self._claude is None:
            from utils.api_clients import get_claude_client
            self._claude = get_claude_client()
        return self._claude

    # ── Main entry point ──────────────────────────────────────

    def tailor(
        self,
        resume_text: str,
        job_description: str,
        use_ai: bool = True,
    ) -> dict[str, Any]:
        """Tailor a resume to a job description.

        Args:
            resume_text: The full resume as plain text.
            job_description: The target job description.
            use_ai: Whether to use Claude for rewriting (default True).

        Returns:
            Dict with keys:
                - tailored_resume: str
                - keyword_report: dict
                - suggestions: list[str]
                - ats_keywords_added: list[str]
        """
        logger.info("Starting resume tailoring…")

        # Step 1 — Keyword extraction
        job_keywords = extract_keywords(job_description, top_n=30)
        # Use text-based matching for accuracy (checks if keyword appears in full text)
        keyword_report = match_keywords_against_text(resume_text, job_keywords)

        logger.info(
            "Keyword match rate: %.1f%% (%d matched, %d missing)",
            keyword_report["match_rate"],
            len(keyword_report["matched"]),
            len(keyword_report["missing"]),
        )

        # Step 2 — AI-powered tailoring
        if use_ai:
            tailored_resume = self._ai_tailor(resume_text, job_description)
            structured_kw = self._extract_structured_keywords(job_description)
        else:
            tailored_resume = self._basic_tailor(resume_text, keyword_report)
            structured_kw = {
                "required_skills": job_keywords[:15],
                "preferred_skills": [],
                "responsibilities": [],
            }

        # Step 3 — Generate suggestions
        suggestions = self._generate_suggestions(keyword_report, structured_kw)

        # Step 4 — Re-evaluate tailored resume against same JD keywords
        tailored_match = match_keywords_against_text(tailored_resume, job_keywords)
        newly_added = set(tailored_match["matched"]) - set(keyword_report["matched"])

        return {
            "tailored_resume": clean_text(tailored_resume),
            "keyword_report": keyword_report,
            "tailored_keyword_report": tailored_match,
            "suggestions": suggestions,
            "ats_keywords_added": sorted(newly_added),
            "structured_keywords": structured_kw,
        }

    # ── AI tailoring ──────────────────────────────────────────

    def _ai_tailor(self, resume_text: str, job_description: str) -> str:
        """Use Claude to perform semantic tailoring."""
        claude = self._get_claude()
        return claude.tailor_for_job(resume_text, job_description)

    def _extract_structured_keywords(self, job_description: str) -> dict:
        """Use Claude to extract structured keywords from a JD."""
        try:
            claude = self._get_claude()
            return claude.extract_keywords(job_description)
        except Exception as e:
            logger.warning("Structured keyword extraction failed: %s", e)
            return {"required_skills": [], "preferred_skills": [], "responsibilities": []}

    # ── Basic (non-AI) tailoring ──────────────────────────────

    def _basic_tailor(self, resume_text: str, keyword_report: dict) -> str:
        """Keyword-injection tailoring without AI.

        Multi-strategy approach based on ATS research:
        1. Inject missing keywords into Skills section
        2. Weave top keywords into Summary
        3. Add keywords to first experience entry context
        4. Ensure proper section headings exist
        """
        missing = keyword_report.get("missing", [])
        if not missing:
            return resume_text

        import re
        result = resume_text

        # 1. Inject into Skills section (smart grouping)
        skills_pattern = re.compile(
            r"((?:skills?|technical\s+skills|core\s+competencies|key\s+skills)\s*\n)(.*?)(\n\n|\n[A-Z]|\Z)",
            re.IGNORECASE | re.DOTALL,
        )
        m = skills_pattern.search(result)
        if m:
            existing_skills = m.group(2).strip()
            existing_lower = existing_skills.lower()
            new_kws = [k for k in missing[:15] if k.lower() not in existing_lower]
            if new_kws:
                augmented = existing_skills + ", " + ", ".join(new_kws)
                result = result[: m.start(2)] + augmented + result[m.end(2):]
        else:
            # Add Skills section if missing
            result += "\n\nSkills\n" + ", ".join(missing[:15])

        # 2. Inject top keywords into Summary (natural phrasing)
        remaining = [k for k in missing if k.lower() not in result.lower()][:5]
        if remaining:
            summary_pat = re.compile(
                r"((?:professional\s+summary|summary|profile|objective)\s*\n)(.*?)(\n\n|\n[A-Z])",
                re.IGNORECASE | re.DOTALL,
            )
            sm = summary_pat.search(result)
            if sm:
                summary_text = sm.group(2).strip()
                to_add = [k for k in remaining if k.lower() not in summary_text.lower()]
                if to_add:
                    phrase = f" Proficient in {', '.join(to_add[:4])}."
                    augmented_summary = summary_text.rstrip('.') + '.' + phrase
                    result = result[:sm.start(2)] + augmented_summary + result[sm.end(2):]

        # 3. Add keywords to experience context (natural weaving)
        still_missing = [k for k in missing if k.lower() not in result.lower()][:3]
        if still_missing:
            exp_pat = re.compile(
                r"((?:professional\s+experience|experience|work\s+experience)\s*\n)",
                re.IGNORECASE,
            )
            em = exp_pat.search(result)
            if em:
                after_heading = result[em.end():]
                bullet_match = re.search(r'^(\s*-\s*)', after_heading, re.MULTILINE)
                if bullet_match:
                    insert_pos = em.end() + bullet_match.start()
                    context_line = f"  Key technologies: {', '.join(still_missing)}\n"
                    if "key technologies" not in result.lower():
                        result = result[:insert_pos] + context_line + result[insert_pos:]

        # 4. Ensure proper ATS section headings
        text_lower = result.lower()
        if 'summary' not in text_lower[:200] and 'profile' not in text_lower[:200]:
            # Check if there's a paragraph-like block that could be a summary
            lines = result.strip().splitlines()
            for i, line in enumerate(lines[:10]):
                stripped = line.strip()
                if len(stripped) > 80 and not re.match(r'^[\s\-•*]', stripped):
                    # Insert "Professional Summary" heading before this paragraph
                    result = '\n'.join(lines[:i]) + '\n\nProfessional Summary\n' + '\n'.join(lines[i:])
                    break

        return result

    # ── Suggestions generator ─────────────────────────────────

    def _generate_suggestions(
        self,
        keyword_report: dict,
        structured_kw: dict,
    ) -> list[str]:
        """Generate human-readable improvement suggestions."""
        suggestions: list[str] = []

        missing = keyword_report.get("missing", [])
        match_rate = keyword_report.get("match_rate", 0)

        if match_rate < 50:
            suggestions.append(
                f"⚠️  Your resume matches only {match_rate}% of job keywords. "
                "Consider significant revisions."
            )
        elif match_rate < 75:
            suggestions.append(
                f"📊 Keyword match rate is {match_rate}%. Room for improvement."
            )
        else:
            suggestions.append(
                f"✅ Good keyword coverage at {match_rate}%."
            )

        if missing:
            top_missing = missing[:8]
            suggestions.append(
                f"🔑 Missing keywords to add: {', '.join(top_missing)}"
            )

        required = structured_kw.get("required_skills", [])
        if required:
            suggestions.append(
                f"📌 Required skills from JD: {', '.join(required[:10])}"
            )

        preferred = structured_kw.get("preferred_skills", [])
        if preferred:
            suggestions.append(
                f"💡 Nice-to-have skills: {', '.join(preferred[:8])}"
            )

        suggestions.append(
            "📝 Tip: Mirror the exact phrasing from the job description where truthful."
        )
        suggestions.append(
            "📝 Tip: Quantify achievements with numbers, percentages, or dollar amounts."
        )

        return suggestions

    # ── Convenience: tailor from data dict ─────────────────────

    def tailor_from_data(
        self,
        resume_data: dict[str, Any],
        job_description: str,
        use_ai: bool = True,
    ) -> dict[str, Any]:
        """Tailor starting from structured resume data.

        Converts to text, tailors, then returns results.
        """
        from utils.file_export import resume_data_to_text

        resume_text = resume_data_to_text(resume_data)
        return self.tailor(resume_text, job_description, use_ai=use_ai)
