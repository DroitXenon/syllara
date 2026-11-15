"""Command-line entry point: `syllara login | discover | list | check | test-email`."""

from __future__ import annotations

import argparse
import sys

from . import config as cfg
from .browser import interactive_login


def cmd_login(conf: cfg.Config, _args) -> int:
    return 0 if interactive_login(conf.base_url) else 1


COMMANDS = {
    "login": (cmd_login, "Open a browser to sign in to Scientia (SSO/MFA) and save the session"),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="syllara", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, (_, help_text) in COMMANDS.items():
        sub.add_parser(name, help=help_text)
    args = parser.parse_args(argv)
    conf = cfg.load()
    return COMMANDS[args.command][0](conf, args)


if __name__ == "__main__":
    sys.exit(main())
