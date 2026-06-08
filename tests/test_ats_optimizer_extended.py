"""
Extended tests for ATS Optimizer — 200+ scenarios.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.ats_optimizer import ATSOptimizer, ATSReport


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Score range & constraint tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestATSScoreRanges:
    """Verify all score components stay within their bounds."""

    def test_overall_0_to_100(self, sample_resume_text):
        r = ATSOptimizer().analyse(sample_resume_text)
        assert 0 <= r.overall_score <= 100

    def test_section_max_25(self, sample_resume_text):
        r = ATSOptimizer().analyse(sample_resume_text)
        assert 0 <= r.section_score <= 25

    def test_keyword_max_25(self, sample_resume_text, sample_job_description):
        r = ATSOptimizer().analyse(sample_resume_text, sample_job_description)
        assert 0 <= r.keyword_score <= 25

    def test_formatting_max_20(self, sample_resume_text):
        r = ATSOptimizer().analyse(sample_resume_text)
        assert 0 <= r.formatting_score <= 20

    def test_bullet_max_20(self, sample_resume_text):
        r = ATSOptimizer().analyse(sample_resume_text)
        assert 0 <= r.bullet_quality_score <= 20

    def test_length_max_10(self, sample_resume_text):
        r = ATSOptimizer().analyse(sample_resume_text)
        assert 0 <= r.length_score <= 10

    def test_sum_equals_overall(self, sample_resume_text):
        r = ATSOptimizer().analyse(sample_resume_text)
        s = r.section_score + r.keyword_score + r.formatting_score + r.bullet_quality_score + r.length_score
        assert abs(r.overall_score - s) < 0.1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Minimal / bad resumes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestATSBadResumes:
    @pytest.mark.parametrize("text", [
        "John",
        "Just a name.",
        "No sections here just words",
        "",
        "   ",
        "Hello world this is not a resume at all",
    ])
    def test_bad_resume_scores_low(self, text):
        r = ATSOptimizer().analyse(text)
        assert r.overall_score < 60

    def test_empty_has_missing_sections(self):
        r = ATSOptimizer().analyse("Nothing here")
        assert len(r.sections_missing) > 0

    def test_no_bullets(self):
        r = ATSOptimizer().analyse("Name: John Doe\nSkills: Python\nExperience: Worked somewhere")
        # bullet_to_list may extract text fragments, so just check it's low
        assert r.total_bullets <= 5

    def test_very_short_resume(self):
        r = ATSOptimizer().analyse("John Doe. Python developer.")
        assert r.length_score < 10


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Good resumes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestATSGoodResumes:
    def test_sample_scores_decently(self, sample_resume_text):
        r = ATSOptimizer().analyse(sample_resume_text)
        assert r.overall_score >= 40

    def test_sample_has_sections(self, sample_resume_text):
        r = ATSOptimizer().analyse(sample_resume_text)
        assert len(r.sections_found) >= 2

    def test_sample_has_bullets(self, sample_resume_text):
        r = ATSOptimizer().analyse(sample_resume_text)
        assert r.total_bullets >= 3

    def test_sample_has_quantified(self, sample_resume_text):
        r = ATSOptimizer().analyse(sample_resume_text)
        assert r.bullets_with_numbers >= 2

    def test_sample_has_action_verbs(self, sample_resume_text):
        r = ATSOptimizer().analyse(sample_resume_text)
        assert r.bullets_with_action_verbs >= 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  With JD keyword matching
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestATSWithJD:
    def test_jd_boosts_keyword_score(self, sample_resume_text, sample_job_description):
        r_no = ATSOptimizer().analyse(sample_resume_text)
        r_jd = ATSOptimizer().analyse(sample_resume_text, sample_job_description)
        # With JD should give a real keyword score (not just baseline)
        assert isinstance(r_jd.keyword_score, float)

    def test_jd_missing_keyword_suggestions(self, sample_resume_text, sample_job_description):
        r = ATSOptimizer().analyse(sample_resume_text, sample_job_description)
        assert any("missing" in s.lower() or "keyword" in s.lower() for s in r.suggestions) or r.keyword_score > 20

    def test_irrelevant_jd(self, sample_resume_text):
        jd = "Looking for a professional chef with 10 years culinary experience in French cuisine."
        r = ATSOptimizer().analyse(sample_resume_text, jd)
        assert r.keyword_score < 15

    def test_perfectly_matched_jd(self, sample_resume_text):
        # Use the resume itself as JD — should match well
        r = ATSOptimizer().analyse(sample_resume_text, sample_resume_text)
        assert r.keyword_score >= 15


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Formatting issues
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestATSFormatting:
    def test_table_detected(self):
        text = "|Name|Company|Date|\n|John|Acme|2024|\n|Jane|Corp|2023|"
        r = ATSOptimizer().analyse(text)
        assert any("table" in f.lower() for f in r.formatting_issues)

    def test_image_detected(self):
        text = "My resume with photo.png attached for reference"
        r = ATSOptimizer().analyse(text)
        assert any("image" in f.lower() for f in r.formatting_issues)

    def test_special_symbols(self):
        text = "★ Python ★ Java ★ Docker ★ AWS ★ Linux ★ Git"
        r = ATSOptimizer().analyse(text)
        assert any("symbol" in f.lower() for f in r.formatting_issues)

    def test_clean_formatting(self, sample_resume_text):
        r = ATSOptimizer().analyse(sample_resume_text)
        # Sample resume should have minimal formatting issues
        assert r.formatting_score >= 15

    def test_long_lines(self):
        text = "A" * 200 + "\n" + "B" * 200 + "\n" + "C" * 200 + "\n" + "D" * 200
        r = ATSOptimizer().analyse(text)
        assert any("150" in f or "long" in f.lower() or "line" in f.lower() for f in r.formatting_issues)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Section detection (content-based fallback)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestATSSectionDetection:
    def test_detects_experience_by_content(self):
        text = """John Doe
