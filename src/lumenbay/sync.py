"""One-group, one-album delivery orchestration; no implicit live connectivity."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from lumenbay.archive import Archive
from lumenbay.wechat import ImageEvent


class ImageSource(Protocol):
    def poll(self, *, seen: Callable[[str], bool] | None = None) -> list[ImageEvent]: ...


class AlbumUploader(Protocol):
    def upload_images(
        self, *, group_id: str, album_id: str, album_name: str, paths: list[Path]
    ) -> object: ...


@dataclass(frozen=True)
class Destination:
    group_id: str
    album_id: str
    album_name: str


@dataclass(frozen=True)
class SyncStats:
    discovered: int = 0
    accepted: int = 0
    unknown: int = 0
    failed: int = 0


class PhotoSync:
    """Ingest visible events first, then submit destination-scoped pending media."""

    def __init__(
        self,
        *,
        source_group: str,
        source: ImageSource,
        destination: Destination,
        uploader: AlbumUploader,
        archive: Archive,
    ) -> None:
        if not all((source_group, destination.group_id, destination.album_id, destination.album_name)):
            raise ValueError("Source and destination must be explicitly configured")
        self.source_group = source_group
        self.source = source
        self.destination = destination
        self.uploader = uploader
        self.archive = archive

    def run_once(self) -> SyncStats:
        def seen(identity: str) -> bool:
            return self.archive.has_event(
                source_group=self.source_group,
                message_id=identity,
                destination_group=self.destination.group_id,
                album_id=self.destination.album_id,
            )

        events = self.source.poll(seen=seen)
        discovered = 0
        for event in events:
            if event.source_group != self.source_group:
                raise ValueError("Source adapter returned a message from the wrong group")
            self.archive.ingest(
                source_group=event.source_group,
                message_id=event.message_id,
                destination_group=self.destination.group_id,
                album_id=self.destination.album_id,
                data=event.path.read_bytes(),
                quality=event.quality,
            )
            discovered += 1

        accepted = unknown = failed = 0
        for delivery in self.archive.pending(
            destination_group=self.destination.group_id,
            album_id=self.destination.album_id,
        ):
            claimed = self.archive.claim(delivery.id)
            if not claimed.path.is_file():
                self.archive.mark_failed(claimed.id)
                failed += 1
                continue
            try:
                self.uploader.upload_images(
                    group_id=self.destination.group_id,
                    album_id=self.destination.album_id,
                    album_name=self.destination.album_name,
                    paths=[claimed.path],
                )
            except Exception:
                # Even an HTTP error can occur after remote commit. Do not
                # retry blindly or log sensitive transport exception details.
                self.archive.mark_unknown(claimed.id)
                unknown += 1
            else:
                # NapCat returns no stable remote media identity for these
                # uploads; an HTTP acknowledgement is not VERIFIED.
                self.archive.mark_acknowledged(claimed.id)
                accepted += 1
        return SyncStats(discovered=discovered, accepted=accepted, unknown=unknown, failed=failed)
