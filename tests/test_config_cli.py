"""Configuration and CLI safety checks (no client login or API requests)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lumenbay.cli import main
from lumenbay.config import Settings


def test_config_relative_storage_paths(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "wechat_group": "Authorized group", "qq_group_id": "qq1",
        "qq_album_name": "Photos", "napcat_base_url": "http://localhost:3000",
        "database": "state/store.sqlite3", "spool": "state/images",
    }), encoding="utf-8")
    result = Settings.load(config)
    assert result.database == tmp_path / "state" / "store.sqlite3"
    assert result.spool == tmp_path / "state" / "images"


def test_missing_configuration_is_rejected(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="wechat_group"):
        Settings.load(config)


def test_live_run_requires_explicit_execute(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as error:
        main(["run", "--config", str(tmp_path / "missing.json")])
    assert error.value.code == 2


def test_status_is_offline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "wechat_group": "Authorized group", "qq_group_id": "qq1",
        "qq_album_name": "Photos", "napcat_base_url": "http://localhost:3000",
        "database": "state/archive.sqlite3", "spool": "state/spool",
    }), encoding="utf-8")
    assert main(["status", "--config", str(config)]) == 0
    assert capsys.readouterr().out.strip() == "{}"
