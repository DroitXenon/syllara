from datetime import date
from pathlib import Path

from syllara.models import Downloaded, FileEntry
from syllara.notify import build_digest


def dl(course, name, section="", updated=False):
    e = FileEntry(url=f"https://x/{name}", name=name, course=course, section=section)
    return Downloaded(e, Path("/S") / course / name, "h", 1, updated)


def test_digest_groups_by_course_and_marks_updates():
    subject, text, html = build_digest(
        [dl("PHYS", "b.pdf"), dl("MATH", "a.pdf", "Week 1"), dl("MATH", "c.pdf", updated=True)],
        date(2026, 11, 15),
    )
    assert subject == "Scientia: 3 new files (2026-11-15)"
    assert text.index("MATH") < text.index("PHYS")
    assert "Week 1 / a.pdf" in text and "c.pdf (updated)" in text
    assert "<h3>MATH</h3>" in html and 'href="https://x/a.pdf"' in html


def test_empty_digest():
    assert build_digest([], date(2026, 11, 15))[0] == "Scientia: no new files (2026-11-15)"
