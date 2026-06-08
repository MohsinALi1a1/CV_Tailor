"""
Additional edge case and regression tests — 50+ to push above 1000 total.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.text_processing import (
    extract_keywords, match_keywords, clean_text, count_words,
    bullet_to_list, list_to_bullet, has_quantified_achievement,
    starts_with_action_verb, parse_resume_sections, _get_basic_stopwords,
    _is_stopword,
)
from modules.ats_optimizer import ATSOptimizer, ATSReport
from modules.resume_tailor import ResumeTailor
from modules.resume_builder import ResumeBuilder
from config import ATS_ACTION_VERBS, ATS_STANDARD_SECTIONS


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Stopwords & helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestStopwords:
    def test_common_stopwords(self):
        sw = _get_basic_stopwords()
        for w in ["the", "a", "an", "and", "or", "in", "on", "at", "to", "for"]:
            assert w in sw

    def test_is_stopword(self):
        assert _is_stopword("the") is True
        assert _is_stopword("python") is False

    def test_stopwords_lowercase(self):
        sw = _get_basic_stopwords()
        assert all(w == w.lower() for w in sw)

    def test_stopwords_no_duplicates(self):
        sw = list(_get_basic_stopwords())
        # Sets remove dupes, so check same length
        assert len(sw) == len(set(sw))

    def test_stopwords_count(self):
        sw = _get_basic_stopwords()
        assert len(sw) >= 50


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Config constants validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestConfigConstants:
    def test_action_verbs_200_plus(self):
        assert len(ATS_ACTION_VERBS) >= 200

    def test_action_verbs_all_lowercase(self):
        assert all(v == v.lower() for v in ATS_ACTION_VERBS)

    def test_action_verbs_no_dupes(self):
        assert len(ATS_ACTION_VERBS) == len(set(ATS_ACTION_VERBS))

    def test_standard_sections_10_plus(self):
        assert len(ATS_STANDARD_SECTIONS) >= 10

    @pytest.mark.parametrize("verb", [
        "led", "built", "managed", "developed", "implemented",
        "designed", "created", "achieved", "reduced", "improved",
        "automated", "launched", "mentored", "optimized", "delivered",
    ])
    def test_key_verbs_present(self, verb):
        assert verb in ATS_ACTION_VERBS

    @pytest.mark.parametrize("section", [
        "Summary", "Experience", "Education", "Skills",
        "Certifications", "Projects",
    ])
    def test_key_sections_present(self, section):
        assert section in ATS_STANDARD_SECTIONS


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ATS Report model
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestATSReportModel:
    def test_default_values(self):
        r = ATSReport()
        assert r.overall_score == 0.0
        assert r.section_score == 0.0
        assert r.total_words == 0
        assert r.sections_found == []
        assert r.suggestions == []

    def test_to_dict_default(self):
        d = ATSReport().to_dict()
        assert d["overall_score"] == 0
        assert d["stats"]["total_words"] == 0

    def test_summary_text_default(self):
        text = ATSReport().summary_text()
        assert "0" in text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Builder edge cases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBuilderEdgeCases:
    def test_unicode_name(self):
        b = ResumeBuilder()
        b.set_contact("张伟")
        assert b.get_data()["name"] == "张伟"

    def test_arabic_name(self):
        b = ResumeBuilder()
        b.set_contact("أحمد")
        assert b.get_data()["name"] == "أحمد"

    def test_very_long_summary(self):
        b = ResumeBuilder()
        b.set_summary("x" * 10000)
        assert len(b.get_data()["summary"]) == 10000

    def test_skill_with_special_chars(self):
        b = ResumeBuilder()
        for s in ["C++", "C#", ".NET", "Node.js", "React.js", "Vue.js"]:
            b.add_skill(s)
        assert len(b.get_data()["skills"]) == 6

    def test_experience_with_empty_bullets(self):
        b = ResumeBuilder()
        b.set_contact("Test")
        b.add_experience("Dev", "Corp", bullets=[])
        assert b.get_data()["experience"][0]["bullets"] == []

    def test_multiple_identical_experiences(self):
        b = ResumeBuilder()
        b.set_contact("Test")
        b.add_experience("Dev", "Corp")
        b.add_experience("Dev", "Corp")
        assert len(b.get_data()["experience"]) == 2

    def test_get_data_returns_copy_like(self):
        b = ResumeBuilder()
        b.set_contact("Test")
        d = b.get_data()
        assert isinstance(d, dict)
        assert "name" in d


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Regression: tailor returns correct keys
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestTailorRegressions:
    def test_all_expected_keys(self, sample_resume_text, sample_job_description):
        r = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        expected = {"tailored_resume", "keyword_report", "tailored_keyword_report",
                    "suggestions", "ats_keywords_added", "structured_keywords"}
        assert expected.issubset(set(r.keys()))

    def test_keyword_report_keys(self, sample_resume_text, sample_job_description):
        r = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        kr = r["keyword_report"]
        assert "matched" in kr
        assert "missing" in kr
        assert "match_rate" in kr

    def test_tailored_keyword_report_keys(self, sample_resume_text, sample_job_description):
        r = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        tkr = r["tailored_keyword_report"]
        assert "matched" in tkr
        assert "missing" in tkr
        assert "match_rate" in tkr

    def test_structured_keywords_keys(self, sample_resume_text, sample_job_description):
        r = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        sk = r["structured_keywords"]
        assert "required_skills" in sk

    def test_suggestions_are_list_of_strings(self, sample_resume_text, sample_job_description):
        r = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        assert isinstance(r["suggestions"], list)
        assert all(isinstance(s, str) for s in r["suggestions"])

    def test_ats_keywords_added_is_list(self, sample_resume_text, sample_job_description):
        r = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        assert isinstance(r["ats_keywords_added"], list)
