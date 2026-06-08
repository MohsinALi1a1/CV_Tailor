"""
Tests for the ATS Optimizer module.
These tests do NOT require API keys.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.ats_optimizer import ATSOptimizer, ATSReport


class TestATSOptimizer:
    """Tests for the ATSOptimizer class."""

    def test_analyse_basic(self, sample_resume_text):
        optimizer = ATSOptimizer()
        report = optimizer.analyse(sample_resume_text)
        assert isinstance(report, ATSReport)
        assert 0 <= report.overall_score <= 100
        assert report.total_words > 0

    def test_analyse_with_jd(self, sample_resume_text, sample_job_description):
        optimizer = ATSOptimizer()
        report = optimizer.analyse(sample_resume_text, sample_job_description)
        assert report.keyword_score > 0
        assert isinstance(report.suggestions, list)

    def test_analyse_empty_resume(self):
        optimizer = ATSOptimizer()
        report = optimizer.analyse("Just a name and nothing else.")
        assert report.overall_score < 50

    def test_score_breakdown_sums(self, sample_resume_text):
        optimizer = ATSOptimizer()
        report = optimizer.analyse(sample_resume_text)
        expected_total = (
            report.section_score
            + report.keyword_score
            + report.formatting_score
            + report.bullet_quality_score
            + report.length_score
        )
        assert abs(report.overall_score - expected_total) < 0.1

    def test_report_to_dict(self, sample_resume_text):
        optimizer = ATSOptimizer()
        report = optimizer.analyse(sample_resume_text)
        d = report.to_dict()
        assert "overall_score" in d
        assert "breakdown" in d
        assert "suggestions" in d
        assert "stats" in d

    def test_report_summary_text(self, sample_resume_text):
        optimizer = ATSOptimizer()
        report = optimizer.analyse(sample_resume_text)
        text = report.summary_text()
        assert "ATS COMPATIBILITY SCORE" in text

    def test_analyse_from_data(self, sample_resume_data):
        optimizer = ATSOptimizer()
        report = optimizer.analyse_from_data(sample_resume_data)
        assert report.overall_score > 0
        assert report.total_words > 0

    def test_formatting_issues_detection(self):
        bad_resume = "Name: John\nSkills: | Python | Java | SQL |\nimage.png attached"
        optimizer = ATSOptimizer()
        report = optimizer.analyse(bad_resume)
        assert len(report.formatting_issues) > 0

    def test_missing_sections(self):
        minimal = "John Doe\nPython developer with 5 years experience."
        optimizer = ATSOptimizer()
        report = optimizer.analyse(minimal)
        assert len(report.sections_missing) > 0


class TestATSScoring:
    """Tests for specific scoring components."""

    def test_good_resume_scores_high(self, sample_resume_text):
        optimizer = ATSOptimizer()
        report = optimizer.analyse(sample_resume_text)
        assert report.overall_score >= 40

    def test_section_score_max_25(self, sample_resume_text):
        optimizer = ATSOptimizer()
        report = optimizer.analyse(sample_resume_text)
        assert report.section_score <= 25

    def test_formatting_score_max_20(self, sample_resume_text):
        optimizer = ATSOptimizer()
        report = optimizer.analyse(sample_resume_text)
        assert report.formatting_score <= 20

    def test_bullet_score_max_20(self, sample_resume_text):
        optimizer = ATSOptimizer()
        report = optimizer.analyse(sample_resume_text)
        assert report.bullet_quality_score <= 20

    def test_length_score_max_10(self, sample_resume_text):
        optimizer = ATSOptimizer()
        report = optimizer.analyse(sample_resume_text)
        assert report.length_score <= 10
