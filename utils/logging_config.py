"""
CV Tailor — Logging Configuration
===================================
Configures rich-formatted logging for the entire application.
"""

from __future__ import annotations

import logging
import sys

from config import get_settings


def setup_logging() -> None:
    """Configure application-wide logging with rich formatting."""
    settings = get_settings()
    level = getattr(logging, settings.log_level, logging.INFO)

    try:
        from rich.logging import RichHandler

        handler = RichHandler(
            level=level,
            show_path=True,
            markup=True,
            rich_tracebacks=True,
        )
        fmt = "%(message)s"
    except ImportError:
        handler = logging.StreamHandler(sys.stdout)
        fmt = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"

    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(fmt, datefmt="%H:%M:%S"))

    root = logging.getLogger()
    root.setLevel(level)
    # Remove existing handlers to avoid duplicates
    root.handlers.clear()
    root.addHandler(handler)

    # Quieten noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
