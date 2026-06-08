"""
CV Tailor — Resume Data Models
================================
Pydantic models for structured, validated resume data.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ExperienceEntry(BaseModel):
    """A single work-experience entry."""
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company / organisation name")
    location: str = Field(default="", description="City, State or Remote")
    start_date: str = Field(..., description="Start date (e.g. 'Jan 2022')")
    end_date: str = Field(default="Present", description="End date or 'Present'")
    bullets: list[str] = Field(default_factory=list, description="Bullet-point accomplishments")


class EducationEntry(BaseModel):
    """A single education entry."""
    degree: str = Field(..., description="Degree / diploma title")
    institution: str = Field(..., description="School / university name")
    location: str = Field(default="", description="City, State")
    graduation_date: str = Field(default="", description="Graduation date")
    gpa: str = Field(default="", description="GPA (optional)")


class ProjectEntry(BaseModel):
    """A single project entry."""
    name: str = Field(..., description="Project title")
    description: str = Field(default="", description="Brief description")
    technologies: str = Field(default="", description="Technologies used")


class ResumeData(BaseModel):
    """Complete structured resume data."""
    name: str = Field(..., description="Full name")
    email: str = Field(default="", description="Email address")
    phone: str = Field(default="", description="Phone number")
    location: str = Field(default="", description="City, State")
    linkedin: str = Field(default="", description="LinkedIn URL")
    website: str = Field(default="", description="Portfolio / personal website")
    summary: str = Field(default="", description="Professional summary")
    skills: list[str] = Field(default_factory=list, description="List of skills")
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to plain dict for export functions."""
        return self.model_dump()

    def to_plain_text(self) -> str:
        """Convert to plain text for tailoring / analysis."""
        from utils.file_export import resume_data_to_text
        return resume_data_to_text(self.to_dict())
