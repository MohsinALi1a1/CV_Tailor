"""
Tests for the templates module.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.templates import (
    get_template_config,
    list_templates,
    export_pdf_template,
    export_docx_template,
    TEMPLATE_CONFIGS,
)


class TestTemplateConfig:
    """Tests for template configuration."""

    def test_list_templates(self):
        templates = list_templates()
        assert len(templates) == 3
        names = [t["name"] for t in templates]
        assert "minimal" in names
        assert "professional" in names
        assert "modern" in names

    def test_get_template_config(self):
        for name in ("minimal", "professional", "modern"):
            config = get_template_config(name)
            assert "font" in config
            assert "color_primary" in config
            assert "margins" in config

    def test_invalid_template(self):
        with pytest.raises(ValueError, match="Unknown template"):
            get_template_config("nonexistent")


class TestTemplateExport:
    """Tests for templated PDF/DOCX export."""

    @pytest.mark.parametrize("template", ["minimal", "professional", "modern"])
    def test_export_pdf_all_templates(self, sample_resume_data, tmp_path, template):
        path = export_pdf_template(
            sample_resume_data,
            template_name=template,
            output_path=str(tmp_path / f"test_{template}.pdf"),
        )
        assert path.exists()
        assert path.stat().st_size > 0

    @pytest.mark.parametrize("template", ["minimal", "professional", "modern"])
    def test_export_docx_all_templates(self, sample_resume_data, tmp_path, template):
        path = export_docx_template(
            sample_resume_data,
            template_name=template,
            output_path=str(tmp_path / f"test_{template}.docx"),
        )
        assert path.exists()
        assert path.stat().st_size > 0

    def test_export_minimal_data(self, tmp_path):
        minimal = {"name": "John Doe"}
        path = export_pdf_template(
            minimal,
            template_name="professional",
            output_path=str(tmp_path / "minimal.pdf"),
        )
        assert path.exists()
