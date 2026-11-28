"""submeter store: inspect the files Submeter keeps."""

from __future__ import annotations

import json

import typer

from submeter.cli._common import JsonFlag
from submeter.core.units import format_size
from submeter.store.files import FileMap

store_app = typer.Typer(no_args_is_help=True, help="Inspect the files Submeter keeps.")


@store_app.command("status")
def store_status(as_json: JsonFlag = False) -> None:
    """Show how much disk each kind of file is using."""
    use = FileMap.discover().disk_use()
    if as_json:
        typer.echo(json.dumps({"bytes": use, "total": sum(use.values())}))
        return
    for kind, size in use.items():
        typer.echo(f"{kind:<10}{format_size(size):>12}")
    typer.echo(f"{'total':<10}{format_size(sum(use.values())):>12}")


def register(app: typer.Typer) -> None:
    """Add the `store` group to the command line."""
    app.add_typer(store_app, name="store")
