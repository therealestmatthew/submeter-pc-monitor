"""submeter config: show and check settings."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from submeter.cli._common import FileOption, _load
from submeter.core.config import ConfigError, load_settings

config_app = typer.Typer(no_args_is_help=True, help="Show and check settings.")


@config_app.command("show")
def config_show(
    file: FileOption = None,
    effective: Annotated[
        bool, typer.Option("--effective", help="Every value with its source. This is the default.")
    ] = False,
) -> None:
    """Print every setting with the layer it came from."""
    for key, value, source in _load(file).effective():
        typer.echo(f"{key:<44}{value:<26}{source}")


@config_app.command("check")
def config_check(file: Path) -> None:
    """Validate a settings file without applying it."""
    try:
        loaded = load_settings(file)
    except ConfigError as error:
        for problem in error.problems:
            typer.echo(f"error: {problem}", err=True)
        raise typer.Exit(2) from error
    typer.echo(f"ok: {len(loaded.effective())} settings, {len(loaded.sources)} set in the file")


def register(app: typer.Typer) -> None:
    """Add the `config` group to the command line."""
    app.add_typer(config_app, name="config")
