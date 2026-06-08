"""
CV Tailor — Configuration Module
=================================
Centralised application settings loaded from environment variables / .env file.
Uses pydantic-settings for validation and type safety.
"""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


# ── Paths ────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUTS_DIR = BASE_DIR / "outputs"

# Ensure output directory exists
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    """Application-wide settings, auto-loaded from .env."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── API keys ─────────────────────────────────────────────
    anthropic_api_key: str = Field(default="", description="Anthropic / Claude API key")
    claude_model: str = Field(default="claude-sonnet-4-20250514", description="Claude model identifier")
    deepgram_api_key: str = Field(default="", description="Deepgram speech-to-text API key")

    # ── Application ──────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    output_dir: str = "outputs"
    default_template: Literal["minimal", "professional", "modern"] = "professional"
    default_export_format: Literal["pdf", "docx"] = "pdf"

    # ── Claude tuning ────────────────────────────────────────
    claude_max_tokens: int = 4096
    claude_temperature: float = 0.4

    # ── Retry logic ──────────────────────────────────────────
    api_max_retries: int = 3
    api_retry_wait: float = 2.0  # seconds between retries


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()


# ── ATS Configuration constants ──────────────────────────────
ATS_STANDARD_SECTIONS = [
    "Summary",
    "Professional Summary",
    "Career Summary",
    "Executive Summary",
    "Objective",
    "Career Objective",
    "Profile",
    "Experience",
    "Work Experience",
    "Professional Experience",
    "Employment History",
    "Education",
    "Academic Background",
    "Skills",
    "Technical Skills",
    "Core Competencies",
    "Key Skills",
    "Areas of Expertise",
    "Certifications",
    "Licenses & Certifications",
    "Professional Development",
    "Projects",
    "Key Projects",
    "Languages",
    "Volunteer Experience",
    "Community Involvement",
    "Awards",
    "Awards & Honors",
    "Achievements",
    "Publications",
    "Research",
    "Training",
]

ATS_ACTION_VERBS = [
    # Core leadership & management
    "achieved", "administered", "advised", "aligned", "allocated",
    "analyzed", "applied", "appointed", "architected", "assembled",
    "assessed", "assigned", "assisted", "attained", "automated",
    # Build & create
    "built", "calculated", "centralized", "chaired", "championed",
    "coached", "collaborated", "communicated", "compiled", "completed",
    "composed", "conceived", "conceptualized", "conducted", "configured",
    "consolidated", "constructed", "consulted", "contributed", "converted",
    "coordinated", "crafted", "created", "cultivated", "customized",
    # Deliver & develop
    "debugged", "decreased", "defined", "delegated", "delivered",
    "demonstrated", "deployed", "designed", "detected", "determined",
    "developed", "devised", "diagnosed", "digitized", "directed",
    "discovered", "documented", "drafted", "drove",
    # Engineer & execute
    "earned", "edited", "educated", "elevated", "eliminated",
    "enabled", "encouraged", "engineered", "enhanced", "ensured",
    "established", "evaluated", "examined", "exceeded", "executed",
    "expanded", "expedited", "experimented",
    # Facilitate & formulate
    "facilitated", "finalized", "fixed", "forecasted", "formulated",
    "founded", "fulfilled", "gathered", "generated", "governed", "grew",
    # Handle & implement
    "handled", "headed", "hired", "hosted",
    "identified", "illustrated", "implemented", "improved", "incorporated",
    "increased", "influenced", "informed", "initiated", "innovated",
    "inspected", "installed", "instituted", "instructed", "integrated",
    "interpreted", "introduced", "invented", "investigated",
    # Launch & lead
    "launched", "led", "leveraged", "liaised", "lifted",
    # Maintain & monitor
    "maintained", "managed", "mapped", "marketed", "maximized",
    "measured", "mediated", "mentored", "merged", "migrated",
    "minimized", "mobilized", "modeled", "modernized", "modified",
    "monitored", "motivated",
    # Navigate & operate
    "navigated", "negotiated", "observed", "obtained", "onboarded",
    "operated", "optimized", "orchestrated", "organized", "outlined",
    "overhauled", "oversaw",
    # Perform & produce
    "partnered", "performed", "pioneered", "planned", "presented",
    "prevented", "prioritized", "processed", "procured", "produced",
    "programmed", "projected", "promoted", "proposed", "provided",
    "published", "pursued",
    # Raised & resolved
    "raised", "realized", "recommended", "reconciled", "recruited",
    "redesigned", "reduced", "refined", "reformed", "refactored",
    "re-engineered", "regulated", "rehabilitated", "reinforced",
    "remodeled", "reorganized", "repaired", "replaced", "reported",
    "represented", "researched", "resolved", "restored", "restructured",
    "revamped", "reviewed", "revised", "revitalized",
    # Saved & supervised
    "saved", "scaled", "scheduled", "secured", "selected", "served",
    "shaped", "simplified", "solved", "sourced", "spearheaded",
    "specified", "staffed", "standardized", "steered", "stimulated",
    "strategized", "streamlined", "strengthened", "structured",
    "succeeded", "summarized", "supervised", "supported", "surpassed",
    "surveyed", "sustained", "synthesized", "systematized",
    # Trained & utilized
    "tackled", "tailored", "targeted", "taught", "tested",
    "tracked", "trained", "transcribed", "transformed", "translated",
    "troubleshot", "tutored",
    "unified", "updated", "upgraded", "utilized",
    "validated", "visualized", "volunteered",
    "widened", "won", "wrote",
]
