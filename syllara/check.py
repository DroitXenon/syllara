"""The daily job: find new files, download, organize, record, email."""

from __future__ import annotations

import hashlib
import logging
import mimetypes
import re
from pathlib import Path

from playwright.sync_api import BrowserContext

from . import notify
from .browser import SessionExpired, fetch, open_context
from .config import DB_PATH, Config
from .crawl import list_files
from .models import Downloaded, FileEntry
from .organizer import available_path, sanitize, target_path
from .store import Store
from .summarize import summarize

log = logging.getLogger(__name__)


def _with_extension(name: str, headers: dict[str, str]) -> str:
    """Use the server's filename/content-type when the link text has no extension."""
    if re.search(r"\.[A-Za-z0-9]{1,5}$", name):
        return name
    disp = headers.get("content-disposition", "")
    m = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", disp, re.IGNORECASE)
    if m and (ext := Path(m.group(1)).suffix):
        return name + ext
    ctype = headers.get("content-type", "").split(";")[0].strip()
    return name + (mimetypes.guess_extension(ctype) or "") if ctype and ctype != "text/html" else name


def download_one(ctx: BrowserContext, conf: Config, store: Store, entry: FileEntry) -> Downloaded | None:
    body, headers = fetch(ctx, entry.url)
    digest = hashlib.sha256(body).hexdigest()
    previous = store.get(entry.url)
    if previous is not None and previous["sha256"] == digest:
        store.touch_version(entry)
        return None

    entry = FileEntry(entry.url, sanitize(_with_extension(entry.name, headers)), entry.course,
                      entry.section, entry.remote_version)
    target = target_path(conf.download_root, entry)
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == digest:
        path = target  # already on disk (e.g. state DB was reset); don't write a duplicate
    else:
        path = available_path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".part")
        tmp.write_bytes(body)
        tmp.rename(path)
        log.info("Saved %s", path)
    store.record(entry, path, digest, len(body))
    return Downloaded(entry, path, digest, len(body), updated=previous is not None, summary=summarize(path))


def run(conf: Config, db_path: Path = DB_PATH, send_email: bool = True) -> int:
    store = Store(db_path)
    downloaded: list[Downloaded] = []
    failures = 0
    try:
        with open_context() as ctx:
            entries = list_files(ctx, conf)
            log.info("Found %d files on Scientia", len(entries))
            for entry in entries:
                if not store.needs_download(entry):
                    continue
                try:
                    if d := download_one(ctx, conf, store, entry):
                        downloaded.append(d)
                except SessionExpired:
                    raise
                except Exception as e:
                    failures += 1
                    log.warning("Failed to download %s: %s", entry.url, e)
    except SessionExpired as e:
        log.error("Session expired (%s); run `syllara login`", e)
        if send_email and conf.email.enabled:
            notify.send_relogin(conf.email, str(e))
        return 2
    finally:
        store.close()

    log.info("Downloaded %d new file(s), %d failure(s)", len(downloaded), failures)
    if send_email and conf.email.enabled and (downloaded or conf.email.send_when_empty):
        notify.send(conf.email, *notify.build_digest(downloaded))
        log.info("Digest emailed to %s", conf.email.to)
    return 1 if failures else 0
