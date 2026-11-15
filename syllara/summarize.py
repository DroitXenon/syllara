"""Summary hook. Returns None until a summarizer (e.g. Claude API) is wired in."""

from __future__ import annotations

from pathlib import Path


def summarize(path: Path) -> str | None:
    return None
