"""The command line: a thin layer that wires the other modules together.

No logic lives here. Each command builds what it needs from the modules below
it, calls them, and prints the result as a table or, with --json, as JSON with
a stable shape. This baseline has five commands. The rest of the list in the
brief (why, cost, diff, session, report, export, run, daemon) is added as the
components behind them are built.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Annotated

import typer

from submeter import __version__
from submeter.attribution.rules import Attributor, RuleSet, aggregate
from submeter.collector.sampler import Sampler
from submeter.core.config import ConfigError, LoadedSettings, load_settings
from submeter.core.units import format_size
from submeter.providers.base import capability_report
from submeter.providers.psutil_provider import PsutilProvider
from submeter.store.files import FileMap

app = typer.Typer(
    no_args_is_help=True, add_completion=False, help="Submeter: what each workload costs."
)
config_app = typer.Typer(no_args_is_help=True, help="Show and check settings.")
store_app = typer.Typer(no_args_is_help=True, help="Inspect the files Submeter keeps.")
app.add_typer(config_app, name="config")
app.add_typer(store_app, name="store")

JsonFlag = Annotated[bool, typer.Option("--json", help="Print JSON instead of a table.")]
FileOption = Annotated[
    Path | None, typer.Option(help="Settings file. Defaults to the standard one.")
]


def _load(file: Path | None, profile: str | None) -> LoadedSettings:
    files = FileMap.discover()
    path = file if file is not None else files.settings_file
    try:
        return load_settings(path if path.exists() else None, profile=profile, env=os.environ)
    except ConfigError as error:
        for problem in error.problems:
            typer.echo(f"error: {problem}", err=True)
        raise typer.Exit(2) from error


@app.command()
def doctor(as_json: JsonFlag = False) -> None:
    """Say what this machine can measure and where the files live."""
    provider = PsutilProvider()
    provider.snapshot()
    files = FileMap.discover()
    report = capability_report([provider])
    places = {
        "settings": str(files.settings_dir),
        "data": str(files.data_dir),
        "state": str(files.state_dir),
    }
    if as_json:
        providers = [capability.model_dump(mode="json") for capability in report]
        typer.echo(json.dumps({"version": __version__, "providers": providers, "files": places}))
        return
    typer.echo(f"submeter {__version__}")
    for capability in report:
        typer.echo(f"{capability.name:<20}{capability.status.value:<14}{capability.note}")
    for kind, place in places.items():
        typer.echo(f"{kind:<20}{place}")


@app.command()
def top(
    seconds: Annotated[float, typer.Option(min=0.2, max=60.0, help="How long to watch.")] = 2.0,
    rules: Annotated[Path | None, typer.Option(help="A rules.toml to use.")] = None,
    as_json: JsonFlag = False,
) -> None:
    """Watch the machine for a moment and total it by workload."""
    files = FileMap.discover()
    rules_path = rules if rules is not None else files.rules_file
    rule_set = RuleSet.load(rules_path) if rules_path.exists() else RuleSet()
    provider, sampler = PsutilProvider(read_cwd=rule_set.needs_cwd), Sampler()
    sampler.ingest(provider.snapshot())
    time.sleep(seconds)
    batch = sampler.ingest(provider.snapshot())
    if batch is None:
        raise typer.Exit(1)
    assignment = Attributor(rule_set, self_pid=os.getpid()).assign(batch.processes)
    workloads = aggregate(batch, assignment)
    if as_json:
        typer.echo(json.dumps([workload.model_dump(mode="json") for workload in workloads]))
        return
    typer.echo(f"{'workload':<22}{'source':<10}{'cores':>8}{'memory':>12}{'procs':>7}")
    for workload in workloads:
        cores = workload.cpu_s / batch.interval_s
        memory = format_size(workload.memory_bytes)
        typer.echo(
            f"{workload.workload:<22}{workload.source.value:<10}{cores:>8.2f}{memory:>12}"
            f"{workload.processes:>7}"
        )


@config_app.command("show")
def config_show(
    file: FileOption = None,
    profile: str | None = None,
    effective: Annotated[
        bool, typer.Option("--effective", help="Every value with its source. This is the default.")
    ] = False,
) -> None:
    """Print every setting with the layer it came from."""
    for key, value, source in _load(file, profile).effective():
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
