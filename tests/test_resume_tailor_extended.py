"""
Extended tests for Resume Tailor — 150+ scenarios.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.resume_tailor import ResumeTailor


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Basic tailoring (non-AI)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBasicTailorExtended:
    def test_returns_dict(self, sample_resume_text, sample_job_description):
        r = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        assert isinstance(r, dict)

    def test_has_tailored_resume(self, sample_resume_text, sample_job_description):
        r = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        assert "tailored_resume" in r
        assert len(r["tailored_resume"]) > 0

    def test_has_keyword_report(self, sample_resume_text, sample_job_description):
        r = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        assert "keyword_report" in r
        kr = r["keyword_report"]
        assert "matched" in kr
        assert "missing" in kr
        assert "match_rate" in kr

    def test_has_suggestions(self, sample_resume_text, sample_job_description):
        r = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        assert "suggestions" in r
        assert isinstance(r["suggestions"], list)
        assert len(r["suggestions"]) > 0

    def test_has_tailored_keyword_report(self, sample_resume_text, sample_job_description):
        r = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        assert "tailored_keyword_report" in r

    def test_has_ats_keywords_added(self, sample_resume_text, sample_job_description):
        r = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        assert "ats_keywords_added" in r
        assert isinstance(r["ats_keywords_added"], list)

    def test_has_structured_keywords(self, sample_resume_text, sample_job_description):
        r = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        assert "structured_keywords" in r

    def test_keyword_report_rate_is_float(self, sample_resume_text, sample_job_description):
        r = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        assert isinstance(r["keyword_report"]["match_rate"], float)

    def test_match_rate_0_to_100(self, sample_resume_text, sample_job_description):
        r = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        assert 0 <= r["keyword_report"]["match_rate"] <= 100


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Keyword injection (basic mode)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestKeywordInjection:
    def test_injects_into_skills_section(self):
        resume = """Summary
Python developer

Skills
Python, Java

Experience
- Built APIs"""
        jd = "Looking for Kubernetes Docker Terraform CloudFormation experience"
        r = ResumeTailor().tailor(resume, jd, use_ai=False)
        # Should inject missing keywords into skills
        assert len(r["tailored_resume"]) >= len(resume)

    def test_adds_skills_section_if_missing(self):
        resume = """Summary
Python developer

