from datetime import date
from pathlib import Path

from syllara.models import FileEntry
from syllara.organizer import available_path, sanitize, target_path


def test_sanitize_strips_path_chars():
    assert sanitize("a/b:c*d?.pdf") == "a_b_c_d_.pdf"
    assert sanitize("  ..  ") == "untitled"
    assert sanitize("x  \n y") == "x y"


def test_target_path_layout(tmp_path: Path):
    e = FileEntry(url="u", name="Notes.pdf", course="CS 101: Intro", section="Week 2")
    assert target_path(tmp_path, e) == tmp_path / "CS 101_ Intro" / "Week 2" / "Notes.pdf"


def test_target_path_without_section(tmp_path: Path):
    e = FileEntry(url="u", name="Notes.pdf", course="CS101")
    assert target_path(tmp_path, e) == tmp_path / "CS101" / "Notes.pdf"


def test_available_path_versions(tmp_path: Path):
    p = tmp_path / "Notes.pdf"
    assert available_path(p) == p
    p.touch()
    d = date(2026, 11, 15)
    v1 = available_path(p, d)
    assert v1.name == "Notes (2026-11-15).pdf"
    v1.touch()
    assert available_path(p, d).name == "Notes (2026-11-15 2).pdf"
