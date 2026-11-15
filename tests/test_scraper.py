from pathlib import Path

from syllara.scraper import find_courses, find_files

FIX = Path(__file__).parent / "fixtures"


def test_find_courses_dedupes_and_ignores_subpages():
    html = (FIX / "dashboard.html").read_text()
    courses = find_courses(html, "https://scientia.school.edu/")
    assert courses == {
        "MATH101 Calculus I": "https://scientia.school.edu/courses/MATH101",
        "PHYS120 Mechanics": "https://scientia.school.edu/courses/PHYS120/",
    }


def test_find_courses_filter():
    html = (FIX / "dashboard.html").read_text()
    assert list(find_courses(html, "https://scientia.school.edu/", wanted=["phys"])) == ["PHYS120 Mechanics"]


def test_find_files_sections_names_and_urls():
    html = (FIX / "course.html").read_text()
    files = find_files(html, "https://scientia.school.edu/courses/MATH101", course="MATH101")
    assert [(f.section, f.name, f.url) for f in files] == [
        ("Week 1 & Intro", "Lecture 1 slides.pdf", "https://scientia.school.edu/files/101/Lecture1.pdf"),
        ("Week 1 & Intro", "Worksheet 1.docx", "https://cdn.school.edu/x/ws1.docx?token=abc"),
        ("Week 2", "Problem set 2", "https://scientia.school.edu/resources/88/download/"),
    ]
    assert all(f.course == "MATH101" for f in files)
