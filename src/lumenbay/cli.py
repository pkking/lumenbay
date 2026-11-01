"""Command-line entry point. No sync commands are implemented yet."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from lumenbay import __version__


def main(argv: Sequence[str] | None = None) -> int:
    """Display the bootstrap CLI help or version."""
    parser = argparse.ArgumentParser(
        prog="lumenbay",
        description="Archive photos from WeChat groups to QQ group albums (planned).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.parse_args(argv)
    parser.print_help()
    return 0
