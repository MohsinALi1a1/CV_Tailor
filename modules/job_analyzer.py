"""
CV Tailor — Job Description Analyser
=======================================
Extracts structured information from a job description and compares
it against a resume to produce a skill-gap report.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from utils.text_processing import extract_keywords, match_keywords

logger = logging.getLogger(__name__)


@dataclass
class JobAnalysis:
    """Structured analysis of a job description."""
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    # Comparison fields (populated when compared with a resume)
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    match_rate: float = 0.0
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "required_skills": self.required_skills,
            "preferred_skills": self.preferred_skills,
            "responsibilities": self.responsibilities,
            "keywords": self.keywords,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "match_rate": round(self.match_rate, 1),
            "suggestions": self.suggestions,
        }

    def summary_text(self) -> str:
        lines = [
            "═══════════════════════════════════════",
            "  JOB DESCRIPTION ANALYSIS",
            "═══════════════════════════════════════",
            "",
        ]
        if self.required_skills:
            lines.append("  📌 Required Skills:")
            for s in self.required_skills:
                lines.append(f"      • {s}")
            lines.append("")

        if self.preferred_skills:
            lines.append("  💡 Preferred Skills:")
            for s in self.preferred_skills:
                lines.append(f"      • {s}")
            lines.append("")

        if self.responsibilities:
            lines.append("  📋 Key Responsibilities:")
            for r in self.responsibilities[:8]:
                lines.append(f"      • {r}")
            lines.append("")

        if self.matched_skills:
            lines.append(f"  ✅ Matched Skills ({len(self.matched_skills)}):")
            lines.append(f"      {', '.join(self.matched_skills)}")
            lines.append("")

        if self.missing_skills:
            lines.append(f"  ⚠️  Missing Skills ({len(self.missing_skills)}):")
            lines.append(f"      {', '.join(self.missing_skills)}")
            lines.append("")

        if self.match_rate:
            lines.append(f"  📊 Skill Match Rate: {self.match_rate:.0f}%")
            lines.append("")

        if self.suggestions:
            lines.append("  💡 Suggestions:")
            for s in self.suggestions:
                lines.append(f"      • {s}")

        lines.append("═══════════════════════════════════════")
        return "\n".join(lines)


class JobAnalyzer:
    """Analyses job descriptions and compares them against resumes."""

    def __init__(self) -> None:
        self._claude = None

    def _get_claude(self):
        if self._claude is None:
            from utils.api_clients import get_claude_client
            self._claude = get_claude_client()
        return self._claude

    # ── Analyse JD only ───────────────────────────────────────

    def analyse(self, job_description: str, use_ai: bool = True) -> JobAnalysis:
        """Analyse a job description and extract structured data.

        Args:
            job_description: Full job description text.
            use_ai: Whether to use Claude for better extraction.

        Returns:
            JobAnalysis with extracted skills and responsibilities.
        """
        analysis = JobAnalysis()
        analysis.keywords = extract_keywords(job_description, top_n=25)

        if use_ai:
            try:
                claude = self._get_claude()
                structured = claude.extract_keywords(job_description)
                analysis.required_skills = structured.get("required_skills", [])
                analysis.preferred_skills = structured.get("preferred_skills", [])
                analysis.responsibilities = structured.get("responsibilities", [])
            except Exception as e:
                logger.warning("AI analysis failed, using NLP fallback: %s", e)
                analysis.required_skills = analysis.keywords[:15]
        else:
            analysis.required_skills = analysis.keywords[:15]

        logger.info(
            "JD analysis: %d required, %d preferred, %d responsibilities",
            len(analysis.required_skills),
            len(analysis.preferred_skills),
            len(analysis.responsibilities),
        )
        return analysis

    # ── Compare JD vs Resume ──────────────────────────────────

    def compare(
        self,
        job_description: str,
        resume_text: str,
        use_ai: bool = True,
    ) -> JobAnalysis:
        """Analyse a JD and compare it against a resume.

        Args:
            job_description: Full job description text.
            resume_text: Full resume as plain text.
            use_ai: Whether to use Claude.

        Returns:
            JobAnalysis with comparison results populated.
        """
        analysis = self.analyse(job_description, use_ai=use_ai)

        # Keyword matching
        resume_keywords = extract_keywords(resume_text, top_n=30)

        # Match against required skills
        all_jd_skills = analysis.required_skills + analysis.preferred_skills
        if not all_jd_skills:
            all_jd_skills = analysis.keywords

        match_result = match_keywords(resume_keywords, all_jd_skills)
        analysis.matched_skills = match_result["matched"]
        analysis.missing_skills = match_result["missing"]
        analysis.match_rate = match_result["match_rate"]

        # Generate suggestions
        analysis.suggestions = self._build_suggestions(analysis)

        logger.info(
            "JD comparison: %.0f%% match (%d matched, %d missing)",
            analysis.match_rate,
            len(analysis.matched_skills),
            len(analysis.missing_skills),
        )
        return analysis

    # ── Compare from structured data ──────────────────────────

    def compare_from_data(
        self,
        job_description: str,
        resume_data: dict[str, Any],
        use_ai: bool = True,
    ) -> JobAnalysis:
        """Compare a JD against structured resume data.

        Args:
            job_description: Full job description text.
            resume_data: Structured resume dictionary.
            use_ai: Whether to use Claude.

        Returns:
            JobAnalysis with comparison results.
        """
        from utils.file_export import resume_data_to_text
        resume_text = resume_data_to_text(resume_data)
        return self.compare(job_description, resume_text, use_ai=use_ai)

    # ── Suggestions ───────────────────────────────────────────

    def _build_suggestions(self, analysis: JobAnalysis) -> list[str]:
        """Build actionable suggestions from the analysis."""
        suggestions: list[str] = []

        if analysis.match_rate >= 80:
            suggestions.append("Great match! Your resume aligns well with this role.")
        elif analysis.match_rate >= 60:
            suggestions.append(
                "Decent match, but there is room to improve keyword alignment."
            )
        else:
            suggestions.append(
                "Low match rate — consider tailoring your resume significantly for this role."
            )

        if analysis.missing_skills:
            critical = [
                s for s in analysis.missing_skills
                if s in [r.lower() for r in analysis.required_skills]
            ]
            if critical:
                suggestions.append(
                    f"Critical missing skills (required): {', '.join(critical[:5])}"
                )
            nice_to_have = [
                s for s in analysis.missing_skills
                if s in [p.lower() for p in analysis.preferred_skills]
            ]
            if nice_to_have:
                suggestions.append(
                    f"Nice-to-have missing: {', '.join(nice_to_have[:5])}"
                )

        if analysis.required_skills and not analysis.matched_skills:
            suggestions.append(
                "None of the required skills were found in your resume — this role may not be a good fit, "
                "or your resume needs significant revision."
            )

        suggestions.append(
            "Tip: Use the Resume Tailoring Engine to automatically align your resume."
        )

        return suggestions
