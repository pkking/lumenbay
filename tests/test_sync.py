"""Offline end-to-end tests with real SQLite spool and fake platform adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from lumenbay.archive import Archive, DeliveryState
from lumenbay.sync import Destination, PhotoSync
from lumenbay.wechat import ImageEvent

JPEG = b"\xff\xd8\xff" + b"new-image"


class FakeSource:
    def __init__(self, event: ImageEvent) -> None:
        self.event = event

    def poll(self, *, seen: Callable[[str], bool] | None = None) -> list[ImageEvent]:
        return [] if seen is not None and seen(self.event.message_id) else [self.event]


class FakeUploader:
    def __init__(self, fail: bool = False) -> None:
        self.uploads: list[tuple[str, str, bytes]] = []
        self.fail = fail

    def upload_images(
        self, *, group_id: str, album_id: str, album_name: str, paths: list[Path]
    ) -> object:
        self.uploads.append((group_id, album_id, paths[0].read_bytes()))
        if self.fail:
            raise TimeoutError("simulate reply lost after remote upload")
        return None


def make_sync(tmp_path: Path, uploader: FakeUploader) -> tuple[PhotoSync, Archive]:
    image = tmp_path / "photo.jpg"
    image.write_bytes(JPEG)
    archive = Archive(tmp_path / "archive.db", tmp_path / "spool")
    sync = PhotoSync(
        source_group="Authorized group",
        source=FakeSource(ImageEvent("Authorized group", "event1", image)),
        destination=Destination("qq1", "album1", "Photos"),
        uploader=uploader,
        archive=archive,
    )
    return sync, archive


def test_upload_accepted_once_without_false_verification(tmp_path: Path) -> None:
    uploader = FakeUploader()
    sync, archive = make_sync(tmp_path, uploader)
    assert sync.run_once().accepted == 1
    delivery = archive.get(1)
    assert delivery.state is DeliveryState.ACKNOWLEDGED
    assert delivery.quality == "unknown"
    assert sync.run_once().discovered == 0
    assert len(uploader.uploads) == 1
    assert uploader.uploads == [("qq1", "album1", JPEG)]


def test_lost_upload_reply_never_blindly_retries(tmp_path: Path) -> None:
    uploader = FakeUploader(fail=True)
    sync, archive = make_sync(tmp_path, uploader)
    assert sync.run_once().unknown == 1
    assert archive.get(1).state is DeliveryState.UNKNOWN
    assert sync.run_once().accepted == 0
    assert len(uploader.uploads) == 1
    assert archive.quarantine_interrupted() == 0


def test_only_matching_album_deliveries_are_submitted(tmp_path: Path) -> None:
    uploader = FakeUploader()
    sync, archive = make_sync(tmp_path, uploader)
    archive.ingest(
        source_group="elsewhere", message_id="event2", destination_group="qq2",
        album_id="album2", data=JPEG, quality="original",
    )
    assert sync.run_once().accepted == 1
    assert len(archive.pending(destination_group="qq2", album_id="album2")) == 1
    assert len(uploader.uploads) == 1


def test_missing_spool_is_not_submitted(tmp_path: Path) -> None:
    uploader = FakeUploader()
    sync, archive = make_sync(tmp_path, uploader)
    entry = archive.ingest(
        source_group="Authorized group", message_id="event1", destination_group="qq1",
        album_id="album1", data=JPEG, quality="unknown",
    )
    entry.path.unlink()
    stats = sync.run_once()
    assert stats.failed == 1
    assert uploader.uploads == []
