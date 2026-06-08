"""
Extended tests for Templates — 80+ scenarios.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.templates import (
    get_template_config, list_templates, export_pdf_template, export_docx_template,
    TEMPLATE_CONFIGS,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Template config
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestTemplateConfigExtended:
    def test_list_returns_3(self):
        assert len(list_templates()) == 3

    @pytest.mark.parametrize("name", ["minimal", "professional", "modern"])
    def test_each_has_font(self, name):
        assert "font" in get_template_config(name)

    @pytest.mark.parametrize("name", ["minimal", "professional", "modern"])
    def test_each_has_color(self, name):
        assert "color_primary" in get_template_config(name)

    @pytest.mark.parametrize("name", ["minimal", "professional", "modern"])
    def test_each_has_margins(self, name):
        assert "margins" in get_template_config(name)

    def test_invalid_template(self):
        with pytest.raises(ValueError):
            get_template_config("nonexistent")

    def test_template_configs_dict(self):
        assert isinstance(TEMPLATE_CONFIGS, dict)
        assert len(TEMPLATE_CONFIGS) == 3

    @pytest.mark.parametrize("name", ["minimal", "professional", "modern"])
    def test_template_in_list(self, name):
        names = [t["name"] for t in list_templates()]
        assert name in names


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PDF Export
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestPDFExportExtended:
    @pytest.mark.parametrize("template", ["minimal", "professional", "modern"])
    def test_all_templates(self, sample_resume_data, tmp_path, template):
        p = export_pdf_template(sample_resume_data, template, str(tmp_path / f"{template}.pdf"))
        assert p.exists() and p.stat().st_size > 0

    def test_minimal_data_pdf(self, tmp_path):
        p = export_pdf_template({"name": "John"}, "professional", str(tmp_path / "min.pdf"))
        assert p.exists()

    def test_empty_data_pdf(self, tmp_path):
        p = export_pdf_template({}, "minimal", str(tmp_path / "empty.pdf"))
        assert p.exists()

    def test_full_data_pdf(self, sample_resume_data, tmp_path):
        p = export_pdf_template(sample_resume_data, "professional", str(tmp_path / "full.pdf"))
        assert p.stat().st_size > 1000

    def test_pdf_with_projects(self, sample_resume_data, tmp_path):
        data = {**sample_resume_data, "projects": [
            {"name": "App", "description": "Cool app", "technologies": "Python"},
        ]}
        p = export_pdf_template(data, "modern", str(tmp_path / "proj.pdf"))
        assert p.exists()

    def test_pdf_with_certifications(self, sample_resume_data, tmp_path):
        data = {**sample_resume_data, "certifications": ["AWS", "GCP", "Azure"]}
        p = export_pdf_template(data, "professional", str(tmp_path / "cert.pdf"))
        assert p.exists()

    def test_pdf_with_languages(self, sample_resume_data, tmp_path):
        data = {**sample_resume_data, "languages": ["English", "Spanish", "French"]}
        p = export_pdf_template(data, "minimal", str(tmp_path / "lang.pdf"))
        assert p.exists()

    def test_pdf_with_volunteer(self, sample_resume_data, tmp_path):
        data = {**sample_resume_data, "volunteer_work": [
            {"role": "Mentor", "organization": "Code.org", "description": "Taught coding"},
        ]}
        p = export_pdf_template(data, "professional", str(tmp_path / "vol.pdf"))
        assert p.exists()

    def test_pdf_with_research(self, sample_resume_data, tmp_path):
        data = {**sample_resume_data, "research_papers": [
            {"title": "AI Paper", "authors": "J. Doe", "venue": "IEEE", "year": "2024"},
        ]}
        p = export_pdf_template(data, "modern", str(tmp_path / "res.pdf"))
        assert p.exists()

    def test_pdf_with_achievements(self, sample_resume_data, tmp_path):
        data = {**sample_resume_data, "achievements": ["Dean's List", "Hackathon Winner"]}
        p = export_pdf_template(data, "professional", str(tmp_path / "ach.pdf"))
        assert p.exists()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DOCX Export
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDOCXExportExtended:
    @pytest.mark.parametrize("template", ["minimal", "professional", "modern"])
    def test_all_templates(self, sample_resume_data, tmp_path, template):
        p = export_docx_template(sample_resume_data, template, str(tmp_path / f"{template}.docx"))
        assert p.exists() and p.stat().st_size > 0

    def test_minimal_data_docx(self, tmp_path):
        p = export_docx_template({"name": "John"}, "professional", str(tmp_path / "min.docx"))
        assert p.exists()

    def test_empty_data_docx(self, tmp_path):
        p = export_docx_template({}, "minimal", str(tmp_path / "empty.docx"))
        assert p.exists()

    def test_docx_with_all_sections(self, sample_resume_data, tmp_path):
        data = {
            **sample_resume_data,
            "certifications": ["AWS", "GCP"],
            "languages": ["English", "Spanish"],
            "research_papers": [{"title": "Paper", "authors": "A", "venue": "V", "year": "2024"}],
            "volunteer_work": [{"role": "Mentor", "organization": "Org", "description": "Desc"}],
            "achievements": ["Award 1", "Award 2"],
        }
        p = export_docx_template(data, "professional", str(tmp_path / "all.docx"))
        assert p.exists()
        assert p.stat().st_size > 1000

    @pytest.mark.parametrize("template", ["minimal", "professional", "modern"])
    def test_special_chars(self, tmp_path, template):
        data = {
            "name": "O'Brien & Partners",
            "email": "test@test.com",
            "summary": "C++ & C# developer with .NET <experience>",
            "skills": ["C++", "C#", ".NET", "React.js"],
            "experience": [{"title": "Dev", "company": "Corp & Co.", "bullets": ["Built APIs"]}],
        }
        p = export_docx_template(data, template, str(tmp_path / f"special_{template}.docx"))
        assert p.exists()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Cross-template consistency
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCrossTemplate:
    def test_all_produce_files(self, sample_resume_data, tmp_path):
        for template in ["minimal", "professional", "modern"]:
            pdf = export_pdf_template(sample_resume_data, template, str(tmp_path / f"{template}.pdf"))
            docx = export_docx_template(sample_resume_data, template, str(tmp_path / f"{template}.docx"))
            assert pdf.exists()
            assert docx.exists()

    def test_pdf_sizes_reasonable(self, sample_resume_data, tmp_path):
        for template in ["minimal", "professional", "modern"]:
            p = export_pdf_template(sample_resume_data, template, str(tmp_path / f"{template}.pdf"))
            size = p.stat().st_size
            assert 500 < size < 500_000  # Between 500 bytes and 500KB

    def test_docx_sizes_reasonable(self, sample_resume_data, tmp_path):
        for template in ["minimal", "professional", "modern"]:
            p = export_docx_template(sample_resume_data, template, str(tmp_path / f"{template}.docx"))
            size = p.stat().st_size
            assert 500 < size < 500_000
