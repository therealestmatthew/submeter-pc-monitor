"""Verify G1, G2 and the G9 check: the fixed 30 s gap rule, and what a gap does to buckets.

Reads and measures only. Raw files go to a temporary folder. Clocks are synthetic, except in
part 3, which runs the real `top` command through typer's test runner with its sleep replaced
by a clock offset, so it takes about a second instead of the requested time.

    uv run python docs/review/probes/verify-1/gap_rule.py

1. Settings that load_settings accepts, and the interval they imply.
2. The real Sampler at intervals of 29, 31, 45 and 60 s with both clocks running.
3. `submeter top --seconds N --json` for N = 2, 31 and 60, and N = 60 where the monotonic clock
   also counts a 40 s sleep (as it may on Windows): what the docs/reference/windows-priorities.md
   section 5 check would see.
4. A one-hour suspend (monotonic stops) between two 10-minute stretches at 2 cores, taken
   through Sampler, Attributor, aggregate, RawFile, roll_up and well_covered.
"""

from __future__ import annotations

import json
import tempfile
import time
import types
from pathlib import Path

from _helpers import DAY0, proc, snap
from typer.testing import CliRunner

import submeter.cli as cli
import submeter.providers.psutil_provider as provider_module
from submeter.attribution.rules import Attributor, RuleSet, aggregate
from submeter.collector.sampler import Sampler
from submeter.core.config import load_settings
from submeter.store.raw import RawFile
from submeter.store.rollup import roll_up, well_covered


def part1() -> None:
    print("1. settings load_settings accepts, and the interval between samples they imply")
    cases = {
        "idle_interval 45s": ({"sampling": {"idle_interval": "45s"}}, ("idle_interval", 1)),
        "cold_interval 60s": ({"sampling": {"cold_interval": "60s"}}, ("cold_interval", 1)),
        "idle 5s (default) x on_battery_multiplier 7": (
            {"sampling": {"on_battery_multiplier": 7}},
            ("idle_interval", 7),
        ),
        "idle 60s x on_battery_multiplier 10": (
            {"sampling": {"idle_interval": "60s", "on_battery_multiplier": 10}},
            ("idle_interval", 10),
        ),
    }
    for label, (overrides, (field, factor)) in cases.items():
        sampling = load_settings(overrides=overrides).settings.sampling
        interval = getattr(sampling, field) * factor
        print(f"   {label:<46} accepted; {interval:6.1f} s between samples")


def part2() -> None:
    print("2. Sampler() with both clocks advancing by the interval; one process at 0.5 cores")
    for interval in (29.0, 31.0, 45.0, 60.0):
        sampler = Sampler()
        sampler.ingest(snap(DAY0, [proc(1, 0.0)], mono=0.0, busy=0.0))
        used = 0.5 * interval
        batch = sampler.ingest(snap(DAY0 + interval, [proc(1, used)], mono=interval, busy=used))
        assert batch is not None
        print(
            f"   {interval:4.0f} s: gap={batch.gap}, process used {used:5.1f} CPU-s, credited "
            f"{batch.processes[0].cpu_s:5.1f}; machine busy recorded {batch.cpu_busy_s:5.1f}"
        )


def part3() -> None:
    print("3. submeter top --seconds N --json, sleep replaced by a clock offset (real counters)")
    offset = {"wall": 0.0, "mono": 0.0}
    fake_time = types.SimpleNamespace(
        time=lambda: time.time() + offset["wall"],
        monotonic=lambda: time.monotonic() + offset["mono"],
    )
    real_provider_time, real_cli_time = provider_module.time, cli.time
    provider_module.time = fake_time  # type: ignore[assignment]
    runner = CliRunner()
    try:
        for seconds, mono_counts_sleep, label in (
            (2.0, True, "--seconds 2"),
            (31.0, True, "--seconds 31"),
            (60.0, True, "--seconds 60, no sleep"),
            (60.0, True, "--seconds 60, 40 s asleep, monotonic counts sleep"),
            (60.0, False, "--seconds 60, 40 s asleep, monotonic stops in sleep"),
        ):
            asleep = 40.0 if "asleep" in label else 0.0

            def fake_sleep(
                s: float, asleep: float = asleep, counts: bool = mono_counts_sleep
            ) -> None:
                time.sleep(0.5)  # half a real second so the counters move
                offset["wall"] += s - 0.5
                offset["mono"] += s - 0.5 - (0.0 if counts else asleep)

            cli.time = types.SimpleNamespace(sleep=fake_sleep)  # type: ignore[assignment]
            result = runner.invoke(cli.app, ["top", "--seconds", str(seconds), "--json"])
            rows = json.loads(result.output)
            cpu = sum(row["cpu_s"] for row in rows)
            procs = sum(row["processes"] for row in rows)
            interval = rows[0]["interval_s"] if rows else 0.0
            print(
                f"   {label:<52} exit {result.exit_code}; {procs} processes, interval_s "
                f"{interval:5.1f}, CPU-s summed {cpu:.3f}"
            )
    finally:
        provider_module.time, cli.time = real_provider_time, real_cli_time  # type: ignore[assignment]


def part4() -> None:
    print("4. one-hour suspend between two 10-minute stretches at 2.00 cores (monotonic stops)")
    sampler, attributor = Sampler(), Attributor(RuleSet())
    shots = []
    cpu = 0.0
    for k in range(601):
        shots.append(snap(DAY0 + 9 * 3600 + k, [proc(1, cpu)], mono=float(k)))
        cpu += 2.0
    cpu -= 2.0
    for k in range(1, 601):
        cpu += 2.0
        shots.append(snap(DAY0 + 9 * 3600 + 600 + 3600 + k, [proc(1, cpu)], mono=600.0 + k))
    with tempfile.TemporaryDirectory() as folder:
        raw = RawFile(Path(folder) / "day.db")
        gap_rows = []
        for shot in shots:
            batch = sampler.ingest(shot)
            if batch is None:
                continue
            workloads = aggregate(batch, attributor.assign(batch.processes))
            if batch.gap:
                gap_rows.append((batch.interval_s, [w.interval_s for w in workloads]))
            raw.write(batch, workloads, {})
        samples = raw.workload_samples(0.0, 1e12)
        gaps = raw.count("gap")
        raw.close()
    print(f"   gap batches {len(gap_rows)}, gap table rows {gaps}; workload rows written for it:")
    for interval, rows in gap_rows:
        print(f"     batch interval_s {interval:.0f}, workload row interval_s {rows}")
    minutes = roll_up(samples, width_s=60, logical_cores=4)
    over = [b for b in minutes if b.covered_s > b.width_s]
    for b in over:
        print(
            f"   minute bucket at +{b.start - DAY0 - 9 * 3600:.0f} s: covered_s "
            f"{b.covered_s:.0f} of {b.width_s:.0f}, cpu_s {b.cpu_s:.0f}, "
            f"well_covered {well_covered(b)}"
        )
    for b in roll_up(samples, width_s=3600, logical_cores=4):
        print(
            f"   hour bucket at +{b.start - DAY0 - 9 * 3600:.0f} s: covered_s {b.covered_s:.0f}, "
            f"cpu_s {b.cpu_s:.0f}, mean cores {b.cpu_s / b.covered_s:.2f}, "
            f"well_covered {well_covered(b)}"
        )
    print("   truth: observed 1200 s at 2.00 cores; the 09:00 hour was observed for 600 s")


if __name__ == "__main__":
    part1()
    part2()
    part3()
    part4()
