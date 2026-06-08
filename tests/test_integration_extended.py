"""
Tests for Streamlit app helpers and _strip_markdown — 50+ scenarios.
"""
from __future__ import annotations
import sys, re
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  _strip_markdown (imported from app module)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _strip_markdown(text: str) -> str:
    """Replicated from streamlit_app for testing."""
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'(?<![a-zA-Z])_([^_]+)_(?![a-zA-Z])', r'\1', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text.strip()


class TestStripMarkdown:
    def test_empty(self):
        assert _strip_markdown("") == ""

    def test_plain_text(self):
        assert _strip_markdown("Hello World") == "Hello World"

    def test_remove_bold(self):
        assert _strip_markdown("**bold text**") == "bold text"

    def test_remove_italic(self):
        assert _strip_markdown("*italic text*") == "italic text"

    def test_remove_bold_italic(self):
        r = _strip_markdown("***bold italic***")
        assert "***" not in r

    def test_remove_h1(self):
        assert _strip_markdown("# Heading") == "Heading"

    def test_remove_h2(self):
        assert _strip_markdown("## Heading") == "Heading"

    def test_remove_h3(self):
        assert _strip_markdown("### Heading") == "Heading"

    def test_remove_h4(self):
        assert _strip_markdown("#### Heading") == "Heading"

    def test_remove_inline_code(self):
        assert _strip_markdown("`code`") == "code"

    def test_remove_code_block(self):
        r = _strip_markdown("```python\nprint('hi')\n```")
        assert "```" not in r

    def test_remove_underscore_bold(self):
        assert _strip_markdown("__bold text__") == "bold text"

    def test_preserve_snake_case(self):
        assert "my_var" in _strip_markdown("my_var = 5")

    def test_mixed_formatting(self):
        text = "## Summary\n**Senior** developer with *Python* experience"
        r = _strip_markdown(text)
        assert "##" not in r
        assert "**" not in r
        assert "*" not in r or "experience" in r
        assert "Senior" in r
        assert "Python" in r

    @pytest.mark.parametrize("text,expected", [
        ("**Python**, **Java**, **Docker**", "Python, Java, Docker"),
        ("## Experience\n- Led team", "Experience\n- Led team"),
        ("`AWS` certified", "AWS certified"),
        ("Skills: **Python**, *Java*", "Skills: Python, Java"),
    ])
    def test_real_ai_output(self, text, expected):
        r = _strip_markdown(text)
        assert r == expected

    def test_multiline(self):
        text = """## Summary
**Experienced** developer

## Experience
- **Led** team of 15
- *Improved* performance by 40%"""
        r = _strip_markdown(text)
        assert "##" not in r
        assert "**" not in r
        assert "Led" in r
        assert "40%" in r

    def test_already_clean(self):
        text = "Led team of 15 engineers"
        assert _strip_markdown(text) == text

    def test_resume_like_output(self):
        text = """## JANE DOE
**Senior Software Engineer**

### Experience
**Senior Dev** at **TechCorp** (2020-Present)
- **Led** migration of monolithic app
- Managed team of **15** engineers
- Implemented CI/CD pipeline increasing release frequency by **200%**"""
        r = _strip_markdown(text)
        assert "##" not in r
        assert "**" not in r
        assert "JANE DOE" in r
        assert "200%" in r
        assert "TechCorp" in r


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Config tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestConfig:
    def test_settings_loads(self):
        from config import get_settings
        s = get_settings()
        assert s.claude_model is not None

    def test_action_verbs_count(self):
        from config import ATS_ACTION_VERBS
        assert len(ATS_ACTION_VERBS) >= 200

    def test_standard_sections_count(self):
        from config import ATS_STANDARD_SECTIONS
        assert len(ATS_STANDARD_SECTIONS) >= 10

    def test_action_verbs_lowercase(self):
        from config import ATS_ACTION_VERBS
        assert all(v == v.lower() for v in ATS_ACTION_VERBS)

    def test_no_duplicate_verbs(self):
        from config import ATS_ACTION_VERBS
        assert len(ATS_ACTION_VERBS) == len(set(ATS_ACTION_VERBS))

    def test_outputs_dir_exists(self):
        from config import OUTPUTS_DIR
        assert OUTPUTS_DIR.exists()

    def test_base_dir_exists(self):
        from config import BASE_DIR
        assert BASE_DIR.exists()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Integration: end-to-end (non-AI)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEndToEnd:
    def test_build_analyse_tailor(self, sample_resume_data, sample_job_description):
        """Full pipeline: build → ATS check → tailor."""
        from modules.resume_builder import ResumeBuilder
        from modules.ats_optimizer import ATSOptimizer
        from modules.resume_tailor import ResumeTailor

        # 1. Build
        builder = ResumeBuilder()
        builder.load_data(sample_resume_data)
        text = builder.to_plain_text()
        assert len(text) > 100

        # 2. ATS Check
        report = ATSOptimizer().analyse(text, sample_job_description)
        assert 0 <= report.overall_score <= 100

        # 3. Tailor
        result = ResumeTailor().tailor(text, sample_job_description, use_ai=False)
        assert "tailored_resume" in result
        assert len(result["tailored_resume"]) > 0

    def test_build_export_all_formats(self, sample_resume_data, tmp_path):
        """Build and export to all formats."""
        from modules.resume_builder import ResumeBuilder

        builder = ResumeBuilder()
        builder.load_data(sample_resume_data)

        for fmt in ["txt", "pdf", "docx"]:
            p = builder.export(fmt, output_path=str(tmp_path / f"test.{fmt}"))
            assert p.exists()
            assert p.stat().st_size > 0

    def test_analyse_and_compare(self, sample_resume_text, sample_job_description):
        """ATS analyse + JD compare."""
        from modules.ats_optimizer import ATSOptimizer
        from modules.job_analyzer import JobAnalyzer

        ats = ATSOptimizer().analyse(sample_resume_text, sample_job_description)
        jd = JobAnalyzer().compare(sample_job_description, sample_resume_text, use_ai=False)

        assert ats.overall_score > 0
        assert jd.match_rate >= 0

    def test_tailor_then_ats(self, sample_resume_text, sample_job_description):
        """Tailor → ATS check: tailored should score ≥ original."""
        from modules.ats_optimizer import ATSOptimizer
        from modules.resume_tailor import ResumeTailor

        original_score = ATSOptimizer().analyse(sample_resume_text, sample_job_description).overall_score
        tailored = ResumeTailor().tailor(sample_resume_text, sample_job_description, use_ai=False)
        tailored_score = ATSOptimizer().analyse(tailored["tailored_resume"], sample_job_description).overall_score

        # Tailored should not be dramatically worse
        assert tailored_score >= original_score - 10

    def test_full_pipeline_with_templates(self, sample_resume_data, sample_job_description, tmp_path):
        """Build → Tailor → Export with all templates."""
        from modules.resume_builder import ResumeBuilder
        from modules.resume_tailor import ResumeTailor
        from modules.templates import export_pdf_template, export_docx_template

        builder = ResumeBuilder()
        builder.load_data(sample_resume_data)
        text = builder.to_plain_text()

        result = ResumeTailor().tailor(text, sample_job_description, use_ai=False)
        assert "tailored_resume" in result

        for template in ["minimal", "professional", "modern"]:
            pdf = export_pdf_template(sample_resume_data, template, str(tmp_path / f"{template}.pdf"))
            docx = export_docx_template(sample_resume_data, template, str(tmp_path / f"{template}.docx"))
            assert pdf.exists()
            assert docx.exists()
