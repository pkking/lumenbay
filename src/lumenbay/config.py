"""Validated, secret-free local runtime configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    wechat_group: str
    qq_group_id: str
    qq_album_name: str
    napcat_base_url: str
    database: Path
    spool: Path
    interval_seconds: float = 10.0

    @classmethod
    def load(cls, path: Path) -> Settings:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Config must contain a JSON object")

        def required(key: str) -> str:
            value = raw.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Missing or invalid configuration field: {key}")
            return value

        interval = raw.get("interval_seconds", 10)
        if not isinstance(interval, (float, int)) or isinstance(interval, bool):
            raise ValueError("interval_seconds must be a positive number")
        if interval < 1:
            raise ValueError("interval_seconds must be >= 1")
        return cls(
            wechat_group=required("wechat_group"),
            qq_group_id=required("qq_group_id"),
            qq_album_name=required("qq_album_name"),
            napcat_base_url=required("napcat_base_url"),
            database=path.parent / required("database"),
            spool=path.parent / required("spool"),
            interval_seconds=float(interval),
        )
