"""Probe: allowed sampling settings against the Sampler's fixed 30-second gap rule,
and what a recorded gap becomes once it is totalled and rolled up.

Parts 1 to 3 are logic only, on made-up counters and clocks. Part 4 runs the baseline's own
`submeter top` once for 31 seconds, which reads processes and changes nothing.

    uv run python docs/review/probes/b-measurement/gap_rule.py

1. Settings that core/config.py accepts, fed to Sampler() at the tick interval they produce
   (the last row assumes cold reads arrive as a batch of their own).
   One process uses half a core throughout, so every second dropped is half a CPU-second lost.
2. A one-hour suspend: the gap batch goes through aggregate() and roll_up() as written.
3. A stall: the collector is not scheduled for 35 seconds while the machine keeps working.
4. `submeter top --seconds 31`, which the baseline accepts (the limit is 60).
"""

from __future__ import annotations

import json
import tempfile

from typer.testing import CliRunner

from submeter.attribution.rules import Attributor, RuleSet, aggregate
from submeter.cli import app
from submeter.collector.sampler import Sampler
from submeter.core.config import load_settings
from submeter.core.models import ProcessCounters, ProcessKey, Snapshot, SystemCounters
from submeter.store.rollup import cores_percentile, roll_up, well_covered

RATE = 0.5


def snapshot(at: float, *, wall: float | None = None) -> Snapshot:
    process = ProcessCounters(
        key=ProcessKey(pid=1, started=100.0), exe="tool", cpu_s=RATE * at, memory_bytes=1 << 28
    )
    system = SystemCounters(
        logical_cores=8,
        cpu_busy_s=(RATE * at, *([0.0] * 7)),
        memory_total_bytes=1 << 34,
        memory_available_bytes=1 << 33,
    )
    taken_at = 1_795_132_800.0 + (at if wall is None else wall)
    return Snapshot(taken_at=taken_at, monotonic=at, processes=(process,), system=system)


def credited(interval: float, ticks: int = 20) -> tuple[float, int]:
    sampler, total, gaps = Sampler(), 0.0, 0
    sampler.ingest(snapshot(0.0))
    for tick in range(1, ticks + 1):
        batch = sampler.ingest(snapshot(tick * interval))
        assert batch is not None
        total += batch.processes[0].cpu_s
        gaps += batch.gap
    return total / (RATE * interval * ticks), gaps


def main() -> None:
    print("1. accepted settings, and what Sampler() with its default gap_after_s=30 makes of them")
    cases = [
        ("defaults on mains, idle", {}, "idle_interval", False),
        ("defaults on battery, idle", {}, "idle_interval", True),
        ("idle_interval = 31s", {"idle_interval": "31s"}, "idle_interval", False),
        ("idle_interval = 60s", {"idle_interval": "60s"}, "idle_interval", False),
        (
            "battery x2 (default), idle 16s",
            {"idle_interval": "16s"},
            "idle_interval",
            True,
        ),
        ("battery x7, idle 5s (default)", {"on_battery_multiplier": 7}, "idle_interval", True),
        ("battery x10, idle 5s (default)", {"on_battery_multiplier": 10}, "idle_interval", True),
        (
            "battery x4, active 8s",
            {"on_battery_multiplier": 4, "active_interval": "8s"},
            "active_interval",
            True,
        ),
        ("cold_interval = 60s, own batch", {"cold_interval": "60s"}, "cold_interval", False),
    ]
    for name, sampling, which, battery in cases:
        settings = load_settings(overrides={"sampling": sampling}).settings.sampling
        interval = getattr(settings, which) * (settings.on_battery_multiplier if battery else 1)
        share, gaps = credited(interval)
        print(
            f"   {name:<31} accepted; interval {interval:>5.1f} s -> "
            f"{gaps:>2} of 20 ticks called a gap, {100 * share:>3.0f}% of the CPU time credited"
        )

    print("\n2. a one-hour suspend between two samples, then four ordinary seconds")
    sampler, attributor, samples = Sampler(), Attributor(RuleSet()), []
    sampler.ingest(snapshot(0.0))
    clock = [(1.0, 1.0), (2.0, 3602.0), (3.0, 3603.0), (4.0, 3604.0), (5.0, 3605.0)]
    for mono, wall in clock:
        batch = sampler.ingest(snapshot(mono, wall=wall))
        assert batch is not None
        totals = aggregate(batch, attributor.assign(batch.processes))
        samples.extend(totals)
        print(
            f"   batch gap={batch.gap!s:<5} interval {batch.interval_s:>6.0f} s -> aggregate() "
            f"returns {len(totals)} workload row, cpu {totals[0].cpu_s:.2f} s over "
            f"{totals[0].interval_s:.0f} s"
        )
    for bucket in roll_up(samples, width_s=60, logical_cores=8):
        print(
            f"   minute bucket +{bucket.start - 1_795_132_800.0:>5.0f} s: covered "
            f"{bucket.covered_s:>6.0f} s of {bucket.width_s:.0f}, cpu {bucket.cpu_s:.2f} s, "
            f"well covered {well_covered(bucket)}, cores p50 {cores_percentile(bucket, 50):.3f}"
        )
    hour = roll_up(samples, width_s=3600, logical_cores=8)
    for bucket in hour:
        print(
            f"   hour bucket   +{bucket.start - 1_795_132_800.0:>5.0f} s: covered "
            f"{bucket.covered_s:>6.0f} s of {bucket.width_s:.0f}, cpu {bucket.cpu_s:.2f} s, "
            f"mean cores {bucket.cpu_s / bucket.covered_s:.4f} (the process used 0.5 while awake)"
        )

    print(
        "   a wall clock stepped forward by an hour gives the sampler the same two clock readings"
    )

    print("\n3. a 35-second stall with both clocks running, then one ordinary second")
    sampler = Sampler()
    sampler.ingest(snapshot(0.0))
    for at in (1.0, 36.0, 37.0):
        batch = sampler.ingest(snapshot(at))
        assert batch is not None
        used = RATE * batch.interval_s
        print(
            f"   batch gap={batch.gap!s:<5} interval {batch.interval_s:>4.0f} s: the process used "
            f"{used:5.2f} CPU-s, credited {batch.processes[0].cpu_s:5.2f}, machine busy recorded "
            f"{batch.cpu_busy_s:5.2f}"
        )

    print("\n4. submeter top --seconds 31 --json, on this machine as it is")
    with tempfile.TemporaryDirectory() as home:
        result = CliRunner().invoke(
            app, ["top", "--seconds", "31", "--json"], env={"SUBMETER_HOME": home}
        )
    rows = json.loads(result.stdout)
    print(
        f"   exit code {result.exit_code}; {len(rows)} workload rows covering "
        f"{sum(row['processes'] for row in rows)} processes over {rows[0]['interval_s']:.1f} s; "
        f"CPU time reported in total: {sum(row['cpu_s'] for row in rows):.2f} s"
    )


if __name__ == "__main__":
    main()
