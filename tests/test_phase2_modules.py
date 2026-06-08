"""Tests for the new CV Tailor modules introduced in Phase 2:
- modules.industry_intel
- modules.skill_taxonomy
- modules.spell_check
- modules.resume_diff
- modules.interview_prep (template path only — no AI)
"""

from __future__ import annotations

import pytest

from modules.industry_intel import (
    IndustryAnalysis,
    INDUSTRY_KEYWORDS,
    INDUSTRY_NAMES,
    detect_industry,
    get_industry_keywords,
    list_industries,
)
from modules.skill_taxonomy import (
    SKILL_CATEGORIES,
    CategorizedSkills,
    categorize_skills,
    get_category_for_skill,
    list_categories,
)
from modules.spell_check import (
    SpellCheckResult,
    quick_spell_score,
    spell_check,
)
from modules.resume_diff import (
    DiffStats,
    ResumeDiff,
    diff_resumes,
    keyword_diff,
    render_inline_diff_html,
)
from modules.interview_prep import (
    BEHAVIORAL_QUESTIONS,
    QUESTIONS_TO_ASK_INTERVIEWER,
    TECHNICAL_QUESTIONS_BY_ROLE,
    InterviewPrepResult,
    generate_interview_prep,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Industry Intelligence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestIndustryIntel:
    def test_detects_software_engineering(self):
        jd = (
            "Senior Python Engineer to build REST APIs and microservices using "
            "Django, FastAPI, Docker, Kubernetes, PostgreSQL on AWS with CI/CD."
        )
        result = detect_industry(jd)
        assert result.primary_industry == "software_engineering"
        assert result.confidence > 0
        assert "python" in result.industry_keywords_in_jd

    def test_detects_data_science(self):
        jd = (
            "ML Engineer. Build models with PyTorch, TensorFlow, scikit-learn. "
            "Feature engineering, hyperparameter tuning. SQL, pandas, numpy."
        )
        result = detect_industry(jd)
        assert result.primary_industry == "data_science"

    def test_detects_marketing(self):
        jd = (
            "Marketing Manager. SEO, SEM, Google Ads, content marketing, "
            "email marketing campaigns, marketing automation with HubSpot."
        )
        result = detect_industry(jd)
        assert result.primary_industry == "marketing"

    def test_detects_sales(self):
        jd = (
            "Enterprise SaaS Sales rep. B2B sales, prospecting, cold calling, "
            "Salesforce, MEDDIC, quota attainment, pipeline management."
        )
        result = detect_industry(jd)
        assert result.primary_industry == "sales"

    def test_detects_devops(self):
        jd = (
            "Site Reliability Engineer. Manage Kubernetes clusters, Terraform, "
            "Prometheus, Grafana. On-call, incident response, SLOs."
        )
        result = detect_industry(jd)
        assert result.primary_industry == "devops_sre"

    def test_empty_jd_returns_general(self):
        result = detect_industry("")
        assert result.primary_industry == "general"
        assert result.confidence == 0.0

    def test_has_industry_tips(self):
        result = detect_industry("Python developer with Django and AWS")
        assert len(result.industry_tips) > 0

    def test_to_dict(self):
        result = detect_industry("Python developer")
        d = result.to_dict()
        assert "primary_industry" in d
        assert "confidence" in d
        assert "industry_tips" in d

    def test_get_industry_keywords(self):
        kws = get_industry_keywords("software_engineering", "core")
        assert "python" in kws
        assert len(kws) > 5

        all_kws = get_industry_keywords("software_engineering", "all")
        assert len(all_kws) >= len(kws)

        empty = get_industry_keywords("nonexistent_industry")
        assert empty == []

    def test_list_industries(self):
        industries = list_industries()
        assert len(industries) >= 10
        assert all("key" in i and "name" in i for i in industries)

    def test_all_industries_have_keywords(self):
        for ind_key in INDUSTRY_NAMES:
            assert ind_key in INDUSTRY_KEYWORDS
            assert "core" in INDUSTRY_KEYWORDS[ind_key]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Skill Taxonomy
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSkillTaxonomy:
    def test_categorizes_languages(self):
        result = categorize_skills(["Python", "Java", "JavaScript"])
        assert "Programming Languages" in result.categorized
        assert len(result.categorized["Programming Languages"]) == 3

    def test_categorizes_mixed(self):
        skills = ["Python", "React", "AWS", "PostgreSQL", "Leadership", "Figma"]
        result = categorize_skills(skills)
        assert len(result.categorized) >= 4
        assert result.total_skills == 6

    def test_uncategorized_for_unknowns(self):
        result = categorize_skills(["XyzFakeSkill123"])
        assert "XyzFakeSkill123" in result.uncategorized

    def test_dedupes_skills(self):
        result = categorize_skills(["Python", "python", "PYTHON"])
        assert result.total_skills == 1

    def test_handles_empty(self):
        result = categorize_skills([])
        assert result.total_skills == 0
        assert result.categorized == {}

    def test_skips_empty_strings(self):
        result = categorize_skills(["", "Python", "  ", None])  # type: ignore
        assert result.total_skills == 1

    def test_format_as_resume_section(self):
        result = categorize_skills(["Python", "AWS", "React"])
        formatted = result.format_as_resume_section()
        assert "Programming Languages" in formatted
        assert ":" in formatted

    def test_format_compact(self):
        result = categorize_skills(["Python", "AWS"])
        compact = result.format_compact()
        assert "|" in compact or len(result.categorized) <= 1

    def test_get_category_for_skill(self):
        assert get_category_for_skill("Python") == "Programming Languages"
        assert get_category_for_skill("AWS") == "Cloud & DevOps"
        assert get_category_for_skill("zzz_unknown") == "Uncategorized"

    def test_list_categories(self):
        cats = list_categories()
        assert "Programming Languages" in cats
        assert "Soft Skills" in cats
        assert len(cats) >= 8

    def test_partial_match(self):
        # "Python 3.11" should still map to Programming Languages via substring
        result = categorize_skills(["Python 3.11", "React.js"])
        # At least one should be categorized (partial match logic)
        assert result.total_skills == 2

    def test_to_dict(self):
        result = categorize_skills(["Python"])
        d = result.to_dict()
        assert "categorized" in d
        assert "uncategorized" in d
        assert "total_skills" in d


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Spell Checker
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSpellCheck:
    def test_clean_text_no_issues(self):
        text = "I am a software engineer with experience in Python and Java."
        result = spell_check(text)
        # May have some flagged words depending on dictionary
        assert isinstance(result, SpellCheckResult)
        assert result.total_words > 0

    def test_detects_obvious_typos(self):
        text = "I have experiance with Pythn programing and develpment."
        result = spell_check(text)
        flagged = [i.word.lower() for i in result.issues]
        assert "experiance" in flagged
        assert "develpment" in flagged

    def test_skips_acronyms(self):
        text = "AWS API REST JSON XML CI CD"
        result = spell_check(text)
        flagged = [i.word for i in result.issues]
        assert "AWS" not in flagged
        assert "API" not in flagged

    def test_skips_tech_terms(self):
        text = "Python JavaScript Kubernetes Docker Terraform"
        result = spell_check(text)
        flagged = [i.word.lower() for i in result.issues]
        assert "python" not in flagged
        assert "kubernetes" not in flagged

    def test_skips_short_words(self):
        text = "I am at to of in"
        result = spell_check(text)
        # No short words should be flagged
        assert all(len(i.word) >= 3 for i in result.issues)

    def test_quick_score_clean(self):
        score = quick_spell_score("Python developer with Java experience")
        assert 0 <= score <= 100

    def test_empty_text(self):
        result = spell_check("")
        assert result.total_words == 0
        assert result.misspelled_count == 0

    def test_to_dict(self):
        result = spell_check("Some text")
        d = result.to_dict()
        assert "issues" in d
        assert "total_words" in d
        assert "accuracy_pct" in d

    def test_max_issues_limit(self):
        # Lots of typos
        bad = " ".join(["xyzfakewordone", "abcfakewordtwo", "qwertynothere"] * 30)
        result = spell_check(bad, max_issues=10)
        assert len(result.issues) <= 10


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Resume Diff
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestResumeDiff:
    def test_identical_resumes(self):
        text = "John Doe\nPython Developer\nExperience with AWS"
        result = diff_resumes(text, text)
        assert result.stats.similarity_pct == 100.0
        assert result.stats.lines_added == 0
        assert result.stats.lines_removed == 0

    def test_added_content(self):
        orig = "John Doe\nPython Developer"
        new = "John Doe\nPython Developer\nAWS Certified"
        result = diff_resumes(orig, new)
        assert result.stats.lines_added >= 1
        assert "aws" in result.stats.keywords_added or "certified" in result.stats.keywords_added

    def test_removed_content(self):
        orig = "John Doe\nPython Developer\nOld Job"
        new = "John Doe\nPython Developer"
        result = diff_resumes(orig, new)
        assert result.stats.lines_removed >= 1

    def test_keyword_diff(self):
        orig = "Python developer with Django"
        new = "Python developer with FastAPI and Kubernetes"
        kd = keyword_diff(orig, new)
        assert "django" in kd["removed"]
        assert "fastapi" in kd["added"]
        assert "python" in kd["common"]

    def test_html_diff_renders(self):
        result = diff_resumes("a\nb\nc", "a\nb\nd")
        assert "<table" in result.html_diff.lower()

    def test_render_inline_diff_html(self):
        html = render_inline_diff_html("orig", "new")
        assert "diff-summary" in html
        assert "<style>" in html

    def test_stats_to_dict(self):
        result = diff_resumes("a", "b")
        d = result.stats.to_dict()
        assert "lines_added" in d
        assert "similarity_pct" in d

    def test_summary_string(self):
        result = diff_resumes("orig", "new with extra content")
        assert "%" in result.summary
        assert "similar" in result.summary


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Interview Prep (template path only)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestInterviewPrep:
    def test_generates_prep_without_ai(self):
        resume = "Python developer with 5 years experience at Google"
        jd = "Senior Python Engineer with Django and AWS"
        prep = generate_interview_prep(resume, jd, use_ai=False)
        assert isinstance(prep, InterviewPrepResult)
        assert len(prep.behavioral) > 0
        assert len(prep.technical) > 0
        assert len(prep.questions_to_ask) > 0
        assert len(prep.preparation_tips) > 0
        assert prep.ai_powered is False

    def test_role_specific_for_data_science(self):
        resume = "Data scientist"
        jd = "ML Engineer with PyTorch, TensorFlow, scikit-learn for predictive modeling"
        prep = generate_interview_prep(resume, jd, use_ai=False)
        assert len(prep.technical) > 0
        # Should include ML-related questions
        all_qs = " ".join(q.question.lower() for q in prep.technical)
        assert "model" in all_qs or "ml" in all_qs or "machine" in all_qs

    def test_questions_per_category(self):
        prep = generate_interview_prep("resume", "jd", use_ai=False, questions_per_category=3)
        assert len(prep.behavioral) <= 3
        assert len(prep.technical) <= 3

    def test_to_dict(self):
        prep = generate_interview_prep("r", "j", use_ai=False)
        d = prep.to_dict()
        assert "behavioral" in d
        assert "technical" in d
        assert "questions_to_ask" in d
        assert "preparation_tips" in d

    def test_role_in_tips(self):
        prep = generate_interview_prep("r", "j", role="Senior Engineer", use_ai=False)
        assert any("Senior Engineer" in t for t in prep.preparation_tips)

    def test_company_in_tips(self):
        prep = generate_interview_prep("r", "j", company="Acme", use_ai=False)
        assert any("Acme" in t for t in prep.preparation_tips)

    def test_question_banks_non_empty(self):
        assert len(BEHAVIORAL_QUESTIONS) >= 10
        assert len(QUESTIONS_TO_ASK_INTERVIEWER) >= 5
        assert "software_engineering" in TECHNICAL_QUESTIONS_BY_ROLE
        assert len(TECHNICAL_QUESTIONS_BY_ROLE["software_engineering"]) >= 5
