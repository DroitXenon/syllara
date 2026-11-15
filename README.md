# syllara

Checks your school's Scientia portal once a day, downloads new course files into
`~/Scientia/<Course>/<Section>/`, and emails you a digest.

## Setup

```sh
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/playwright install chromium

mkdir -p ~/.syllara && cp config.example.toml ~/.syllara/config.toml
# edit ~/.syllara/config.toml: base_url, courses, email to/from

# Gmail app password (https://myaccount.google.com/apppasswords), stored in Keychain:
security add-generic-password -s syllara-smtp -a you@gmail.com -w
```

## First run

```sh
.venv/bin/syllara login        # browser opens; finish SSO/MFA; press Enter
.venv/bin/syllara discover     # shows which course/file links the patterns match
.venv/bin/syllara list         # all files it would download
.venv/bin/syllara test-email   # check the email settings
.venv/bin/syllara check        # download + email digest
```

Schools lay out Scientia differently. If `discover` misses courses or files, adjust the
regexes in the `[scraper]` section of the config. `discover` saves the rendered pages to
`~/.syllara/discover/` and lists the JSON API calls it saw.

## Daily schedule

```sh
scripts/install-launchd.sh     # runs `syllara check` at 08:00; catches up after sleep
```

Logs: `~/.syllara/logs/`. If the SSO session expires, you'll get a "re-login needed"
email; run `syllara login` again.

## How it works

- **Session**: a persistent Chromium profile in `~/.syllara/profile` keeps your SSO cookies.
- **State**: `~/.syllara/state.db` (SQLite) records each downloaded URL and its SHA-256.
- **Changes**: if a known file's content changes, the new version is saved next to the old one
  as `name (YYYY-MM-DD).ext` and marked "updated" in the digest.
- **Summaries**: `syllara/summarize.py` is a stub to be replaced with Claude-API summaries later.

## Tests

```sh
.venv/bin/pytest
```
