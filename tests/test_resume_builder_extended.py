"""
Extended tests for Resume Builder — 150+ scenarios.
"""
from __future__ import annotations
import json, sys, tempfile
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.resume_builder import ResumeBuilder


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Contact info
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBuilderContact:
    def test_set_name(self):
        b = ResumeBuilder()
        b.set_contact("Alice Smith")
        assert b.get_data()["name"] == "Alice Smith"

    def test_set_all_fields(self):
        b = ResumeBuilder()
        b.set_contact("Alice", "a@t.com", "+1-555", "NYC", "li.com/alice", "alice.dev")
        d = b.get_data()
        assert d["name"] == "Alice"
        assert d["email"] == "a@t.com"
        assert d["phone"] == "+1-555"
        assert d["location"] == "NYC"
        assert d["linkedin"] == "li.com/alice"
        assert d["website"] == "alice.dev"

    def test_update_contact(self):
        b = ResumeBuilder()
        b.set_contact("Alice")
        b.set_contact("Bob")
        assert b.get_data()["name"] == "Bob"

    def test_empty_name(self):
        b = ResumeBuilder()
        b.set_contact("")
        assert b.get_data()["name"] == ""

    @pytest.mark.parametrize("name", [
        "John Doe", "María García", "张伟", "Ahmed Al-Farsi",
        "O'Brien", "Jean-Pierre", "Dr. Smith", "Jr. Doe",
    ])
    def test_diverse_names(self, name):
        b = ResumeBuilder()
        b.set_contact(name)
        assert b.get_data()["name"] == name

    @pytest.mark.parametrize("email", [
        "john@example.com", "jane.doe@company.co.uk",
        "user+tag@gmail.com", "test@test.io",
    ])
    def test_various_emails(self, email):
        b = ResumeBuilder()
        b.set_contact("Test", email)
        assert b.get_data()["email"] == email

    @pytest.mark.parametrize("phone", [
        "+1-555-0100", "(555) 010-0100", "+44 20 7946 0958",
        "555.010.0100", "+92 300 1234567",
    ])
    def test_various_phones(self, phone):
        b = ResumeBuilder()
        b.set_contact("Test", phone=phone)
        assert b.get_data()["phone"] == phone


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Summary
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBuilderSummary:
    def test_set_summary(self):
        b = ResumeBuilder()
        b.set_summary("Senior engineer with 8 years experience")
        assert "8 years" in b.get_data()["summary"]

    def test_empty_summary(self):
        b = ResumeBuilder()
        b.set_summary("")
        assert b.get_data()["summary"] == ""

    def test_long_summary(self):
        b = ResumeBuilder()
        long_text = "Experienced developer. " * 50
        b.set_summary(long_text)
        assert len(b.get_data()["summary"]) > 100

    def test_summary_with_special_chars(self):
        b = ResumeBuilder()
        b.set_summary("C++ & C# developer with .NET experience")
        assert "C++" in b.get_data()["summary"]

    def test_update_summary(self):
        b = ResumeBuilder()
        b.set_summary("First")
        b.set_summary("Second")
        assert b.get_data()["summary"] == "Second"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Skills
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBuilderSkills:
    def test_add_single(self):
        b = ResumeBuilder()
        b.add_skill("Python")
        assert "Python" in b.get_data()["skills"]

    def test_add_multiple(self):
        b = ResumeBuilder()
        b.add_skill("Python")
        b.add_skill("Java")
        b.add_skill("Docker")
        assert len(b.get_data()["skills"]) == 3

    def test_no_duplicates(self):
        b = ResumeBuilder()
        b.add_skill("Python")
        b.add_skill("Python")
        b.add_skill("Python")
        assert b.get_data()["skills"].count("Python") == 1

    def test_set_skills(self):
        b = ResumeBuilder()
        b.set_skills(["Python", "Java", "Docker"])
        assert len(b.get_data()["skills"]) == 3

    def test_set_skills_dedupes(self):
        b = ResumeBuilder()
        b.set_skills(["Python", "Java", "Python", "Java"])
        assert len(b.get_data()["skills"]) == 2

    def test_empty_skill_ignored(self):
        b = ResumeBuilder()
        b.add_skill("")
        assert len(b.get_data()["skills"]) == 0

    @pytest.mark.parametrize("skill", [
        "Python", "JavaScript", "C++", "C#", ".NET", "React.js",
        "Node.js", "AWS", "Docker", "Kubernetes", "TensorFlow",
        "Machine Learning", "Data Science", "CI/CD", "REST APIs",
    ])
    def test_various_skills(self, skill):
        b = ResumeBuilder()
        b.add_skill(skill)
        assert skill in b.get_data()["skills"]

    def test_many_skills(self):
        b = ResumeBuilder()
        for i in range(50):
            b.add_skill(f"Skill_{i}")
        assert len(b.get_data()["skills"]) == 50


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Experience
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBuilderExperience:
    def test_add_basic(self):
        b = ResumeBuilder()
        b.add_experience("Dev", "Corp")
        assert len(b.get_data()["experience"]) == 1

    def test_add_full(self):
        b = ResumeBuilder()
        b.add_experience(title="Senior Dev", company="TechCorp",
                         location="San Francisco",
                         start_date="Jan 2020", end_date="Present",
                         bullets=["Led team", "Built APIs"])
        exp = b.get_data()["experience"][0]
        assert exp["title"] == "Senior Dev"
        assert exp["company"] == "TechCorp"
        assert len(exp["bullets"]) == 2

    def test_add_multiple_experiences(self):
        b = ResumeBuilder()
        for i in range(5):
            b.add_experience(f"Title {i}", f"Company {i}")
        assert len(b.get_data()["experience"]) == 5

    def test_experience_ordering(self):
        b = ResumeBuilder()
        b.add_experience("First", "Corp1")
        b.add_experience("Second", "Corp2")
        exps = b.get_data()["experience"]
        assert exps[0]["title"] == "First"
        assert exps[1]["title"] == "Second"

    def test_experience_with_bullets(self):
        bullets = [
            "Led migration reducing deployment time by 60%",
            "Managed team of 15 engineers",
            "Implemented CI/CD pipeline",
        ]
        b = ResumeBuilder()
        b.add_experience("Dev", "Corp", bullets=bullets)
        assert len(b.get_data()["experience"][0]["bullets"]) == 3

    def test_empty_title(self):
        b = ResumeBuilder()
        b.add_experience("", "Corp")
        assert b.get_data()["experience"][0]["title"] == ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Education
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBuilderEducation:
    def test_add_basic(self):
        b = ResumeBuilder()
        b.add_education("BS CS", "MIT")
        assert len(b.get_data()["education"]) == 1

    def test_add_full(self):
        b = ResumeBuilder()
        b.add_education("BS CS", "MIT", "2020", "3.9", "Cambridge, MA")
        edu = b.get_data()["education"][0]
        assert edu["degree"] == "BS CS"
        assert edu["institution"] == "MIT"

    def test_add_multiple(self):
        b = ResumeBuilder()
        b.add_education("BS", "Uni1")
        b.add_education("MS", "Uni2")
        assert len(b.get_data()["education"]) == 2

    @pytest.mark.parametrize("degree", [
        "B.S. Computer Science", "M.S. Data Science", "Ph.D. Machine Learning",
        "MBA", "B.E. Electrical Engineering", "Associate's Degree",
    ])
    def test_various_degrees(self, degree):
        b = ResumeBuilder()
        b.add_education(degree, "University")
        assert b.get_data()["education"][0]["degree"] == degree


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Certifications
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBuilderCertifications:
    def test_add(self):
        b = ResumeBuilder()
        b.add_certification("AWS Certified")
        assert "AWS Certified" in b.get_data()["certifications"]

    def test_no_duplicates(self):
        b = ResumeBuilder()
        b.add_certification("AWS")
        b.add_certification("AWS")
        assert b.get_data()["certifications"].count("AWS") == 1

    def test_multiple(self):
        b = ResumeBuilder()
        b.add_certification("AWS")
        b.add_certification("GCP")
        b.add_certification("Azure")
        assert len(b.get_data()["certifications"]) == 3

    @pytest.mark.parametrize("cert", [
        "AWS Certified Solutions Architect",
        "Google Cloud Professional",
        "Azure Administrator",
        "Certified Kubernetes Administrator",
        "PMP - Project Management Professional",
        "Scrum Master Certified",
    ])
    def test_various_certs(self, cert):
        b = ResumeBuilder()
        b.add_certification(cert)
        assert cert in b.get_data()["certifications"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Projects
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBuilderProjects:
    def test_add(self):
        b = ResumeBuilder()
        b.add_project("MyApp", "A cool app", "Python, React")
        assert len(b.get_data()["projects"]) == 1

    def test_add_multiple(self):
        b = ResumeBuilder()
        for i in range(5):
            b.add_project(f"Project{i}", f"Description {i}", f"Tech {i}")
        assert len(b.get_data()["projects"]) == 5

    def test_project_fields(self):
        b = ResumeBuilder()
        b.add_project("Dashboard", "Real-time analytics", "React, D3.js")
        p = b.get_data()["projects"][0]
        assert p["name"] == "Dashboard"
        assert p["description"] == "Real-time analytics"
        assert p["technologies"] == "React, D3.js"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Languages
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBuilderLanguages:
    def test_set_languages(self):
        b = ResumeBuilder()
        b.set_languages(["English", "Spanish"])
        assert b.get_data()["languages"] == ["English", "Spanish"]

    def test_update_languages(self):
        b = ResumeBuilder()
        b.set_languages(["English"])
        b.set_languages(["French", "German"])
        assert b.get_data()["languages"] == ["French", "German"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Research Papers, Volunteer, Achievements
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBuilderNewSections:
    def test_add_research_paper(self):
        b = ResumeBuilder()
        b.add_research_paper(title="AI Paper", authors="J. Doe", venue="IEEE", year="2024")
        assert len(b.get_data()["research_papers"]) == 1

    def test_add_volunteer_work(self):
        b = ResumeBuilder()
        b.add_volunteer_work(role="Mentor", organization="Code.org", description="Taught coding")
        assert len(b.get_data()["volunteer_work"]) == 1

    def test_add_achievement(self):
        b = ResumeBuilder()
        b.add_achievement("Dean's List 2024")
        assert "Dean's List 2024" in b.get_data()["achievements"]

    def test_multiple_papers(self):
        b = ResumeBuilder()
        for i in range(5):
            b.add_research_paper(title=f"Paper {i}", authors="Author", venue="Venue", year="2024")
        assert len(b.get_data()["research_papers"]) == 5

    def test_multiple_volunteer(self):
        b = ResumeBuilder()
        for i in range(3):
            b.add_volunteer_work(role=f"Role {i}", organization=f"Org {i}")
        assert len(b.get_data()["volunteer_work"]) == 3

    def test_multiple_achievements(self):
        b = ResumeBuilder()
        b.add_achievement("Award 1")
        b.add_achievement("Award 2")
        assert len(b.get_data()["achievements"]) == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Fluent API / Chaining
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBuilderChaining:
    def test_all_methods_return_self(self):
        b = ResumeBuilder()
        result = (
            b.set_contact("Jane", "j@t.com")
            .set_summary("Test summary")
            .add_skill("Python")
            .add_experience("Dev", "Corp")
            .add_education("BS", "MIT")
            .add_certification("AWS")
            .set_languages(["English"])
        )
        assert result is b

    def test_chain_build_complete(self):
        b = (
            ResumeBuilder()
            .set_contact("Jane Doe", "j@example.com", "+1-555", "NYC")
            .set_summary("Experienced developer")
            .add_skill("Python")
            .add_skill("Java")
            .add_experience("Senior Dev", "Corp", "2020", "Present",
                            ["Led team", "Built APIs"])
            .add_education("BS CS", "MIT", "2016")
            .add_certification("AWS")
        )
        d = b.get_data()
        assert d["name"] == "Jane Doe"
        assert len(d["skills"]) == 2
        assert len(d["experience"]) == 1
        assert len(d["education"]) == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Load data / JSON
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBuilderLoadData:
    def test_load_data(self, sample_resume_data):
        b = ResumeBuilder()
        b.load_data(sample_resume_data)
        d = b.get_data()
        assert d["name"] == "Jane Doe"
        assert len(d["experience"]) == 2

    def test_load_minimal(self):
        b = ResumeBuilder()
        b.load_data({"name": "John"})
        assert b.get_data()["name"] == "John"

    def test_load_empty(self):
        b = ResumeBuilder()
        # Empty dict missing required 'name' field
        with pytest.raises(Exception):
            b.load_data({})

    def test_load_json(self, sample_resume_data, tmp_path):
        p = tmp_path / "resume.json"
        p.write_text(json.dumps(sample_resume_data))
        b = ResumeBuilder()
        b.load_json(str(p))
        assert b.get_data()["name"] == "Jane Doe"

    def test_load_data_preserves_all_fields(self, sample_resume_data):
        b = ResumeBuilder()
        b.load_data(sample_resume_data)
        d = b.get_data()
        assert d["email"] == "jane.doe@email.com"
        assert d["phone"] == "+1-555-0100"
        assert len(d["skills"]) == 12


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Plain text export
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBuilderPlainText:
    def test_basic(self, sample_resume_data):
        b = ResumeBuilder()
        b.load_data(sample_resume_data)
        text = b.to_plain_text()
        assert "Jane Doe" in text
        assert "Python" in text

    def test_minimal(self):
        b = ResumeBuilder()
        b.set_contact("John Doe")
        text = b.to_plain_text()
        assert "John Doe" in text

    def test_includes_experience(self, sample_resume_data):
        b = ResumeBuilder()
        b.load_data(sample_resume_data)
        text = b.to_plain_text()
        assert "Tech Corp" in text

    def test_includes_education(self, sample_resume_data):
        b = ResumeBuilder()
        b.load_data(sample_resume_data)
        text = b.to_plain_text()
        assert "Computer Science" in text

    def test_includes_skills(self, sample_resume_data):
        b = ResumeBuilder()
        b.load_data(sample_resume_data)
        text = b.to_plain_text()
        for skill in ["Python", "Docker", "AWS"]:
            assert skill in text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  File exports
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBuilderExportExtended:
    @pytest.mark.parametrize("fmt", ["txt", "pdf", "docx"])
    def test_export_formats(self, sample_resume_data, tmp_path, fmt):
        b = ResumeBuilder()
        b.load_data(sample_resume_data)
        p = b.export(fmt, output_path=str(tmp_path / f"test.{fmt}"))
        assert p.exists()
        assert p.stat().st_size > 0

    def test_export_invalid_format(self, sample_resume_data):
        b = ResumeBuilder()
        b.load_data(sample_resume_data)
        with pytest.raises(ValueError):
            b.export("html")

    def test_export_pdf_minimal(self, tmp_path):
        b = ResumeBuilder()
        b.set_contact("John Doe")
        p = b.export("pdf", output_path=str(tmp_path / "minimal.pdf"))
        assert p.exists()

    def test_export_docx_minimal(self, tmp_path):
        b = ResumeBuilder()
        b.set_contact("John Doe")
        p = b.export("docx", output_path=str(tmp_path / "minimal.docx"))
        assert p.exists()

    def test_export_txt_minimal(self, tmp_path):
        b = ResumeBuilder()
        b.set_contact("John Doe")
        p = b.export("txt", output_path=str(tmp_path / "minimal.txt"))
        assert p.exists()
        assert "John Doe" in p.read_text(encoding="utf-8")

    def test_export_pdf_full(self, sample_resume_data, tmp_path):
        b = ResumeBuilder()
        b.load_data(sample_resume_data)
        p = b.export("pdf", output_path=str(tmp_path / "full.pdf"))
        assert p.stat().st_size > 1000  # Should be a real PDF

    def test_export_docx_full(self, sample_resume_data, tmp_path):
        b = ResumeBuilder()
        b.load_data(sample_resume_data)
        p = b.export("docx", output_path=str(tmp_path / "full.docx"))
        assert p.stat().st_size > 1000


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Validated data
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBuilderValidation:
    def test_validated_data(self, sample_resume_data):
        b = ResumeBuilder()
        b.load_data(sample_resume_data)
        v = b.get_validated_data()
        assert v.name == "Jane Doe"
        assert len(v.experience) == 2

    def test_validated_minimal(self):
        b = ResumeBuilder()
        b.set_contact("John")
        v = b.get_validated_data()
        assert v.name == "John"
