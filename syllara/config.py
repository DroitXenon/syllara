"""Load ~/.syllara/config.toml into typed settings."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .scraper import DEFAULT_COURSE_PATTERN, DEFAULT_FILE_PATTERN

HOME = Path(os.environ.get("SYLLARA_HOME", "~/.syllara")).expanduser()
CONFIG_PATH = HOME / "config.toml"
PROFILE_DIR = HOME / "profile"
DB_PATH = HOME / "state.db"
LOG_DIR = HOME / "logs"
DISCOVER_DIR = HOME / "discover"


@dataclass
class EmailConfig:
    enabled: bool = True
    to: str = ""
    sender: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    keychain_service: str = "syllara-smtp"
    send_when_empty: bool = False


@dataclass
class ScraperConfig:
    courses_url: str = ""  # page listing your courses; defaults to base_url
    course_pattern: str = DEFAULT_COURSE_PATTERN
    file_pattern: str = DEFAULT_FILE_PATTERN
    course_subpaths: list[str] = field(default_factory=list)  # extra pages per course, e.g. ["resources"]


@dataclass
class Config:
    base_url: str
    courses: list[str] = field(default_factory=list)
    scraper: ScraperConfig = field(default_factory=ScraperConfig)
    download_root: Path = Path("~/Scientia").expanduser()
    email: EmailConfig = field(default_factory=EmailConfig)


def load(path: Path = CONFIG_PATH) -> Config:
    if not path.exists():
        raise SystemExit(f"No config at {path}. Copy config.example.toml there and edit it.")
    data = tomllib.loads(path.read_text())
    sci = data.get("scientia", {})
    email = data.get("email", {})
    scr = data.get("scraper", {})
    base_url = sci["base_url"].rstrip("/")
    return Config(
        base_url=base_url,
        courses=list(sci.get("courses", [])),
        scraper=ScraperConfig(
            courses_url=scr.get("courses_url") or base_url,
            course_pattern=scr.get("course_pattern", DEFAULT_COURSE_PATTERN),
            file_pattern=scr.get("file_pattern", DEFAULT_FILE_PATTERN),
            course_subpaths=list(scr.get("course_subpaths", [])),
        ),
        download_root=Path(data.get("storage", {}).get("download_root", "~/Scientia")).expanduser(),
        email=EmailConfig(
            enabled=email.get("enabled", True),
            to=email.get("to", ""),
            sender=email.get("from", ""),
            smtp_host=email.get("smtp_host", "smtp.gmail.com"),
            smtp_port=int(email.get("smtp_port", 465)),
            keychain_service=email.get("keychain_service", "syllara-smtp"),
            send_when_empty=email.get("send_when_empty", False),
        ),
    )
