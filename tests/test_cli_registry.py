"""The command line is a package of command modules, each found by discovery (plan choice C8).

`submeter.cli` builds `app` and calls `register(app)` on every module of the package whose
name does not start with an underscore, so a new command is a new module and edits no shared
file. Every import of `submeter.cli` happens inside a test, so that the two tests guarding the
move still run where `submeter.cli` is a single module.
"""

from __future__ import annotations

import importlib
import pkgutil
import re
import tomllib
from pathlib import Path

import typer
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]


def _command_modules() -> list[str]:
    package = importlib.import_module("submeter.cli")
    path = getattr(package, "__path__", None)
    assert path is not None, "submeter.cli is a module, not a package"
    return sorted(found.name for found in pkgutil.iter_modules(path) if found.name[0] != "_")


def _listed(output: str, *names: str) -> set[str]:
    return {name for name in names if re.search(rf"(?m)^\W*{name}\s", output)}


def test_every_command_module_registers_a_command() -> None:
    modules = _command_modules()
    assert {"config", "doctor", "store", "top"} <= set(modules)
    for name in modules:
        module = importlib.import_module(f"submeter.cli.{name}")
        register = getattr(module, "register", None)
        assert callable(register), f"submeter.cli.{name} has no register(app)"
        fresh = typer.Typer()
        register(fresh)
        added = len(fresh.registered_commands) + len(fresh.registered_groups)
        assert added >= 1, f"submeter.cli.{name}.register(app) added no command or group"


def test_cli_is_a_package() -> None:
    package = importlib.import_module("submeter.cli")
    assert getattr(package, "__path__", None) is not None
    assert not (ROOT / "src" / "submeter" / "cli.py").exists()


def test_help_lists_the_four_command_groups() -> None:
    app = importlib.import_module("submeter.cli").app
    runner = CliRunner()
    shown = runner.invoke(app, ["--help"])
    assert shown.exit_code == 0
    groups = ("doctor", "top", "config", "store")
    assert _listed(shown.stdout, *groups) == set(groups)
    config = runner.invoke(app, ["config", "--help"])
    assert config.exit_code == 0 and _listed(config.stdout, "show", "check") == {"show", "check"}
    store = runner.invoke(app, ["store", "--help"])
    assert store.exit_code == 0 and _listed(store.stdout, "status") == {"status"}


def test_the_console_script_still_resolves() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    target = project["project"]["scripts"]["submeter"]
    assert target == "submeter.cli:app"
    module_name, attribute = target.split(":")
    assert isinstance(getattr(importlib.import_module(module_name), attribute), typer.Typer)
