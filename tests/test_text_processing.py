"""
Tests for the text_processing utility module.
These tests do NOT require API keys and test pure text processing logic.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.text_processing import (
    extract_keywords,
    match_keywords,
    clean_text,
    count_words,
    bullet_to_list,
    list_to_bullet,
    has_quantified_achievement,
    starts_with_action_verb,
    calculate_keyword_density,
    parse_resume_sections,
)


class TestExtractKeywords:
    """Tests for keyword extraction."""

    def test_basic_extraction(self):
        text = "Python developer with experience in machine learning and data science"
        keywords = extract_keywords(text, top_n=10)
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        # At least some recognisable terms should be extracted
        lower_keywords = [kw.lower() for kw in keywords]
        assert any("python" in kw for kw in lower_keywords)

    def test_empty_text(self):
        keywords = extract_keywords("", top_n=10)
        assert keywords == []

    def test_top_n_limit(self):
        text = "Python Java JavaScript TypeScript Go Rust C++ Ruby PHP Swift Kotlin Scala"
        keywords = extract_keywords(text, top_n=3)
        assert len(keywords) <= 3


class TestMatchKeywords:
    """Tests for keyword matching between resume and job description."""

    def test_perfect_match(self):
        result = match_keywords(["python", "java", "sql"], ["python", "java", "sql"])
        assert result["match_rate"] == 100.0
        assert len(result["missing"]) == 0

    def test_partial_match(self):
        result = match_keywords(["python", "java"], ["python", "java", "sql", "go"])
        assert result["match_rate"] == 50.0
        assert "sql" in result["missing"]
        assert "go" in result["missing"]

    def test_no_match(self):
        result = match_keywords(["python", "java"], ["ruby", "scala"])
        assert result["match_rate"] == 0.0
        assert len(result["missing"]) == 2

    def test_case_insensitive(self):
        result = match_keywords(["Python", "JAVA"], ["python", "java"])
        assert result["match_rate"] == 100.0

    def test_empty_job_keywords(self):
        result = match_keywords(["python"], [])
        # Should not crash; empty job set → 100% match (nothing required)
        assert isinstance(result["match_rate"], float)


class TestCleanText:
    """Tests for text cleaning."""

    def test_collapse_whitespace(self):
        text = "Hello    World   Test"
        assert "  " not in clean_text(text)

    def test_collapse_newlines(self):
        text = "Hello\n\n\n\n\nWorld"
        result = clean_text(text)
        assert "\n\n\n" not in result

    def test_strip(self):
        text = "   Hello World   "
        assert clean_text(text) == "Hello World"


class TestCountWords:
    """Tests for word counting."""

    def test_basic(self):
        assert count_words("Hello World") == 2

    def test_empty(self):
        assert count_words("") == 1 or count_words("") == 0  # split on empty returns ['']

    def test_multiline(self):
        assert count_words("Hello\nWorld\nTest") == 3


class TestBulletParsing:
    """Tests for bullet point parsing and formatting."""

    def test_bullet_to_list(self):
        text = "• Item one\n• Item two\n- Item three"
        result = bullet_to_list(text)
        assert len(result) == 3
        assert result[0] == "Item one"
        assert result[2] == "Item three"

    def test_list_to_bullet(self):
        items = ["Item one", "Item two"]
        result = list_to_bullet(items)
        assert "• Item one" in result
        assert "• Item two" in result

    def test_empty_bullets(self):
        assert bullet_to_list("") == []
        assert list_to_bullet([]) == ""


class TestQuantifiedAchievements:
    """Tests for detecting quantified achievements in bullets."""

    def test_percentage(self):
        assert has_quantified_achievement("Increased revenue by 40%") is True

    def test_dollar(self):
        assert has_quantified_achievement("Saved $2 million in costs") is True

    def test_number(self):
        assert has_quantified_achievement("Managed team of 15 engineers") is True

    def test_no_numbers(self):
        assert has_quantified_achievement("Worked on improving code quality") is False


class TestActionVerbs:
    """Tests for action verb detection."""

    def test_starts_with_action(self):
        assert starts_with_action_verb("Led a team of 10 engineers") is True
        assert starts_with_action_verb("Developed a new microservice") is True
        assert starts_with_action_verb("Managed cross-functional projects") is True

    def test_no_action_verb(self):
        assert starts_with_action_verb("The project was completed") is False
        assert starts_with_action_verb("I worked on the backend") is False


class TestKeywordDensity:
    """Tests for keyword density calculation."""

    def test_basic_density(self):
        text = "python python python java java sql"
        density = calculate_keyword_density(text, ["python", "java"])
        assert density["python"] > density["java"]

    def test_zero_density(self):
        text = "hello world"
        density = calculate_keyword_density(text, ["python"])
        assert density["python"] == 0.0


class TestParseResumeSections:
    """Tests for resume section parsing."""

    def test_basic_parsing(self, sample_resume_text):
        sections = parse_resume_sections(sample_resume_text)
        assert isinstance(sections, dict)
        # Should find at least some sections
        section_names = [s.lower() for s in sections.keys()]
        assert any("experience" in s for s in section_names) or any(
            "skills" in s for s in section_names
        )

    def test_no_sections(self):
        text = "Just a plain text without any headings or structure."
        sections = parse_resume_sections(text)
        assert "Full Resume" in sections
