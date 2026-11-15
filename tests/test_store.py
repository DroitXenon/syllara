from pathlib import Path

from syllara.models import FileEntry
from syllara.store import Store


def entry(version: str = "v1") -> FileEntry:
    return FileEntry(url="https://x/f/1", name="Week 1.pdf", course="MATH101", section="Lectures",
                     remote_version=version)


def test_new_entry_needs_download(tmp_path: Path):
    store = Store(tmp_path / "s.db")
    assert store.needs_download(entry())


def test_recorded_entry_is_skipped(tmp_path: Path):
    store = Store(tmp_path / "s.db")
    store.record(entry(), tmp_path / "a.pdf", "abc", 10)
    assert not store.needs_download(entry())


def test_changed_version_needs_download(tmp_path: Path):
    store = Store(tmp_path / "s.db")
    store.record(entry("v1"), tmp_path / "a.pdf", "abc", 10)
    assert store.needs_download(entry("v2"))


def test_blank_version_never_counts_as_change(tmp_path: Path):
    store = Store(tmp_path / "s.db")
    store.record(entry("v1"), tmp_path / "a.pdf", "abc", 10)
    assert not store.needs_download(entry(""))


def test_record_upserts_and_keeps_first_seen(tmp_path: Path):
    store = Store(tmp_path / "s.db")
    store.record(entry("v1"), tmp_path / "a.pdf", "abc", 10)
    first = store.get(entry().url)["first_seen"]
    store.record(entry("v2"), tmp_path / "b.pdf", "def", 20)
    row = store.get(entry().url)
    assert (row["sha256"], row["remote_version"], row["first_seen"]) == ("def", "v2", first)


def test_touch_version(tmp_path: Path):
    store = Store(tmp_path / "s.db")
    store.record(entry("v1"), tmp_path / "a.pdf", "abc", 10)
    store.touch_version(entry("v2"))
    assert not store.needs_download(entry("v2"))
