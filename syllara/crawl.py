"""Walk Scientia in a logged-in browser context and list file entries."""

from __future__ import annotations

import logging
from urllib.parse import urljoin

from playwright.sync_api import BrowserContext, Page

from .browser import SessionExpired, looks_like_login, open_portal
from .config import Config
from .models import FileEntry
from .scraper import find_courses, find_files

log = logging.getLogger(__name__)


def _load(page: Page, url: str, base_url: str) -> str:
    page.goto(url, wait_until="networkidle")
    if looks_like_login(page.url, base_url):
        raise SessionExpired(page.url)
    return page.content()


def list_courses(ctx: BrowserContext, conf: Config) -> dict[str, str]:
    page = open_portal(ctx, conf.base_url)
    sc = conf.scraper
    html = page.content() if sc.courses_url == conf.base_url else _load(page, sc.courses_url, conf.base_url)
    return find_courses(html, page.url, sc.course_pattern, conf.courses or None)


def list_files(ctx: BrowserContext, conf: Config) -> list[FileEntry]:
    courses = list_courses(ctx, conf)
    if not courses:
        log.warning("No courses matched; check [scraper].course_pattern with `syllara discover`.")
    page = ctx.pages[0]
    entries: dict[str, FileEntry] = {}
    for name, url in courses.items():
        pages = [url] + [urljoin(url.rstrip("/") + "/", sub) for sub in conf.scraper.course_subpaths]
        for page_url in pages:
            try:
                html = _load(page, page_url, conf.base_url)
            except SessionExpired:
                raise
            except Exception as e:  # one broken course page shouldn't stop the run
                log.warning("Could not load %s: %s", page_url, e)
                continue
            for f in find_files(html, page.url, name, conf.scraper.file_pattern):
                entries.setdefault(f.url, f)
    return list(entries.values())
