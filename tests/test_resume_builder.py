"""
Tests for the Resume Builder module.
These tests do NOT require API keys (AI enhancement tests are skipped without key).
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.resume_builder import ResumeBuilder


class TestResumeBuilder:
    """Tests for the ResumeBuilder class."""

    def test_set_contact(self):
        builder = ResumeBuilder()
        builder.set_contact("Jane Doe", "jane@test.com", "+1-555-0100", "NYC")
        data = builder.get_data()
        assert data["name"] == "Jane Doe"
        assert data["email"] == "jane@test.com"
        assert data["phone"] == "+1-555-0100"
        assert data["location"] == "NYC"

    def test_set_summary(self):
        builder = ResumeBuilder()
        builder.set_summary("Experienced engineer")
        assert builder.get_data()["summary"] == "Experienced engineer"

    def test_add_skills(self):
        builder = ResumeBuilder()
        builder.add_skill("Python")
        builder.add_skill("Java")
        builder.add_skill("Python")  # duplicate
        data = builder.get_data()
        assert data["skills"] == ["Python", "Java"]

    def test_set_skills(self):
        builder = ResumeBuilder()
        builder.set_skills(["Python", "Java", "Python"])  # duplicate
        data = builder.get_data()
        assert data["skills"] == ["Python", "Java"]

    def test_add_experience(self):
        builder = ResumeBuilder()
        builder.add_experience(
            title="Engineer",
            company="Acme",
            start_date="Jan 2020",
            end_date="Present",
            bullets=["Built APIs", "Led team"],
        )
        data = builder.get_data()
        assert len(data["experience"]) == 1
        assert data["experience"][0]["title"] == "Engineer"
        assert len(data["experience"][0]["bullets"]) == 2

    def test_add_education(self):
        builder = ResumeBuilder()
        builder.add_education(
            degree="BSc CS",
            institution="MIT",
            graduation_date="2020",
            gpa="3.9",
        )
        data = builder.get_data()
        assert len(data["education"]) == 1
        assert data["education"][0]["degree"] == "BSc CS"

    def test_add_certification(self):
        builder = ResumeBuilder()
        builder.add_certification("AWS Certified")
        builder.add_certification("AWS Certified")  # duplicate
        data = builder.get_data()
        assert data["certifications"] == ["AWS Certified"]

    def test_add_project(self):
        builder = ResumeBuilder()
        builder.add_project("MyApp", "A cool app", "Python, React")
        data = builder.get_data()
        assert len(data["projects"]) == 1
        assert data["projects"][0]["name"] == "MyApp"

    def test_set_languages(self):
        builder = ResumeBuilder()
        builder.set_languages(["English", "Spanish"])
        assert builder.get_data()["languages"] == ["English", "Spanish"]

    def test_fluent_api(self):
        """Test method chaining."""
        builder = ResumeBuilder()
        result = (
            builder
            .set_contact("Jane", "j@t.com")
            .set_summary("Test")
            .add_skill("Python")
            .add_experience("Dev", "Acme")
            .add_education("BSc", "MIT")
            .add_certification("AWS")
            .set_languages(["English"])
        )
        assert result is builder

    def test_load_data(self, sample_resume_data):
        builder = ResumeBuilder()
        builder.load_data(sample_resume_data)
        data = builder.get_data()
        assert data["name"] == "Jane Doe"
        assert len(data["experience"]) == 2
        assert len(data["skills"]) == 12

    def test_load_json(self, sample_resume_data, tmp_path):
        json_path = tmp_path / "resume.json"
        json_path.write_text(json.dumps(sample_resume_data))
        builder = ResumeBuilder()
        builder.load_json(str(json_path))
        assert builder.get_data()["name"] == "Jane Doe"

    def test_to_plain_text(self, sample_resume_data):
        builder = ResumeBuilder()
        builder.load_data(sample_resume_data)
        text = builder.to_plain_text()
        assert "Jane Doe" in text
        assert "Python" in text
        assert "Tech Corp" in text

    def test_get_validated_data(self, sample_resume_data):
        builder = ResumeBuilder()
        builder.load_data(sample_resume_data)
        validated = builder.get_validated_data()
        assert validated.name == "Jane Doe"
        assert len(validated.experience) == 2


class TestResumeExport:
    """Tests for resume export functionality."""

    def test_export_txt(self, sample_resume_data, tmp_path):
        builder = ResumeBuilder()
        builder.load_data(sample_resume_data)
        path = builder.export("txt", output_path=str(tmp_path / "test.txt"))
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Jane Doe" in content

    def test_export_pdf(self, sample_resume_data, tmp_path):
        builder = ResumeBuilder()
        builder.load_data(sample_resume_data)
        path = builder.export("pdf", output_path=str(tmp_path / "test.pdf"))
        assert path.exists()
        assert path.stat().st_size > 0

    def test_export_docx(self, sample_resume_data, tmp_path):
        builder = ResumeBuilder()
        builder.load_data(sample_resume_data)
        path = builder.export("docx", output_path=str(tmp_path / "test.docx"))
        assert path.exists()
        assert path.stat().st_size > 0

    def test_export_invalid_format(self, sample_resume_data):
        builder = ResumeBuilder()
        builder.load_data(sample_resume_data)
        with pytest.raises(ValueError, match="Unsupported format"):
            builder.export("html")
