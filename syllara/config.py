"""Load ~/.syllara/config.toml into typed settings."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

HOME = Path(os.environ.get("SYLLARA_HOME", "~/.syllara")).expanduser()
CONFIG_PATH = HOME / "config.toml"
PROFILE_DIR = HOME / "profile"
DB_PATH = HOME / "state.db"
LOG_DIR = HOME / "logs"


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
class Config:
    base_url: str
    courses: list[str] = field(default_factory=list)
    download_root: Path = Path("~/Scientia").expanduser()
    email: EmailConfig = field(default_factory=EmailConfig)


def load(path: Path = CONFIG_PATH) -> Config:
    if not path.exists():
        raise SystemExit(f"No config at {path}. Copy config.example.toml there and edit it.")
    data = tomllib.loads(path.read_text())
    sci = data.get("scientia", {})
    email = data.get("email", {})
    return Config(
        base_url=sci["base_url"].rstrip("/"),
        courses=list(sci.get("courses", [])),
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
