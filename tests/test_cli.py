"""Offline smoke tests for the scaffold."""

from __future__ import annotations

import pytest

from lumenbay import __version__
from lumenbay.cli import main


def test_package_version() -> None:
    assert __version__ == "0.1.0"


def test_cli_help_without_args(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "usage: lumenbay" in capsys.readouterr().out


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert f"lumenbay {__version__}" in capsys.readouterr().out
