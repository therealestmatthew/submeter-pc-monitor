"""Tests of the project settings in pyproject.toml. Run with: uv run pytest"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def project_settings() -> dict[str, Any]:
    with PYPROJECT.open("rb") as file:
        return tomllib.load(file)


def test_python_floor_is_3_13() -> None:
    """Python 3.13 is the first whose time.monotonic() on Windows resolves 1 microsecond (R124)."""
    assert project_settings()["project"]["requires-python"] == ">=3.13"