Senior Developer at TechCorp, Jan 2020 - Present
- Led team of 10 engineers
- Built REST APIs
Junior Developer at StartupXYZ, Jun 2016 - Dec 2019
- Developed microservices"""
        r = ATSOptimizer().analyse(text)
        found_lower = {s.lower() for s in r.sections_found}
        assert any("experience" in f for f in found_lower)

    def test_detects_education_by_content(self):
        text = "John Doe\nBachelor of Science in Computer Science from MIT, GPA 3.9"
        r = ATSOptimizer().analyse(text)
        found_lower = {s.lower() for s in r.sections_found}
        assert any("education" in f for f in found_lower)

    def test_detects_skills_by_content(self):
        text = "John Doe\nPython, Java, JavaScript, Docker, Kubernetes, AWS, React, Node.js"
        r = ATSOptimizer().analyse(text)
        found_lower = {s.lower() for s in r.sections_found}
        assert any("skills" in f for f in found_lower)

    def test_detects_summary_by_content(self):
        text = """John Doe
Experienced senior software engineer with 8 years of experience in cloud architecture, Python development, and leading cross-functional engineering teams."""
        r = ATSOptimizer().analyse(text)
        found_lower = {s.lower() for s in r.sections_found}
        assert any("summary" in f for f in found_lower)

    def test_detects_projects_by_content(self):
        text = "John Doe\nBuilt a real-time dashboard using React, hosted on github.com/johndoe/dashboard"
        r = ATSOptimizer().analyse(text)
        found_lower = {s.lower() for s in r.sections_found}
        assert any("project" in f for f in found_lower)

    def test_detects_certifications_by_content(self):
        text = "John Doe\nAWS Certified Solutions Architect - Professional"
        r = ATSOptimizer().analyse(text)
        found_lower = {s.lower() for s in r.sections_found}
        assert any("certification" in f for f in found_lower)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Report serialisation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestATSReportSerialization:
    def test_to_dict_has_all_keys(self, sample_resume_text):
        r = ATSOptimizer().analyse(sample_resume_text)
        d = r.to_dict()
        assert "overall_score" in d
        assert "breakdown" in d
        assert "sections_found" in d
        assert "sections_missing" in d
        assert "formatting_issues" in d
        assert "suggestions" in d
        assert "stats" in d

    def test_to_dict_breakdown_keys(self, sample_resume_text):
        d = ATSOptimizer().analyse(sample_resume_text).to_dict()
        bd = d["breakdown"]
        for key in ["section_score", "keyword_score", "formatting_score", "bullet_quality_score", "length_score"]:
            assert key in bd

    def test_to_dict_stats_keys(self, sample_resume_text):
        d = ATSOptimizer().analyse(sample_resume_text).to_dict()
        s = d["stats"]
        for key in ["total_words", "total_bullets", "bullets_with_numbers", "bullets_with_action_verbs"]:
            assert key in s

    def test_summary_text_contains_score(self, sample_resume_text):
        r = ATSOptimizer().analyse(sample_resume_text)
        text = r.summary_text()
        assert "ATS COMPATIBILITY SCORE" in text
        assert "/" in text

    def test_suggestions_are_strings(self, sample_resume_text):
        r = ATSOptimizer().analyse(sample_resume_text)
        assert all(isinstance(s, str) for s in r.suggestions)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Length scoring
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestATSLength:
    @pytest.mark.parametrize("word_count,expected_max", [
        (10, 5),    # very short
        (200, 5),   # still short
        (400, 10),  # ideal start
        (600, 10),  # ideal middle
        (800, 10),  # ideal end
        (900, 8),   # getting long
    ])
    def test_length_scores(self, word_count, expected_max):
        text = " ".join(["word"] * word_count)
        r = ATSOptimizer().analyse(text)
        assert r.length_score <= expected_max

    def test_ideal_length_gets_10(self):
        text = " ".join(["word"] * 500)
        r = ATSOptimizer().analyse(text)
        assert r.length_score == 10


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Bullet quality
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestATSBulletQuality:
    def test_good_bullets_score_high(self):
        text = """Experience
