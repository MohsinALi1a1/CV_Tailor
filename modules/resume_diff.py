"""
CV Tailor — Resume Diff & Comparison
======================================
Side-by-side diff utility to visualize changes between original and tailored resumes.
Generates HTML, plain text, and structured diff outputs.
"""

from __future__ import annotations

import difflib
import html
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiffStats:
    lines_added: int = 0
    lines_removed: int = 0
    lines_modified: int = 0
    lines_unchanged: int = 0
    words_added: int = 0
    words_removed: int = 0
    keywords_added: list[str] = field(default_factory=list)
    keywords_removed: list[str] = field(default_factory=list)
    similarity_pct: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "lines_modified": self.lines_modified,
            "lines_unchanged": self.lines_unchanged,
            "words_added": self.words_added,
            "words_removed": self.words_removed,
            "keywords_added": self.keywords_added,
            "keywords_removed": self.keywords_removed,
            "similarity_pct": round(self.similarity_pct, 1),
        }


@dataclass
class ResumeDiff:
    stats: DiffStats = field(default_factory=DiffStats)
    unified_diff: str = ""
    html_diff: str = ""
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "stats": self.stats.to_dict(),
            "unified_diff": self.unified_diff,
            "html_diff": self.html_diff,
            "summary": self.summary,
        }


def _tokenize(text: str) -> set[str]:
    """Extract significant words from text."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#./-]{1,}", text.lower())
    stopwords = {
        "the", "a", "an", "and", "or", "but", "of", "in", "on", "at", "to", "for",
        "with", "by", "from", "as", "is", "was", "were", "be", "been", "have", "has",
        "had", "do", "does", "did", "will", "would", "could", "should", "this", "that",
        "these", "those", "i", "we", "you", "they", "he", "she", "it", "my", "our",
    }
    return {w for w in words if len(w) >= 3 and w not in stopwords}


def diff_resumes(original: str, tailored: str) -> ResumeDiff:
    """Compare two resume texts and produce a structured diff.

    Args:
        original: The original resume text.
        tailored: The tailored / new resume text.

    Returns:
        ResumeDiff with stats, unified diff, and rendered HTML.
    """
    orig_lines = original.splitlines()
    tail_lines = tailored.splitlines()

    # Compute unified diff
    unified = "\n".join(
        difflib.unified_diff(
            orig_lines, tail_lines,
            fromfile="original.txt", tofile="tailored.txt",
            lineterm="",
        )
    )

    # Compute stats from opcodes
    matcher = difflib.SequenceMatcher(None, orig_lines, tail_lines)
    similarity_pct = matcher.ratio() * 100

    stats = DiffStats(similarity_pct=similarity_pct)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            stats.lines_unchanged += i2 - i1
        elif tag == "insert":
            stats.lines_added += j2 - j1
        elif tag == "delete":
            stats.lines_removed += i2 - i1
        elif tag == "replace":
            stats.lines_modified += max(i2 - i1, j2 - j1)

    # Word-level diff
    orig_words = _tokenize(original)
    tail_words = _tokenize(tailored)
    added_words = tail_words - orig_words
    removed_words = orig_words - tail_words
    stats.words_added = len(added_words)
    stats.words_removed = len(removed_words)
    stats.keywords_added = sorted(added_words)[:50]
    stats.keywords_removed = sorted(removed_words)[:50]

    # HTML diff
    html_diff_table = difflib.HtmlDiff(wrapcolumn=80).make_table(
        orig_lines, tail_lines,
        fromdesc="Original Resume", todesc="Tailored Resume",
        context=True, numlines=2,
    )

    # Summary
    summary_parts = []
    if stats.lines_added:
        summary_parts.append(f"+{stats.lines_added} lines added")
    if stats.lines_removed:
        summary_parts.append(f"-{stats.lines_removed} lines removed")
    if stats.lines_modified:
        summary_parts.append(f"~{stats.lines_modified} lines modified")
    if stats.words_added:
        summary_parts.append(f"+{stats.words_added} unique keywords")
    summary_parts.append(f"{similarity_pct:.1f}% similar")
    summary = " | ".join(summary_parts)

    return ResumeDiff(
        stats=stats,
        unified_diff=unified,
        html_diff=html_diff_table,
        summary=summary,
    )


def render_inline_diff_html(original: str, tailored: str) -> str:
    """Render a compact side-by-side HTML diff for Streamlit display."""
    diff = diff_resumes(original, tailored)
    style = """
    <style>
      .diff-container { font-family: 'Courier New', monospace; font-size: 12px; }
      .diff-summary { padding: 10px; background: #f0f4f8; border-left: 4px solid #2563eb; margin-bottom: 10px; border-radius: 4px; }
      .diff-added { background: #dcfce7; color: #166534; padding: 2px 4px; }
      .diff-removed { background: #fee2e2; color: #991b1b; padding: 2px 4px; text-decoration: line-through; }
      table.diff { width: 100%; border-collapse: collapse; }
      table.diff td { padding: 2px 6px; vertical-align: top; }
      table.diff .diff_header { background: #e5e7eb; font-weight: bold; }
      table.diff .diff_next { background: #f3f4f6; }
      table.diff .diff_add { background: #dcfce7; }
      table.diff .diff_sub { background: #fee2e2; }
      table.diff .diff_chg { background: #fef3c7; }
    </style>
    """
    summary_html = f"""
    <div class="diff-summary">
      <strong>📊 Diff Summary:</strong> {html.escape(diff.summary)}
      <br><strong>✅ Added Keywords ({len(diff.stats.keywords_added)}):</strong>
      {html.escape(', '.join(diff.stats.keywords_added[:30]) or '(none)')}
      <br><strong>⚠️ Removed Keywords ({len(diff.stats.keywords_removed)}):</strong>
      {html.escape(', '.join(diff.stats.keywords_removed[:30]) or '(none)')}
    </div>
    """
    return f'<div class="diff-container">{style}{summary_html}{diff.html_diff}</div>'


def keyword_diff(original: str, tailored: str) -> dict[str, Any]:
    """Just return the keyword-level differences (lightweight)."""
    orig_words = _tokenize(original)
    tail_words = _tokenize(tailored)
    return {
        "added": sorted(tail_words - orig_words),
        "removed": sorted(orig_words - tail_words),
        "common": sorted(orig_words & tail_words),
        "added_count": len(tail_words - orig_words),
        "removed_count": len(orig_words - tail_words),
    }
