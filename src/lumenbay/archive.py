"""Durable and destination-scoped photo delivery state.

No network calls are made by this module. Ambiguous uploads are never retried
until another component has reconciled the remote album.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class DeliveryState(StrEnum):
    READY = "ready"
    UPLOADING = "uploading"
    FAILED = "failed"
    UNKNOWN = "unknown"
    VERIFIED = "verified"


@dataclass(frozen=True)
class Delivery:
    id: int
    destination_group: str
    album_id: str
    sha256: str
    path: Path
    quality: str
    state: DeliveryState
    attempts: int
    remote_reference: str | None


def _extension(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    raise ValueError("Unsupported or unrecognized image format")


class Archive:
    """Atomic SQLite state transitions and content-addressed local spool."""

    def __init__(self, database: Path, spool: Path) -> None:
        self.database = Path(database)
        self.spool = Path(spool)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.spool.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY,
                    destination_group TEXT NOT NULL,
                    album_id TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    path TEXT NOT NULL,
                    quality TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'ready',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    remote_reference TEXT,
                    UNIQUE(destination_group, album_id, sha256)
                );
                CREATE TABLE IF NOT EXISTS events (
                    source_group TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    destination_group TEXT NOT NULL,
                    album_id TEXT NOT NULL,
                    image_id INTEGER NOT NULL REFERENCES images(id),
                    PRIMARY KEY(source_group, message_id, destination_group, album_id)
                );
                """
            )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.database, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _delivery(row: sqlite3.Row) -> Delivery:
        return Delivery(
            id=int(row["id"]),
            destination_group=str(row["destination_group"]),
            album_id=str(row["album_id"]),
            sha256=str(row["sha256"]),
            path=Path(str(row["path"])),
            quality=str(row["quality"]),
            state=DeliveryState(str(row["state"])),
            attempts=int(row["attempts"]),
            remote_reference=row["remote_reference"],
        )

    def get(self, delivery_id: int) -> Delivery:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM images WHERE id = ?", (delivery_id,)).fetchone()
        if row is None:
            raise KeyError(delivery_id)
        return self._delivery(row)

    def ingest(
        self,
        *,
        source_group: str,
        message_id: str,
        destination_group: str,
        album_id: str,
        data: bytes,
        quality: str,
    ) -> Delivery:
        """Persist image bytes before registering its source event.

        Source-event identity prevents replay; destination plus hash prevents
        duplicate remote objects from repeated messages.
        """
        if not all((source_group, message_id, destination_group, album_id)):
            raise ValueError("Group, album and message identifiers must be nonempty")
        if quality not in {"original", "compressed", "thumbnail", "unknown"}:
            raise ValueError("Unknown media quality")
        extension = _extension(data)
        digest = hashlib.sha256(data).hexdigest()
        target = self.spool / f"{digest}{extension}"
        if not target.exists():
            with tempfile.NamedTemporaryFile(dir=self.spool, delete=False) as tmp:
                temp_name = Path(tmp.name)
                try:
                    tmp.write(data)
                    tmp.flush()
                    os.fsync(tmp.fileno())
                except BaseException:
                    temp_name.unlink(missing_ok=True)
                    raise
            os.replace(temp_name, target)

        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            event = conn.execute(
                """SELECT image_id FROM events WHERE source_group = ? AND message_id = ?
                   AND destination_group = ? AND album_id = ?""",
                (source_group, message_id, destination_group, album_id),
            ).fetchone()
            if event is not None:
                result_id = int(event["image_id"])
            else:
                conn.execute(
                    """INSERT OR IGNORE INTO images
                       (destination_group, album_id, sha256, path, quality)
                       VALUES (?, ?, ?, ?, ?)""",
                    (destination_group, album_id, digest, str(target), quality),
                )
                row = conn.execute(
                    """SELECT id FROM images WHERE destination_group = ?
                       AND album_id = ? AND sha256 = ?""",
                    (destination_group, album_id, digest),
                ).fetchone()
                assert row is not None
                result_id = int(row["id"])
                conn.execute(
                    """INSERT INTO events
                       (source_group, message_id, destination_group, album_id, image_id)
                       VALUES (?, ?, ?, ?, ?)""",
                    (source_group, message_id, destination_group, album_id, result_id),
                )
        return self.get(result_id)

    def pending(self, *, limit: int = 100) -> list[Delivery]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._connection() as conn:
            rows = conn.execute(
                """SELECT * FROM images WHERE state IN ('ready', 'failed')
                   ORDER BY id LIMIT ?""",
                (limit,),
            ).fetchall()
        return [self._delivery(row) for row in rows]

    def claim(self, delivery_id: int) -> Delivery:
        with self._connection() as conn:
            updated = conn.execute(
                """UPDATE images SET state = 'uploading', attempts = attempts + 1
                   WHERE id = ? AND state IN ('ready', 'failed')""",
                (delivery_id,),
            )
            if updated.rowcount != 1:
                raise ValueError("Delivery is not claimable; reconcile unknown uploads first")
        return self.get(delivery_id)

    def _transition(
        self,
        delivery_id: int,
        *,
        state: DeliveryState,
        allowed: tuple[DeliveryState, ...],
        remote_reference: str | None = None,
    ) -> Delivery:
        with self._connection() as conn:
            placeholders = ", ".join("?" for _ in allowed)
            updated = conn.execute(
                f"""UPDATE images SET state = ?, remote_reference = COALESCE(?, remote_reference)
                    WHERE id = ? AND state IN ({placeholders})""",
                (state.value, remote_reference, delivery_id, *(item.value for item in allowed)),
            )
            if updated.rowcount != 1:
                raise ValueError(f"Invalid delivery transition to {state}")
        return self.get(delivery_id)

    def mark_failed(self, delivery_id: int) -> Delivery:
        """Use only for definite failures known not to have committed remotely."""
        return self._transition(
            delivery_id, state=DeliveryState.FAILED, allowed=(DeliveryState.UPLOADING,)
        )

    def mark_unknown(self, delivery_id: int) -> Delivery:
        return self._transition(
            delivery_id, state=DeliveryState.UNKNOWN, allowed=(DeliveryState.UPLOADING,)
        )

    def mark_verified(self, delivery_id: int, remote_reference: str) -> Delivery:
        if not remote_reference:
            raise ValueError("Remote verification reference is required")
        return self._transition(
            delivery_id,
            state=DeliveryState.VERIFIED,
            allowed=(DeliveryState.UPLOADING, DeliveryState.UNKNOWN),
            remote_reference=remote_reference,
        )

    def quarantine_interrupted(self) -> int:
        """A restart cannot know if an in-flight upload committed remotely."""
        with self._connection() as conn:
            updated = conn.execute("UPDATE images SET state = 'unknown' WHERE state = 'uploading'")
            return updated.rowcount
