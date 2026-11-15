"""Command-line entry point: `syllara login | discover | list | check | test-email`."""

from __future__ import annotations

import argparse
import sys

from . import config as cfg
from .browser import SessionExpired, interactive_login, open_context, open_portal
from .crawl import list_courses, list_files
from .scraper import find_courses, find_files, parse_links


def cmd_login(conf: cfg.Config, _args) -> int:
    return 0 if interactive_login(conf.base_url) else 1


def cmd_discover(conf: cfg.Config, _args) -> int:
    """Save rendered pages and print what the current patterns match, to help tune [scraper]."""
    out = cfg.DISCOVER_DIR
    out.mkdir(parents=True, exist_ok=True)
    api_calls: list[str] = []
    with open_context() as ctx:
        ctx.on("response", lambda r: api_calls.append(f"{r.status} {r.url}")
               if "json" in (r.headers.get("content-type") or "") else None)
        page = open_portal(ctx, conf.base_url)
        if conf.scraper.courses_url != conf.base_url:
            page.goto(conf.scraper.courses_url, wait_until="networkidle")
        html = page.content()
        (out / "courses.html").write_text(html)
        page.screenshot(path=str(out / "courses.png"), full_page=True)
        courses = find_courses(html, page.url, conf.scraper.course_pattern, conf.courses or None)
        print(f"Saved {out / 'courses.html'}\n\nCourses matched ({len(courses)}):")
        for name, url in courses.items():
            print(f"  {name}  ->  {url}")
        if not courses:
            print("  (none) All links on the page:")
            for link in parse_links(html, page.url):
                print(f"    {link.text[:50]!r:52} {link.href}")
            return 1

        name, url = next(iter(courses.items()))
        page.goto(url, wait_until="networkidle")
        html = page.content()
        (out / "course.html").write_text(html)
        page.screenshot(path=str(out / "course.png"), full_page=True)
        files = find_files(html, page.url, name, conf.scraper.file_pattern)
        print(f"\nSaved {out / 'course.html'}\n\nFiles matched in {name!r} ({len(files)}):")
        for f in files:
            print(f"  [{f.section}] {f.name}  ->  {f.url}")
        print("\nOther links on that page (not matched as files):")
        matched = {f.url for f in files}
        for link in parse_links(html, page.url):
            if link.href not in matched:
                print(f"    {link.text[:50]!r:52} {link.href}")
    if api_calls:
        print("\nJSON API calls seen (an API may be more robust than HTML scraping):")
        for call in dict.fromkeys(api_calls):
            print(f"  {call}")
    return 0


def cmd_list(conf: cfg.Config, _args) -> int:
    with open_context() as ctx:
        files = list_files(ctx, conf)
    for f in files:
        print(f"{f.course} / {f.section or '-'} / {f.name}\n    {f.url}")
    print(f"\n{len(files)} files")
    return 0


COMMANDS = {
    "login": (cmd_login, "Open a browser to sign in to Scientia (SSO/MFA) and save the session"),
    "discover": (cmd_discover, "Save Scientia pages and show what the scraper patterns match"),
    "list": (cmd_list, "List files found on Scientia without downloading"),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="syllara", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, (_, help_text) in COMMANDS.items():
        sub.add_parser(name, help=help_text)
    args = parser.parse_args(argv)
    conf = cfg.load()
    try:
        return COMMANDS[args.command][0](conf, args)
    except SessionExpired:
        print("Scientia session expired. Run `syllara login`.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
