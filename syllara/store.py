"""SQLite record of files already downloaded."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import FileEntry

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    url            TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    course         TEXT NOT NULL,
    section        TEXT NOT NULL,
    remote_version TEXT NOT NULL,
    sha256         TEXT NOT NULL,
    size           INTEGER NOT NULL,
    path           TEXT NOT NULL,
    first_seen     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def get(self, url: str) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM files WHERE url = ?", (url,)).fetchone()

    def needs_download(self, entry: FileEntry) -> bool:
        row = self.get(entry.url)
        if row is None:
            return True
        return bool(entry.remote_version) and entry.remote_version != row["remote_version"]

    def record(self, entry: FileEntry, path: Path, sha256: str, size: int) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.db.execute(
            """
            INSERT INTO files (url, name, course, section, remote_version, sha256, size, path, first_seen, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                name = excluded.name, course = excluded.course, section = excluded.section,
                remote_version = excluded.remote_version, sha256 = excluded.sha256,
                size = excluded.size, path = excluded.path, updated_at = excluded.updated_at
            """,
            (entry.url, entry.name, entry.course, entry.section, entry.remote_version,
             sha256, size, str(path), now, now),
        )
        self.db.commit()

    def touch_version(self, entry: FileEntry) -> None:
        """Remote marker changed but content is identical: just remember the new marker."""
        self.db.execute("UPDATE files SET remote_version = ? WHERE url = ?", (entry.remote_version, entry.url))
        self.db.commit()

    def close(self) -> None:
        self.db.close()
