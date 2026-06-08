"""
CV Tailor — Resume Builder Module
====================================
Builds professional, ATS-friendly resumes from structured input.
Optionally enhances content via the Claude API.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

from modules.models import ResumeData, ExperienceEntry, EducationEntry, ProjectEntry
from utils.file_export import export_pdf, export_docx, export_text, resume_data_to_text

logger = logging.getLogger(__name__)


class ResumeBuilder:
    """Orchestrates resume creation from structured data.

    Usage::

        builder = ResumeBuilder()
        builder.set_contact("Jane Doe", "jane@example.com", "+1-555-0100", "NYC")
        builder.set_summary("Senior Python developer with 8+ years experience…")
        builder.add_skill("Python")
        builder.add_experience(title="Lead Dev", company="Acme", ...)
        builder.add_education(degree="BSc CS", institution="MIT", ...)

        # Optionally enhance with AI
        builder.enhance_with_ai()

        # Export
        builder.export("pdf")
    """

    def __init__(self) -> None:
        self._data: dict[str, Any] = {
            "name": "",
            "email": "",
            "phone": "",
            "location": "",
            "linkedin": "",
            "website": "",
            "summary": "",
            "skills": [],
            "experience": [],
            "education": [],
            "certifications": [],
            "projects": [],
            "languages": [],
            "research_papers": [],
            "volunteer_work": [],
            "achievements": [],
        }
        self._claude = None  # lazy-loaded

    # ── Contact ───────────────────────────────────────────────

    def set_contact(
        self,
        name: str,
        email: str = "",
        phone: str = "",
        location: str = "",
        linkedin: str = "",
        website: str = "",
    ) -> "ResumeBuilder":
        """Set contact / header information."""
        self._data.update(
            name=name,
            email=email,
            phone=phone,
            location=location,
            linkedin=linkedin,
            website=website,
        )
        return self

    # ── Summary ───────────────────────────────────────────────

    def set_summary(self, summary: str) -> "ResumeBuilder":
        """Set the professional summary section."""
        self._data["summary"] = summary
        return self

    # ── Skills ────────────────────────────────────────────────

    def add_skill(self, skill: str) -> "ResumeBuilder":
        """Add a single skill."""
        if skill and skill not in self._data["skills"]:
            self._data["skills"].append(skill)
        return self

    def set_skills(self, skills: list[str]) -> "ResumeBuilder":
        """Replace skills list entirely."""
        self._data["skills"] = list(dict.fromkeys(skills))  # dedupe, keep order
        return self

    # ── Experience ────────────────────────────────────────────

    def add_experience(
        self,
        title: str,
        company: str,
        location: str = "",
        start_date: str = "",
        end_date: str = "Present",
        bullets: list[str] | None = None,
    ) -> "ResumeBuilder":
        """Add one work-experience entry."""
        entry = {
            "title": title,
            "company": company,
            "location": location,
            "start_date": start_date,
            "end_date": end_date,
            "bullets": bullets or [],
        }
        self._data["experience"].append(entry)
        return self

    # ── Education ─────────────────────────────────────────────

    def add_education(
        self,
        degree: str,
        institution: str,
        location: str = "",
        graduation_date: str = "",
        gpa: str = "",
    ) -> "ResumeBuilder":
        """Add one education entry."""
        entry = {
            "degree": degree,
            "institution": institution,
            "location": location,
            "graduation_date": graduation_date,
            "gpa": gpa,
        }
        self._data["education"].append(entry)
        return self

    # ── Certifications ────────────────────────────────────────

    def add_certification(self, cert: str) -> "ResumeBuilder":
        """Add a certification."""
        if cert and cert not in self._data["certifications"]:
            self._data["certifications"].append(cert)
        return self

    # ── Projects ──────────────────────────────────────────────

    def add_project(
        self,
        name: str,
        description: str = "",
        technologies: str = "",
    ) -> "ResumeBuilder":
        """Add a project entry."""
        self._data["projects"].append({
            "name": name,
            "description": description,
            "technologies": technologies,
        })
        return self

    # ── Languages ─────────────────────────────────────────────

    def set_languages(self, languages: list[str]) -> "ResumeBuilder":
        """Set spoken / written languages."""
        self._data["languages"] = languages
        return self

    # ── Research Papers ─────────────────────────────────────

    def add_research_paper(
        self,
        title: str,
        authors: str = "",
        venue: str = "",
        year: str = "",
        url: str = "",
    ) -> "ResumeBuilder":
        """Add a research paper / publication entry."""
        self._data["research_papers"].append({
            "title": title,
            "authors": authors,
            "venue": venue,
            "year": year,
            "url": url,
        })
        return self

    # ── Volunteer Work ─────────────────────────────────────

    def add_volunteer_work(
        self,
        role: str,
        organization: str = "",
        start_date: str = "",
        end_date: str = "",
        description: str = "",
    ) -> "ResumeBuilder":
        """Add a volunteer work entry."""
        self._data["volunteer_work"].append({
            "role": role,
            "organization": organization,
            "start_date": start_date,
            "end_date": end_date,
            "description": description,
        })
        return self

    # ── Achievements ───────────────────────────────────────

    def add_achievement(self, achievement: str) -> "ResumeBuilder":
        """Add an achievement / award entry."""
        self._data["achievements"].append(achievement)
        return self

    # ── Bulk load ─────────────────────────────────────────────

    def load_data(self, data: dict[str, Any]) -> "ResumeBuilder":
        """Load resume data from a dict (e.g. from JSON).

        Validates against the ResumeData model.
        """
        validated = ResumeData(**data)
        self._data = validated.to_dict()
        return self

    def load_json(self, path: str) -> "ResumeBuilder":
        """Load resume data from a JSON file."""
        import json

        raw = Path(path).read_text(encoding="utf-8")
        return self.load_data(json.loads(raw))

    # ── AI Enhancement ────────────────────────────────────────

    def _get_claude(self):
        if self._claude is None:
            from utils.api_clients import get_claude_client
            self._claude = get_claude_client()
        return self._claude

    def enhance_with_ai(self) -> "ResumeBuilder":
        """Use Claude to improve summary, bullet points, and overall quality.

        Requires ANTHROPIC_API_KEY to be set.
        """
        claude = self._get_claude()
        logger.info("Enhancing resume with AI…")

        # Improve summary
        if self._data.get("summary"):
            self._data["summary"] = claude.improve_text(
                self._data["summary"],
                "This is a professional summary for a resume. Keep it to 3-4 sentences. "
                "NEVER add years of experience or any details not already in the original text.",
            )
            logger.debug("Summary enhanced.")

        # Improve experience bullets
        for exp in self._data.get("experience", []):
            if exp.get("bullets"):
                exp["bullets"] = claude.rewrite_bullets(exp["bullets"])
                logger.debug("Bullets enhanced for: %s at %s", exp["title"], exp["company"])

        logger.info("AI enhancement complete.")
        return self

    def enhance_with_ai_star(self) -> "ResumeBuilder":
        """Use Claude to rewrite bullets using the STAR approach.

        STAR = Situation, Task, Action, Result.
        Each bullet is rewritten to follow this framework for maximum impact.
        """
        claude = self._get_claude()
        logger.info("Enhancing resume with AI (STAR approach)…")

        # Improve summary
        if self._data.get("summary"):
            self._data["summary"] = claude.improve_text(
                self._data["summary"],
                "This is a professional summary for a resume. Keep it to 3-4 sentences. "
                "Make it results-oriented with quantified achievements. "
                "NEVER add years of experience or any details not already in the original text.",
            )

        # Rewrite experience bullets using STAR
        for exp in self._data.get("experience", []):
            if exp.get("bullets"):
                exp["bullets"] = claude.rewrite_bullets_star(
                    exp["bullets"],
                    role=exp.get("title", ""),
                    company=exp.get("company", ""),
                )
                logger.debug("STAR bullets for: %s at %s", exp["title"], exp["company"])

        # Improve project descriptions using STAR
        for proj in self._data.get("projects", []):
            if proj.get("description"):
                proj["description"] = claude.improve_text(
                    proj["description"],
                    "Rewrite this project description using the STAR approach (Situation, Task, Action, Result). "
                    "Keep it to 1-2 concise sentences. Start with an action verb. Quantify impact.",
                )

        logger.info("AI STAR enhancement complete.")
        return self

    # ── Getters ───────────────────────────────────────────────

    def get_data(self) -> dict[str, Any]:
        """Return the current resume data dict."""
        return self._data.copy()

    def get_validated_data(self) -> ResumeData:
        """Return validated ResumeData model."""
        return ResumeData(**self._data)

    def to_plain_text(self) -> str:
        """Return a plain-text representation of the resume."""
        return resume_data_to_text(self._data)

    # ── Export ────────────────────────────────────────────────

    def export(
        self,
        fmt: Literal["pdf", "docx", "txt"] = "pdf",
        output_path: str | None = None,
    ) -> Path:
        """Export the resume to the specified format.

        Args:
            fmt: Output format — 'pdf', 'docx', or 'txt'.
            output_path: Optional custom output path.

        Returns:
            Path to the generated file.
        """
        exporters = {
            "pdf": export_pdf,
            "docx": export_docx,
            "txt": export_text,
        }
        if fmt not in exporters:
            raise ValueError(f"Unsupported format '{fmt}'. Choose from: {list(exporters.keys())}")

        path = exporters[fmt](self._data, output_path)
        logger.info("Resume exported → %s", path)
        return path
