"""Email digest via SMTP (password from macOS Keychain or SYLLARA_SMTP_PASSWORD)."""

from __future__ import annotations

import html
import os
import smtplib
import subprocess
from collections import defaultdict
from datetime import date
from email.message import EmailMessage

from .config import EmailConfig
from .models import Downloaded


def build_digest(items: list[Downloaded], today: date | None = None) -> tuple[str, str, str]:
    """Return (subject, plain text, html) grouped by course."""
    day = (today or date.today()).isoformat()
    if not items:
        return f"Scientia: no new files ({day})", "No new files today.", "<p>No new files today.</p>"

    by_course: dict[str, list[Downloaded]] = defaultdict(list)
    for d in items:
        by_course[d.entry.course].append(d)

    n = len(items)
    subject = f"Scientia: {n} new file{'s' if n != 1 else ''} ({day})"
    text, parts = [], []
    for course in sorted(by_course):
        text.append(f"\n{course}")
        parts.append(f"<h3>{html.escape(course)}</h3><ul>")
        for d in by_course[course]:
            tag = " (updated)" if d.updated else ""
            where = f"{d.entry.section} / " if d.entry.section else ""
            text.append(f"  - {where}{d.path.name}{tag}\n    {d.path}")
            parts.append(
                f"<li>{html.escape(where)}<a href=\"{html.escape(d.entry.url)}\">{html.escape(d.path.name)}</a>"
                f"{html.escape(tag)}<br><code>{html.escape(str(d.path))}</code>"
                + (f"<blockquote>{html.escape(d.summary)}</blockquote>" if d.summary else "")
                + "</li>"
            )
            if d.summary:
                text.append(f"    {d.summary}")
        parts.append("</ul>")
    return subject, "\n".join(text).lstrip(), "".join(parts)


def _password(conf: EmailConfig) -> str:
    if pw := os.environ.get("SYLLARA_SMTP_PASSWORD"):
        return pw
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", conf.keychain_service, "-a", conf.sender, "-w"],
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise RuntimeError(
            f"No SMTP password. Add it with: security add-generic-password -s {conf.keychain_service} "
            f"-a {conf.sender} -w"
        ) from e
    return out.stdout.strip()


def send(conf: EmailConfig, subject: str, text: str, html_body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = conf.sender
    msg["To"] = conf.to
    msg.set_content(text)
    msg.add_alternative(f"<html><body>{html_body}</body></html>", subtype="html")
    with smtplib.SMTP_SSL(conf.smtp_host, conf.smtp_port, timeout=30) as smtp:
        smtp.login(conf.sender, _password(conf))
        smtp.send_message(msg)


def send_relogin(conf: EmailConfig, login_url: str) -> None:
    send(
        conf,
        "Scientia: re-login needed",
        f"Your Scientia session expired (redirected to {login_url}).\nRun: syllara login",
        f"<p>Your Scientia session expired (redirected to <code>{html.escape(login_url)}</code>).</p>"
        "<p>Run <code>syllara login</code> on your Mac.</p>",
    )
