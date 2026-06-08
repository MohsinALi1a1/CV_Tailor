"""
Tests for the Resume Tailor module.
Non-AI tests only (basic mode).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.resume_tailor import ResumeTailor


class TestResumeTailorBasic:
    """Tests for basic (non-AI) tailoring."""

    def test_basic_tailor(self, sample_resume_text, sample_job_description):
        tailor = ResumeTailor()
        result = tailor.tailor(sample_resume_text, sample_job_description, use_ai=False)
        assert "tailored_resume" in result
        assert "keyword_report" in result
        assert "suggestions" in result
        assert isinstance(result["tailored_resume"], str)
        assert len(result["tailored_resume"]) > 0

    def test_keyword_report_structure(self, sample_resume_text, sample_job_description):
        tailor = ResumeTailor()
        result = tailor.tailor(sample_resume_text, sample_job_description, use_ai=False)
        report = result["keyword_report"]
        assert "matched" in report
        assert "missing" in report
        assert "match_rate" in report
        assert isinstance(report["match_rate"], float)

    def test_suggestions_are_generated(self, sample_resume_text, sample_job_description):
        tailor = ResumeTailor()
        result = tailor.tailor(sample_resume_text, sample_job_description, use_ai=False)
        assert len(result["suggestions"]) > 0

    def test_tailor_from_data(self, sample_resume_data, sample_job_description):
        tailor = ResumeTailor()
        result = tailor.tailor_from_data(
            sample_resume_data, sample_job_description, use_ai=False
        )
        assert "tailored_resume" in result
        assert len(result["tailored_resume"]) > 0


class TestResumeTailorEdgeCases:
    """Edge case tests for the tailor."""

    def test_empty_resume(self, sample_job_description):
        tailor = ResumeTailor()
        result = tailor.tailor("", sample_job_description, use_ai=False)
        assert isinstance(result["tailored_resume"], str)

    def test_empty_jd(self, sample_resume_text):
        tailor = ResumeTailor()
        result = tailor.tailor(sample_resume_text, "", use_ai=False)
        assert isinstance(result["tailored_resume"], str)