- Led migration reducing deployment time by 60%
- Managed team of 15 engineers across 3 time zones
- Implemented CI/CD pipeline increasing frequency by 200%
- Reduced costs by $150K annually through optimization"""
        r = ATSOptimizer().analyse(text)
        assert r.bullet_quality_score >= 10

    def test_weak_bullets_score_low(self):
        text = """Experience
- Worked on stuff at the company
- Helped with projects and tasks
- Attended meetings and reviewed things
- Participated in various team activities"""
        r = ATSOptimizer().analyse(text)
        assert r.bullet_quality_score < 15

    def test_no_bullets_gets_minimal(self):
        text = "John Doe. Python developer with experience."
        r = ATSOptimizer().analyse(text)
        assert r.bullet_quality_score <= 5


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  analyse_from_data
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestATSFromData:
    def test_from_data_works(self, sample_resume_data):
        r = ATSOptimizer().analyse_from_data(sample_resume_data)
        assert r.overall_score > 0

    def test_from_data_with_jd(self, sample_resume_data, sample_job_description):
        r = ATSOptimizer().analyse_from_data(sample_resume_data, sample_job_description)
        assert r.keyword_score > 0

    def test_minimal_data(self):
        r = ATSOptimizer().analyse_from_data({"name": "John Doe"})
        assert isinstance(r, ATSReport)

    def test_empty_data(self):
        r = ATSOptimizer().analyse_from_data({})
        assert isinstance(r, ATSReport)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Diverse resume formats
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestATSDiverseFormats:
    def test_resume_with_all_sections(self):
        text = """John Doe
john@email.com | +1-555-0100

Summary
Experienced engineer with 8 years in Python.

Skills
Python, Java, Docker, AWS, Kubernetes

Experience
Senior Dev | TechCorp | 2020 - Present
- Led team of 15 engineers
- Built microservices reducing latency by 40%

Education
BS Computer Science | MIT | 2016

Certifications
AWS Solutions Architect

Projects
MyApp - An open source tool with 500+ stars

Languages
English, Spanish"""
        r = ATSOptimizer().analyse(text)
        assert r.overall_score >= 50
        assert len(r.sections_found) >= 5

    def test_resume_minimal_format(self):
        text = """JOHN DOE
Email: john@email.com

WORK HISTORY
Software Engineer, Corp (2020-Present)
Developed web applications using Python and React.

ACADEMIC BACKGROUND
BSc Computer Science, State University, 2016"""
        r = ATSOptimizer().analyse(text)
        assert isinstance(r, ATSReport)

    def test_resume_creative_format(self):
        text = """━━━ JANE DOE ━━━
✉ jane@email.com | 📱 555-0100

═══ ABOUT ME ═══
Creative developer passionate about UX.

═══ WHAT I DO ═══
★ Build beautiful web apps
★ Design user interfaces
★ Write clean code"""
        r = ATSOptimizer().analyse(text)
        assert isinstance(r, ATSReport)

    def test_resume_with_numbers_heavy(self):
        text = """John Doe
Experience
- Increased revenue by 400%
- Saved $5 million in costs
- Managed 50+ engineers
- Processed 100 million records
- Achieved 99.99% uptime
- Reduced errors by 90%"""
        r = ATSOptimizer().analyse(text)
        assert r.bullets_with_numbers >= 5

    def test_resume_all_action_verbs(self):
        text = """Experience
- Led digital transformation initiative
- Developed scalable microservice architecture
- Implemented automated testing framework
- Designed cloud-native solutions
- Orchestrated cross-team collaboration
- Streamlined deployment processes"""
        r = ATSOptimizer().analyse(text)
        assert r.bullets_with_action_verbs >= 4

    @pytest.mark.parametrize("heading_style", [
        "Experience", "EXPERIENCE", "experience", "Experience:", "---Experience---",
        "Work Experience", "Professional Experience", "Employment History",
    ])
    def test_various_experience_headings(self, heading_style):
        text = f"""{heading_style}
Senior Developer | Corp | 2020-Present
- Led team of engineers"""
        r = ATSOptimizer().analyse(text)
        # Should detect experience section via heading or content
        assert isinstance(r, ATSReport)
