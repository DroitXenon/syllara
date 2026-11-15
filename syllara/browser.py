"""Persistent Playwright browser profile so SSO/MFA is done once by hand."""

from __future__ import annotations

import re
from contextlib import contextmanager
from typing import Iterator
from urllib.parse import urlparse

from playwright.sync_api import BrowserContext, Page, sync_playwright

from .config import PROFILE_DIR

# Hosts/paths that mean we got bounced to an identity provider instead of Scientia.
_LOGIN_HINT = re.compile(
    r"login\.microsoftonline\.com|accounts\.google\.com|okta\.com|duosecurity\.com"
    r"|/(login|signin|sso|saml2?|idp|cas|shibboleth)(/|\?|$)",
    re.IGNORECASE,
)


class SessionExpired(Exception):
    """Scientia redirected to the SSO login page; the user needs to run `syllara login`."""


@contextmanager
def open_context(headless: bool = True) -> Iterator[BrowserContext]:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=headless,
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
        )
        try:
            yield ctx
        finally:
            ctx.close()


def looks_like_login(url: str, base_url: str) -> bool:
    if urlparse(url).hostname != urlparse(base_url).hostname:
        return True
    return bool(_LOGIN_HINT.search(url))


def open_portal(ctx: BrowserContext, base_url: str) -> Page:
    """Open Scientia's landing page, raising SessionExpired if SSO kicks in."""
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(base_url, wait_until="networkidle")
    if looks_like_login(page.url, base_url):
        raise SessionExpired(page.url)
    return page


def interactive_login(base_url: str) -> bool:
    """Open a visible browser and wait for the user to finish SSO. Returns True on success."""
    with open_context(headless=False) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(base_url)
        print("Complete the school login in the browser window.")
        print("Waiting until you land back on Scientia (up to 5 minutes)...")
        try:
            page.wait_for_url(lambda u: not looks_like_login(u, base_url), timeout=300_000)
            page.wait_for_load_state("networkidle")
        except Exception:
            print("Timed out waiting for login.")
            return False
        input("Logged in. Press Enter to save the session and close the browser...")
        return True


def fetch_bytes(ctx: BrowserContext, url: str) -> bytes:
    """Download a file using the logged-in session's cookies."""
    resp = ctx.request.get(url, timeout=120_000)
    if not resp.ok:
        raise RuntimeError(f"GET {url} -> HTTP {resp.status}")
    # Files may be served from a CDN on another host, so only treat known IdP/login URLs as expiry.
    if _LOGIN_HINT.search(resp.url):
        raise SessionExpired(resp.url)
    return resp.body()
