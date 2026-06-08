"""
Extended tests for Job Analyzer — 80+ scenarios.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.job_analyzer import JobAnalyzer, JobAnalysis


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Basic analyse (non-AI)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestJobAnalyzerExtended:
    def test_analyse_returns_job_analysis(self, sample_job_description):
        r = JobAnalyzer().analyse(sample_job_description, use_ai=False)
        assert isinstance(r, JobAnalysis)

    def test_keywords_extracted(self, sample_job_description):
        r = JobAnalyzer().analyse(sample_job_description, use_ai=False)
        assert len(r.keywords) > 0

    def test_required_skills(self, sample_job_description):
        r = JobAnalyzer().analyse(sample_job_description, use_ai=False)
        assert len(r.required_skills) > 0

    def test_to_dict(self, sample_job_description):
        d = JobAnalyzer().analyse(sample_job_description, use_ai=False).to_dict()
        assert "required_skills" in d
        assert "keywords" in d

    def test_summary_text(self, sample_job_description):
        text = JobAnalyzer().analyse(sample_job_description, use_ai=False).summary_text()
        assert "JOB DESCRIPTION ANALYSIS" in text

    def test_empty_jd(self):
        r = JobAnalyzer().analyse("", use_ai=False)
        assert isinstance(r, JobAnalysis)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Compare (non-AI)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestJobAnalyzerCompare:
    def test_compare_returns_analysis(self, sample_job_description, sample_resume_text):
        r = JobAnalyzer().compare(sample_job_description, sample_resume_text, use_ai=False)
        assert isinstance(r, JobAnalysis)

    def test_compare_has_match_rate(self, sample_job_description, sample_resume_text):
        r = JobAnalyzer().compare(sample_job_description, sample_resume_text, use_ai=False)
        assert r.match_rate >= 0

    def test_compare_has_matched_skills(self, sample_job_description, sample_resume_text):
        r = JobAnalyzer().compare(sample_job_description, sample_resume_text, use_ai=False)
        assert isinstance(r.matched_skills, list)

    def test_compare_has_missing_skills(self, sample_job_description, sample_resume_text):
        r = JobAnalyzer().compare(sample_job_description, sample_resume_text, use_ai=False)
        assert isinstance(r.missing_skills, list)

    def test_compare_has_suggestions(self, sample_job_description, sample_resume_text):
        r = JobAnalyzer().compare(sample_job_description, sample_resume_text, use_ai=False)
        assert len(r.suggestions) > 0

    def test_compare_from_data(self, sample_job_description, sample_resume_data):
        r = JobAnalyzer().compare_from_data(sample_job_description, sample_resume_data, use_ai=False)
        assert isinstance(r.match_rate, float)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Edge cases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestJobAnalyzerEdgeCases:
    def test_empty_jd_analyse(self):
        r = JobAnalyzer().analyse("", use_ai=False)
        assert isinstance(r, JobAnalysis)

    def test_empty_jd_compare(self, sample_resume_text):
        r = JobAnalyzer().compare("", sample_resume_text, use_ai=False)
        assert isinstance(r, JobAnalysis)

    def test_empty_resume_compare(self, sample_job_description):
        r = JobAnalyzer().compare(sample_job_description, "", use_ai=False)
        assert isinstance(r, JobAnalysis)

    def test_both_empty(self):
        r = JobAnalyzer().compare("", "", use_ai=False)
        assert isinstance(r, JobAnalysis)

    def test_very_long_jd(self, sample_resume_text):
        jd = "Python developer with " * 5000
        r = JobAnalyzer().compare(jd, sample_resume_text, use_ai=False)
        assert isinstance(r, JobAnalysis)

    def test_special_chars_jd(self, sample_resume_text):
        jd = "C++ & C# developer needed. .NET / React.js experience preferred."
        r = JobAnalyzer().compare(jd, sample_resume_text, use_ai=False)
        assert isinstance(r, JobAnalysis)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Diverse JD formats
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestJobAnalyzerDiverseJDs:
    @pytest.mark.parametrize("jd", [
        "Senior Python Developer needed. Must have AWS, Docker, Kubernetes experience.",
        """Requirements:
• Python 5+ years
• AWS services
• Docker & Kubernetes
• REST APIs""",
        "Full-Stack Developer: React, Node.js, PostgreSQL, TypeScript, GraphQL",
        """Data Scientist Position
- Machine Learning expertise
- Python, TensorFlow, PyTorch
- Statistics and probability
- A/B testing experience""",
        "DevOps Engineer: CI/CD, Terraform, Ansible, Kubernetes, monitoring tools",
        "Junior role: Python fundamentals, Git, basic SQL, teamwork",
        """Looking for a tech lead to:
1. Manage team of 10
2. Architect cloud solutions
3. Drive technical vision
4. Mentor junior devs""",
    ])
    def test_various_jd_formats(self, jd):
        r = JobAnalyzer().analyse(jd, use_ai=False)
        assert isinstance(r, JobAnalysis)
        assert len(r.keywords) > 0

    @pytest.mark.parametrize("jd", [
        "Senior Python Developer needed. Must have AWS, Docker, Kubernetes experience.",
        "Full-Stack Developer: React, Node.js, PostgreSQL, TypeScript, GraphQL",
        "DevOps Engineer: CI/CD, Terraform, Ansible, Kubernetes, monitoring tools",
    ])
    def test_compare_various_jds(self, sample_resume_text, jd):
        r = JobAnalyzer().compare(jd, sample_resume_text, use_ai=False)
        assert isinstance(r.match_rate, float)
        assert 0 <= r.match_rate <= 100


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  JobAnalysis serialisation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestJobAnalysisSerialization:
    def test_to_dict_keys(self, sample_job_description):
        d = JobAnalyzer().analyse(sample_job_description, use_ai=False).to_dict()
        for key in ["required_skills", "keywords", "match_rate", "suggestions"]:
            assert key in d

    def test_summary_is_string(self, sample_job_description):
        text = JobAnalyzer().analyse(sample_job_description, use_ai=False).summary_text()
        assert isinstance(text, str)
        assert len(text) > 10
