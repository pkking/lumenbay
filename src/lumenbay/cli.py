"""Local CLI for safe, explicitly authorized photo archiving."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from lumenbay import __version__
from lumenbay.archive import Archive
from lumenbay.config import Settings


def _run(config_path: Path, *, once: bool) -> int:
    # Import desktop/UI adapters only after explicit user opt-in.
    from lumenbay.napcat import NapCatAlbumClient
    from lumenbay.sync import Destination, PhotoSync
    from lumenbay.wechat import WxAutoImageSource

    settings = Settings.load(config_path)
    uploader = NapCatAlbumClient(
        base_url=settings.napcat_base_url,
        access_token=os.environ.get("LUMENBAY_NAPCAT_TOKEN", ""),
    )
    album = uploader.find_album(settings.qq_group_id, settings.qq_album_name)
    source = WxAutoImageSource.from_desktop(settings.wechat_group)
    archive = Archive(settings.database, settings.spool)
    archive.quarantine_interrupted()
    sync = PhotoSync(
        source_group=settings.wechat_group,
        source=source,
        destination=Destination(settings.qq_group_id, album.id, album.name),
        uploader=uploader,
        archive=archive,
    )
    while True:
        try:
            stats = sync.run_once()
            print(json.dumps(asdict(stats), sort_keys=True), flush=True)
            if once:
                return 2 if stats.unknown or stats.failed else 0
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            # Avoid leaking group/member identifiers, paths or credentials.
            print(f"Sync failed: {type(exc).__name__}", file=sys.stderr, flush=True)
            if once:
                return 2
        time.sleep(settings.interval_seconds)


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point; live uploads require an explicit switch."""
    parser = argparse.ArgumentParser(
        prog="lumenbay",
        description="Archive photos from an authorized WeChat group to a QQ group album.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command")
    run = commands.add_parser("run", help="Read WeChat and submit photos to QQ album")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--execute", action="store_true", help="Allow live group-album uploads")
    run.add_argument("--once", action="store_true", help="Process a single visible-message poll")
    status = commands.add_parser("status", help="Show locally persisted delivery counts")
    status.add_argument("--config", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "run":
        if not args.execute:
            parser.error("Live operations require --execute and authorized test groups")
        return _run(args.config, once=args.once)
    if args.command == "status":
        settings = Settings.load(args.config)
        store = Archive(settings.database, settings.spool)
        print(json.dumps(store.counts(destination_group=settings.qq_group_id), sort_keys=True))
        return 0
    parser.print_help()
    return 0
