"""Tests for the settings surface: what a settings file may contain and how it is loaded."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from typer.testing import CliRunner

from submeter.cli import app
from submeter.collector import sampler
from submeter.core.config import ConfigError, Settings, load_settings


# ---- R149: no profiles -----------------------------------------------------------------------
def test_profiles_are_removed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    file = tmp_path / "submeter.toml"
    file.write_text('[profile.laptop]\nsampling.active_interval = "2s"\n')
    with pytest.raises(ConfigError) as caught:
        load_settings(file)
    assert any(problem.startswith("profile:") for problem in caught.value.problems)
    assert "profile" not in inspect.signature(load_settings).parameters
    monkeypatch.setenv("SUBMETER_HOME", str(tmp_path / "home"))
    shown = CliRunner().invoke(app, ["config", "show", "--profile", "x"])
    assert shown.exit_code == 2 and "No such option" in shown.output


# ---- R142: no hot and cold sets --------------------------------------------------------------
def test_hot_and_cold_sets_are_removed(tmp_path: Path) -> None:
    file = tmp_path / "submeter.toml"
    file.write_text('[sampling]\ncold_interval = "10s"\nhot_cpu_threshold = "0.5%"\n')
    with pytest.raises(ConfigError) as caught:
        load_settings(file)
    text = " | ".join(caught.value.problems)
    assert "sampling.cold_interval" in text and "sampling.hot_cpu_threshold" in text
    assert Settings().sampling.active_interval == 2.0
    assert not hasattr(sampler, "hot_keys")
