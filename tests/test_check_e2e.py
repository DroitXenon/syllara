"""End-to-end: run the real crawler + downloader against a local fake Scientia."""

import sqlite3
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from syllara import browser, check
from syllara.config import Config, EmailConfig
from syllara.store import Store

DASHBOARD = '<h2>Courses</h2><a href="/courses/MATH101/">MATH101 Calculus</a>'
COURSE = """<h1>MATH101</h1>
<h3>Week 1</h3><a href="/files/l1.pdf">Lecture 1</a>
<h3>Week 2</h3><a href="/download/ps2">Problem set 2</a>"""


@pytest.fixture
def site(tmp_path: Path):
    root = tmp_path / "site"
    (root / "courses" / "MATH101").mkdir(parents=True)
    (root / "files").mkdir()
    (root / "download").mkdir()
    (root / "index.html").write_text(DASHBOARD)
    (root / "courses" / "MATH101" / "index.html").write_text(COURSE)
    (root / "files" / "l1.pdf").write_bytes(b"%PDF-1.4 lecture one")
    (root / "download" / "ps2").write_bytes(b"%PDF-1.4 problem set")

    class Handler(SimpleHTTPRequestHandler):
        def guess_type(self, path):
            return "application/pdf" if path.endswith("ps2") else super().guess_type(path)

        def log_message(self, *a):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield root, f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_check_downloads_once_then_detects_updates(site, tmp_path, monkeypatch):
    root, url = site
    monkeypatch.setattr(browser, "PROFILE_DIR", tmp_path / "profile")
    conf = Config(base_url=url, download_root=tmp_path / "Scientia", email=EmailConfig(enabled=False))
    db = tmp_path / "state.db"

    assert check.run(conf, db_path=db) == 0
    lecture = tmp_path / "Scientia" / "MATH101 Calculus" / "Week 1" / "Lecture 1.pdf"
    pset = tmp_path / "Scientia" / "MATH101 Calculus" / "Week 2" / "Problem set 2.pdf"
    assert lecture.read_bytes() == b"%PDF-1.4 lecture one"
    assert pset.exists()

    # Second run: nothing new.
    before = sorted(p.name for p in (tmp_path / "Scientia").rglob("*"))
    assert check.run(conf, db_path=db) == 0
    assert sorted(p.name for p in (tmp_path / "Scientia").rglob("*")) == before

    # Forget one file: it is fetched again, but identical content isn't duplicated on disk.
    with sqlite3.connect(db) as c:
        c.execute("DELETE FROM files WHERE url LIKE '%l1.pdf'")
    assert check.run(conf, db_path=db) == 0
    assert [p.name for p in lecture.parent.iterdir()] == ["Lecture 1.pdf"]

    # Content changes under a new URL version: saved alongside as a dated copy.
    (root / "files" / "l1.pdf").write_bytes(b"%PDF-1.4 lecture one v2")
    with sqlite3.connect(db) as c:
        c.execute("UPDATE files SET remote_version = 'old' WHERE url LIKE '%l1.pdf'")
    monkeypatch.setattr(Store, "needs_download", lambda self, e: "l1.pdf" in e.url)
    assert check.run(conf, db_path=db) == 0
    names = sorted(p.name for p in lecture.parent.iterdir())
    assert len(names) == 2 and names[0].startswith("Lecture 1 (") and names[1] == "Lecture 1.pdf"
