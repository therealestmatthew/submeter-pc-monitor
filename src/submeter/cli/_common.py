"""What more than one command module uses: the shared options and the settings loader."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer

from submeter.core.config import ConfigError, LoadedSettings, load_settings
from submeter.store.files import FileMap

JsonFlag = Annotated[bool, typer.Option("--json", help="Print JSON instead of a table.")]
FileOption = Annotated[
    Path | None, typer.Option(help="Settings file. Defaults to the standard one.")
]


def _load(file: Path | None) -> LoadedSettings:
    files = FileMap.discover()
    path = file if file is not None else files.settings_file
    try:
        return load_settings(path if path.exists() else None, env=os.environ)
    except ConfigError as error:
        for problem in error.problems:
            typer.echo(f"error: {problem}", err=True)
        raise typer.Exit(2) from error
