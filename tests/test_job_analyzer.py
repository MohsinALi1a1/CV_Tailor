"""
Tests for the Job Analyzer module.
Non-AI tests only (basic NLP mode).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.job_analyzer import JobAnalyzer, JobAnalysis


class TestJobAnalyzer:
    """Tests for the JobAnalyzer class."""

    def test_analyse_basic(self, sample_job_description):
        analyzer = JobAnalyzer()
        analysis = analyzer.analyse(sample_job_description, use_ai=False)
        assert isinstance(analysis, JobAnalysis)
        assert len(analysis.keywords) > 0
        assert len(analysis.required_skills) > 0

    def test_compare_basic(self, sample_job_description, sample_resume_text):
        analyzer = JobAnalyzer()
        analysis = analyzer.compare(sample_job_description, sample_resume_text, use_ai=False)
        assert analysis.match_rate >= 0
        assert isinstance(analysis.matched_skills, list)
        assert isinstance(analysis.missing_skills, list)
        assert len(analysis.suggestions) > 0

    def test_analysis_to_dict(self, sample_job_description):
        analyzer = JobAnalyzer()
        analysis = analyzer.analyse(sample_job_description, use_ai=False)
        d = analysis.to_dict()
        assert "required_skills" in d
        assert "keywords" in d
        assert "match_rate" in d

    def test_analysis_summary_text(self, sample_job_description):
        analyzer = JobAnalyzer()
        analysis = analyzer.analyse(sample_job_description, use_ai=False)
        text = analysis.summary_text()
        assert "JOB DESCRIPTION ANALYSIS" in text

    def test_compare_from_data(self, sample_job_description, sample_resume_data):
        analyzer = JobAnalyzer()
        analysis = analyzer.compare_from_data(
            sample_job_description, sample_resume_data, use_ai=False
        )
        assert isinstance(analysis.match_rate, float)

    def test_empty_jd(self):
        analyzer = JobAnalyzer()
        analysis = analyzer.analyse("", use_ai=False)
        assert isinstance(analysis, JobAnalysis)
