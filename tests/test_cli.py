"""Tests for the command line, run end to end. Run with: uv run pytest"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from submeter.cli import app


def test_cli_runs_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUBMETER_HOME", str(tmp_path))
    runner = CliRunner()
    doctor = runner.invoke(app, ["doctor", "--json"])
    assert (
        doctor.exit_code == 0
        and json.loads(doctor.stdout)["providers"][0]["name"] == "process.psutil"
    )
    watched = runner.invoke(app, ["top", "--seconds", "0.3", "--json"])
    assert watched.exit_code == 0 and {"workload", "cpu_s", "source"} <= set(
        json.loads(watched.stdout)[0]
    )
    bad = tmp_path / "bad.toml"
    bad.write_text("[api]\nport = 80\n")
    assert runner.invoke(app, ["config", "check", str(bad)]).exit_code == 2
    assert "api.port" in runner.invoke(app, ["config", "show"]).stdout
    shown = runner.invoke(app, ["config", "show", "--effective"])
    assert shown.exit_code == 0 and "api.port" in shown.stdout
    assert json.loads(runner.invoke(app, ["store", "status", "--json"]).stdout)["total"] == 0
