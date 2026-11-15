"""Decide where a downloaded file lives on disk."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .models import FileEntry

_UNSAFE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def sanitize(part: str) -> str:
    cleaned = _UNSAFE.sub("_", re.sub(r"\s+", " ", part)).strip().strip(".").strip()
    return cleaned[:150] or "untitled"


def target_path(root: Path, entry: FileEntry) -> Path:
    parts = [sanitize(entry.course)]
    if entry.section:
        parts.append(sanitize(entry.section))
    return root.joinpath(*parts, sanitize(entry.name))


def available_path(path: Path, today: date | None = None) -> Path:
    """Return `path`, or `name (YYYY-MM-DD).ext` (plus a counter) if it already exists."""
    if not path.exists():
        return path
    stamp = (today or date.today()).isoformat()
    candidate = path.with_name(f"{path.stem} ({stamp}){path.suffix}")
    n = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem} ({stamp} {n}){path.suffix}")
        n += 1
    return candidate