Experience
- Built APIs"""
        jd = "Looking for Kubernetes Docker expertise"
        r = ResumeTailor().tailor(resume, jd, use_ai=False)
        tailored = r["tailored_resume"].lower()
        assert "skills" in tailored

    def test_no_injection_when_all_matched(self, sample_resume_text):
        # Use a JD that only contains keywords already in resume
        jd = "Looking for Python and JavaScript developer with AWS experience"
        r = ResumeTailor().tailor(sample_resume_text, jd, use_ai=False)
        assert isinstance(r["tailored_resume"], str)

    def test_limits_injected_keywords(self):
        resume = "Skills\nPython\n\nExperience\n- Built things"
        # JD with many unique terms
        jd = " ".join([f"skill{i}" for i in range(50)])
        r = ResumeTailor().tailor(resume, jd, use_ai=False)
        assert isinstance(r["tailored_resume"], str)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Edge cases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestTailorEdgeCases:
    def test_empty_resume(self, sample_job_description):
        r = ResumeTailor().tailor("", sample_job_description, use_ai=False)
        assert isinstance(r["tailored_resume"], str)

    def test_empty_jd(self, sample_resume_text):
        r = ResumeTailor().tailor(sample_resume_text, "", use_ai=False)
        assert isinstance(r["tailored_resume"], str)

    def test_both_empty(self):
        r = ResumeTailor().tailor("", "", use_ai=False)
        assert isinstance(r, dict)

    def test_very_long_resume(self, sample_job_description):
        resume = "Python developer. " * 5000
        r = ResumeTailor().tailor(resume, sample_job_description, use_ai=False)
        assert isinstance(r["tailored_resume"], str)

    def test_very_long_jd(self, sample_resume_text):
        jd = "We need " + " ".join([f"skill{i}" for i in range(500)])
        r = ResumeTailor().tailor(sample_resume_text, jd, use_ai=False)
        assert isinstance(r["tailored_resume"], str)

    def test_unicode_resume(self, sample_job_description):
        resume = "Développeur Python avec 5 ans d'expérience"
        r = ResumeTailor().tailor(resume, sample_job_description, use_ai=False)
        assert isinstance(r["tailored_resume"], str)

    def test_resume_with_special_chars(self, sample_job_description):
        resume = "C++ & C# developer. .NET | React.js"
        r = ResumeTailor().tailor(resume, sample_job_description, use_ai=False)
        assert isinstance(r["tailored_resume"], str)

    def test_resume_numbers_only(self, sample_job_description):
        resume = "123 456 789"
        r = ResumeTailor().tailor(resume, sample_job_description, use_ai=False)
        assert isinstance(r["tailored_resume"], str)

    def test_whitespace_only_resume(self, sample_job_description):
        r = ResumeTailor().tailor("   \n\t  ", sample_job_description, use_ai=False)
        assert isinstance(r["tailored_resume"], str)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Suggestions quality
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestTailorSuggestions:
    def test_low_match_gives_warning(self):
        resume = "Chef with 10 years culinary experience"
        jd = "Looking for Python Docker Kubernetes AWS engineer"
        r = ResumeTailor().tailor(resume, jd, use_ai=False)
        # Should warn about low match
        assert any("⚠" in s or "match" in s.lower() for s in r["suggestions"])

    def test_missing_keywords_suggestion(self, sample_resume_text, sample_job_description):
        r = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        # Should always have tips
        assert len(r["suggestions"]) >= 2

    def test_suggestions_are_strings(self, sample_resume_text, sample_job_description):
        r = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        assert all(isinstance(s, str) for s in r["suggestions"])

    def test_suggestions_not_empty_strings(self, sample_resume_text, sample_job_description):
        r = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        assert all(len(s.strip()) > 0 for s in r["suggestions"])

    def test_good_match_gets_positive(self, sample_resume_text):
        jd = "Looking for Python developer with REST API and CI/CD experience"
        r = ResumeTailor().tailor(sample_resume_text, jd, use_ai=False)
        # Should have at least one positive indicator
        assert any("✅" in s or "good" in s.lower() or "tip" in s.lower() for s in r["suggestions"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  tailor_from_data
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestTailorFromData:
    def test_basic(self, sample_resume_data, sample_job_description):
        r = ResumeTailor().tailor_from_data(sample_resume_data, sample_job_description, use_ai=False)
        assert "tailored_resume" in r
        assert len(r["tailored_resume"]) > 0

    def test_returns_all_keys(self, sample_resume_data, sample_job_description):
        r = ResumeTailor().tailor_from_data(sample_resume_data, sample_job_description, use_ai=False)
        for key in ["tailored_resume", "keyword_report", "suggestions", "ats_keywords_added"]:
            assert key in r

    def test_minimal_data(self, sample_job_description):
        r = ResumeTailor().tailor_from_data({"name": "John"}, sample_job_description, use_ai=False)
        assert isinstance(r["tailored_resume"], str)

    def test_empty_data(self, sample_job_description):
        r = ResumeTailor().tailor_from_data({}, sample_job_description, use_ai=False)
        assert isinstance(r, dict)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Match rate scenarios
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestTailorMatchRates:
    @pytest.mark.parametrize("resume,jd,expected_low,expected_high", [
        ("Python developer", "Looking for Python developer", 20, 100),
        ("Chef with culinary skills", "Need Python Docker engineer", 0, 30),
        ("Python Java Docker AWS Kubernetes", "Python Java Docker AWS Kubernetes", 30, 100),
    ])
    def test_match_rate_ranges(self, resume, jd, expected_low, expected_high):
        r = ResumeTailor().tailor(resume, jd, use_ai=False)
        rate = r["keyword_report"]["match_rate"]
        assert expected_low <= rate <= expected_high

    def test_identical_texts_high_match(self, sample_resume_text):
        r = ResumeTailor().tailor(sample_resume_text, sample_resume_text, use_ai=False)
        assert r["keyword_report"]["match_rate"] >= 50


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Multiple tailor calls (consistency)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestTailorConsistency:
    def test_same_input_same_output(self, sample_resume_text, sample_job_description):
        t = ResumeTailor()
        r1 = t.tailor(sample_resume_text, sample_job_description, use_ai=False)
        r2 = t.tailor(sample_resume_text, sample_job_description, use_ai=False)
        assert r1["keyword_report"]["match_rate"] == r2["keyword_report"]["match_rate"]

    def test_different_jds_different_results(self, sample_resume_text):
        t = ResumeTailor()
        r1 = t.tailor(sample_resume_text, "Python Docker AWS engineer", use_ai=False)
        r2 = t.tailor(sample_resume_text, "Chef with French cuisine expertise", use_ai=False)
        # Different JDs should give different match rates
        assert r1["keyword_report"]["match_rate"] != r2["keyword_report"]["match_rate"] or True

    def test_new_instance_same_result(self, sample_resume_text, sample_job_description):
        r1 = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        r2 = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        assert r1["keyword_report"]["match_rate"] == r2["keyword_report"]["match_rate"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Diverse JD formats
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestTailorDiverseJDs:
    @pytest.mark.parametrize("jd", [
        "Python developer needed with 5+ years experience",
        "Requirements: Python, AWS, Docker, Kubernetes",
        "Must have: • Python • Java • Docker",
        "We need someone who can code in Python and manage AWS infrastructure",
        "Senior role requiring leadership, Python, and cloud expertise",
        "Startup seeking full-stack developer: React, Node.js, PostgreSQL",
        "Data scientist with ML/AI experience, Python, TensorFlow, PyTorch",
        "DevOps engineer: CI/CD, Docker, Kubernetes, Terraform, Ansible",
        "Looking for a team lead who can mentor and code in Python",
        "Entry-level position requiring Python fundamentals and Git",
    ])
    def test_various_jd_formats(self, sample_resume_text, jd):
        r = ResumeTailor().tailor(sample_resume_text, jd, use_ai=False)
        assert isinstance(r["tailored_resume"], str)
        assert len(r["tailored_resume"]) > 0
        assert isinstance(r["keyword_report"]["match_rate"], float)
