"""Shared data types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileEntry:
    """A downloadable file as listed on Scientia."""

    url: str
    name: str
    course: str
    section: str = ""
    # Whatever Scientia shows as a version marker (date string, size, etag); used for change detection.
    remote_version: str = ""


@dataclass(frozen=True)
class Downloaded:
    entry: FileEntry
    path: Path
    sha256: str
    size: int
    updated: bool  # True if this replaces an earlier version of the same file
    summary: str | None = None
