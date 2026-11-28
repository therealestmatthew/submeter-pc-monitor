"""submeter doctor: what this machine can measure and where the files live."""

from __future__ import annotations

import json

import typer

from submeter import __version__
from submeter.cli._common import JsonFlag
from submeter.providers.base import capability_report
from submeter.providers.psutil_provider import PsutilProvider
from submeter.store.files import FileMap


def doctor(as_json: JsonFlag = False) -> None:
    """Say what this machine can measure and where the files live."""
    provider = PsutilProvider()
    provider.snapshot()
    files = FileMap.discover()
    report = capability_report([provider])
    exposed = files.readable_by_others()
    places = {
        "settings": str(files.settings_dir),
        "data": str(files.data_dir),
        "state": str(files.state_dir),
    }
    if as_json:
        providers = [capability.model_dump(mode="json") for capability in report]
        found = {"providers": providers, "files": places, "readable_by_others": exposed}
        typer.echo(json.dumps({"version": __version__, **found}))
        return
    typer.echo(f"submeter {__version__}")
    for capability in report:
        typer.echo(f"{capability.name:<20}{capability.status.value:<14}{capability.note}")
    for kind, place in places.items():
        typer.echo(f"{kind:<20}{place}")
    shown = "unavailable on Windows" if exposed is None else ", ".join(exposed) or "none"
    typer.echo(f"{'readable by others':<20}{shown}")


def register(app: typer.Typer) -> None:
    """Add `doctor` to the command line."""
    app.command()(doctor)
