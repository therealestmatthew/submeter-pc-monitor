"""submeter top: watch the machine for a moment and total it by workload."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Annotated

import typer

from submeter.attribution.rules import Attributor, RuleSet, aggregate
from submeter.cli._common import JsonFlag
from submeter.collector.sampler import Sampler
from submeter.core.units import format_size
from submeter.providers.psutil_provider import PsutilProvider
from submeter.store.files import FileMap


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
    assignment = Attributor(rule_set, self_pids={os.getpid()}).assign(batch.processes)
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


def register(app: typer.Typer) -> None:
    """Add `top` to the command line."""
    app.command()(top)
