"""
CV Tailor — Bonus Features Module
====================================
Cover letter generation, LinkedIn summary generator,
and multilingual resume support.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CoverLetterGenerator:
    """Generate tailored cover letters using Claude.

    Usage::

        gen = CoverLetterGenerator()
        letter = gen.generate(
            resume_text="...",
            job_description="...",
            company_name="Acme Corp",
            hiring_manager="John Smith",
        )
    """

    def __init__(self) -> None:
        self._claude = None

    def _get_claude(self):
        if self._claude is None:
            from utils.api_clients import get_claude_client
            self._claude = get_claude_client()
        return self._claude

    def generate(
        self,
        resume_text: str,
        job_description: str,
        company_name: str = "",
        hiring_manager: str = "",
        role: str = "",
    ) -> str:
        """Generate a cover letter.

        Args:
            resume_text: The full resume text.
            job_description: The target job description.
            company_name: Name of the hiring company.
            hiring_manager: Name of the hiring manager.
            role: Target job title (optional).

        Returns:
            Cover letter as plain text.
        """
        claude = self._get_claude()
        letter = claude.generate_cover_letter(
            resume_text=resume_text,
            job_description=job_description,
            company_name=company_name,
            hiring_manager=hiring_manager,
            role=role,
        )
        logger.info("Cover letter generated (%d chars)", len(letter))
        return letter

    def generate_from_data(
        self,
        resume_data: dict[str, Any],
        job_description: str,
        company_name: str = "",
        hiring_manager: str = "",
        role: str = "",
    ) -> str:
        """Generate a cover letter from structured resume data.

        Args:
            resume_data: Structured resume dictionary.
            job_description: The target job description.
            company_name: Name of the hiring company.
            hiring_manager: Name of the hiring manager.
            role: Target job title (optional).

        Returns:
            Cover letter as plain text.
        """
        from utils.file_export import resume_data_to_text
        resume_text = resume_data_to_text(resume_data)
        return self.generate(resume_text, job_description, company_name, hiring_manager, role)

    def save(self, letter_text: str, output_path: str) -> Path:
        """Save a cover letter to a text file.

        Args:
            letter_text: The cover letter content.
            output_path: Destination file path.

        Returns:
            Path to the saved file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(letter_text, encoding="utf-8")
        logger.info("Cover letter saved: %s", path)
        return path


class LinkedInSummaryGenerator:
    """Generate LinkedIn 'About' summaries using Claude.

    Usage::

        gen = LinkedInSummaryGenerator()
        summary = gen.generate(resume_text="...")
    """

    def __init__(self) -> None:
        self._claude = None

    def _get_claude(self):
        if self._claude is None:
            from utils.api_clients import get_claude_client
            self._claude = get_claude_client()
        return self._claude

    def generate(self, resume_text: str) -> str:
        """Generate a LinkedIn summary from a resume.

        Args:
            resume_text: Full resume as plain text.

        Returns:
            LinkedIn 'About' section text.
        """
        claude = self._get_claude()
        summary = claude.generate_linkedin_summary(resume_text)
        logger.info("LinkedIn summary generated (%d chars)", len(summary))
        return summary

    def generate_from_data(self, resume_data: dict[str, Any]) -> str:
        """Generate from structured resume data.

        Args:
            resume_data: Structured resume dictionary.

        Returns:
            LinkedIn summary text.
        """
        from utils.file_export import resume_data_to_text
        return self.generate(resume_data_to_text(resume_data))


class MultilingualResume:
    """Translate resumes into different languages using Claude.

    Usage::

        ml = MultilingualResume()
        spanish_resume = ml.translate(resume_text="...", target_language="Spanish")
    """

    SUPPORTED_LANGUAGES = [
        "Arabic", "Chinese (Simplified)", "Chinese (Traditional)",
        "Dutch", "French", "German", "Hindi", "Italian", "Japanese",
        "Korean", "Portuguese", "Russian", "Spanish", "Turkish", "Urdu",
    ]

    def __init__(self) -> None:
        self._claude = None

    def _get_claude(self):
        if self._claude is None:
            from utils.api_clients import get_claude_client
            self._claude = get_claude_client()
        return self._claude

    def translate(self, resume_text: str, target_language: str) -> str:
        """Translate a resume to a target language.

        Args:
            resume_text: Full resume as plain text.
            target_language: Target language name.

        Returns:
            Translated resume text.
        """
        claude = self._get_claude()
        translated = claude.translate_resume(resume_text, target_language)
        logger.info("Resume translated to %s (%d chars)", target_language, len(translated))
        return translated

    def translate_from_data(
        self,
        resume_data: dict[str, Any],
        target_language: str,
    ) -> str:
        """Translate from structured resume data.

        Args:
            resume_data: Structured resume dictionary.
            target_language: Target language name.

        Returns:
            Translated resume text.
        """
        from utils.file_export import resume_data_to_text
        return self.translate(resume_data_to_text(resume_data), target_language)

    @classmethod
    def list_languages(cls) -> list[str]:
        """Return list of supported languages."""
        return cls.SUPPORTED_LANGUAGES.copy()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Convenience functions (used by Streamlit app)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def generate_cover_letter(
    resume_text: str,
    job_description: str,
    company_name: str = "",
    hiring_manager: str = "",
    role: str = "",
) -> str:
    """Convenience function: generate a cover letter.

    Args:
        resume_text: Full resume text.
        job_description: Target job description.
        company_name: Hiring company name (optional).
        hiring_manager: Hiring manager's name (optional).
        role: Target job title (optional).
    """
    gen = CoverLetterGenerator()
    return gen.generate(
        resume_text=resume_text,
        job_description=job_description,
        company_name=company_name,
        hiring_manager=hiring_manager,
        role=role,
    )


def generate_linkedin_summary(resume_text: str) -> str:
    """Convenience function: generate a LinkedIn summary."""
    gen = LinkedInSummaryGenerator()
    return gen.generate(resume_text)


def translate_resume(resume_text: str, target_language: str) -> str:
    """Convenience function: translate a resume."""
    ml = MultilingualResume()
    return ml.translate(resume_text, target_language)
