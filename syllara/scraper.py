"""Find courses and file links on Scientia pages.

Scientia's markup differs per school, so link matching is driven by regexes in the
`[scraper]` config section. Run `syllara discover` to see what the defaults pick up
and tune them; parsing works on rendered HTML so it can be tested against saved pages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin

from .models import FileEntry

DEFAULT_COURSE_PATTERN = r"/(course|courses|subject|subjects|unit|units|class|classes)/[^/?#]+/?(\?|$)"
DEFAULT_FILE_PATTERN = (
    r"\.(pdf|pptx?|docx?|xlsx?|key|zip|ipynb|py|java|c|txt|md|csv|mp4|m4a|png|jpe?g)(\?|$)"
    r"|/(download|downloads|file|files|resource|resources|attachment|attachments)/"
)
_HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


@dataclass(frozen=True)
class Link:
    href: str
    text: str
    section: str


class _LinkCollector(HTMLParser):
    """Collect <a href> links with their text and the nearest preceding heading."""

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[Link] = []
        self._section = ""
        self._heading: list[str] | None = None
        self._anchor: tuple[str, list[str], str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "base":
            href = dict(attrs).get("href")
            if href:
                self.base_url = urljoin(self.base_url, href)
        elif tag in _HEADINGS:
            self._heading = []
        elif tag == "a":
            a = dict(attrs)
            href = a.get("href")
            if href and not href.startswith(("javascript:", "mailto:", "#")):
                # Prefer the download attribute / title as a filename hint when present.
                hint = a.get("download") or a.get("title") or ""
                self._anchor = (urldefrag(urljoin(self.base_url, href))[0], [], hint)

    def handle_endtag(self, tag):
        if tag in _HEADINGS and self._heading is not None:
            text = _clean("".join(self._heading))
            if text:
                self._section = text
            self._heading = None
        elif tag == "a" and self._anchor is not None:
            href, parts, hint = self._anchor
            self.links.append(Link(href=href, text=_clean("".join(parts)) or _clean(hint), section=self._section))
            self._anchor = None

    def handle_data(self, data):
        if self._heading is not None:
            self._heading.append(data)
        if self._anchor is not None:
            self._anchor[1].append(data)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def parse_links(html: str, page_url: str) -> list[Link]:
    p = _LinkCollector(page_url)
    p.feed(html)
    p.close()
    return p.links


def find_courses(html: str, page_url: str, pattern: str = DEFAULT_COURSE_PATTERN,
                 wanted: list[str] | None = None) -> dict[str, str]:
    """Return {course name: url}. `wanted` filters by case-insensitive substring of name or url."""
    rx = re.compile(pattern, re.IGNORECASE)
    courses: dict[str, str] = {}
    for link in parse_links(html, page_url):
        if not rx.search(link.href) or not link.text:
            continue
        if wanted and not any(w.lower() in (link.text + " " + link.href).lower() for w in wanted):
            continue
        courses.setdefault(link.text, link.href)
    return courses


def find_files(html: str, page_url: str, course: str, pattern: str = DEFAULT_FILE_PATTERN) -> list[FileEntry]:
    rx = re.compile(pattern, re.IGNORECASE)
    seen: set[str] = set()
    files: list[FileEntry] = []
    for link in parse_links(html, page_url):
        if link.href in seen or not rx.search(link.href):
            continue
        seen.add(link.href)
        files.append(FileEntry(url=link.href, name=_filename(link), course=course, section=link.section))
    return files


def _filename(link: Link) -> str:
    """Use the link text, adding the URL's extension if the text lacks one."""
    path = link.href.split("?", 1)[0].rstrip("/")
    url_name = path.rsplit("/", 1)[-1]
    ext_match = re.search(r"\.[A-Za-z0-9]{1,5}$", url_name)
    name = link.text or url_name or "file"
    if ext_match and not name.lower().endswith(ext_match.group(0).lower()):
        name += ext_match.group(0)
    return name
