"""Storage invariants; all tests are offline and use temporary files."""

from __future__ import annotations

from pathlib import Path

import pytest

from lumenbay.archive import Archive, DeliveryState

JPEG = b"\xff\xd8\xff" + b"example-original-image"


def make_archive(tmp_path: Path) -> Archive:
    return Archive(tmp_path / "data" / "archive.sqlite3", tmp_path / "spool")


def record(
    store: Archive,
    message_id: str = "m1",
    destination_group: str = "qq1",
    data: bytes = JPEG,
) -> int:
    return store.ingest(
        source_group="wx1",
        message_id=message_id,
        destination_group=destination_group,
        album_id="album",
        data=data,
        quality="original",
    ).id


def test_replayed_event_and_repeated_content_share_delivery(tmp_path: Path) -> None:
    store = make_archive(tmp_path)
    first = record(store)
    assert record(store) == first
    assert record(store, "m2") == first
    assert len(store.pending()) == 1
    assert store.get(first).path.read_bytes() == JPEG


def test_same_photo_in_another_album_scope_is_separate(tmp_path: Path) -> None:
    store = make_archive(tmp_path)
    assert record(store) != record(store, "m2", destination_group="qq2")


def test_restart_and_ambiguous_upload_never_requeue(tmp_path: Path) -> None:
    store = make_archive(tmp_path)
    first = record(store)
    claimed = store.claim(first)
    assert claimed.attempts == 1
    restarted = make_archive(tmp_path)
    assert restarted.quarantine_interrupted() == 1
    assert restarted.get(first).state is DeliveryState.UNKNOWN
    assert restarted.pending() == []
    with pytest.raises(ValueError, match="not claimable"):
        restarted.claim(first)
    verified = restarted.mark_verified(first, "remote-photo-id")
    assert verified.state is DeliveryState.VERIFIED
    assert verified.remote_reference == "remote-photo-id"


def test_definite_failure_can_retry(tmp_path: Path) -> None:
    store = make_archive(tmp_path)
    photo = record(store)
    store.claim(photo)
    store.mark_failed(photo)
    assert store.claim(photo).attempts == 2
    assert store.mark_verified(photo, "remote").state is DeliveryState.VERIFIED
    assert store.pending() == []


def test_validation_and_invalid_transition(tmp_path: Path) -> None:
    store = make_archive(tmp_path)
    with pytest.raises(ValueError, match="image"):
        store.ingest(
            source_group="wx1",
            message_id="m1",
            destination_group="q1",
            album_id="a1",
            data=b"not a picture",
            quality="original",
        )
    photo = record(store)
    with pytest.raises(ValueError, match="Invalid"):
        store.mark_verified(photo, "remote")
    with pytest.raises(ValueError, match="quality"):
        store.ingest(
            source_group="wx1",
            message_id="m2",
            destination_group="q1",
            album_id="a1",
            data=JPEG,
            quality="invalid",
        )


def test_destination_filter_and_acknowledgement(tmp_path: Path) -> None:
    store = make_archive(tmp_path)
    first = record(store, "a", "qq1")
    second = record(store, "b", "qq2")
    assert [x.id for x in store.pending(destination_group="qq1", album_id="album")] == [first]
    assert [x.id for x in store.pending(destination_group="qq2", album_id="album")] == [second]
    assert store.has_event(
        source_group="wx1", message_id="a", destination_group="qq1", album_id="album"
    )
    assert not store.has_event(
        source_group="wx1", message_id="a", destination_group="qq2", album_id="album"
    )
    store.claim(first)
    acknowledged = store.mark_acknowledged(first)
    assert acknowledged.state is DeliveryState.ACKNOWLEDGED
    assert store.pending(destination_group="qq1") == []
    with pytest.raises(ValueError, match="not claimable"):
        store.claim(first)
    assert store.mark_verified(first, "remote-later").state is DeliveryState.VERIFIED
