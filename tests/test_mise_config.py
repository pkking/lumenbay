"""Keep the committed mise runtime contract compatible with Python 3.11+."""

from __future__ import annotations

import tomllib
from pathlib import Path


def test_mise_uses_python_311_and_auto_venv() -> None:
    config = tomllib.loads((Path(__file__).resolve().parents[1] / "mise.toml").read_text())
    assert config["tools"]["python"] == "3.11"
    venv = config["env"]["_"]["python"]["venv"]
    assert venv == {"path": ".venv", "create": True}
