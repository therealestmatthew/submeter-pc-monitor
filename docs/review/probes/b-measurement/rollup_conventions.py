"""Probe: can "CPU-hours from the hourly tier match the raw sum within 0.1%" be met, and
against which raw sum?

Logic only, on synthetic workload samples. It writes one raw file to a temporary folder,
which is removed. Nothing is timed and no process is read.

    uv run python docs/review/probes/b-measurement/rollup_conventions.py

The baseline holds two rules for "which samples belong to this hour":
- roll_up() gives a whole sample to the bucket that holds the middle of its interval;
- RawFile.workload_samples(start, end) returns samples whose end time is in (start, end].
For each sampling interval the brief allows, a day of a bursty workload is stored, and
each full hour is totalled both ways. An hour merged from minute buckets is compared as well.
"""

from __future__ import annotations

import random
import tempfile
from pathlib import Path

from submeter.core.models import AccountingSource, SampleBatch, WorkloadSample
from submeter.store.raw import RawFile
from submeter.store.rollup import merge, roll_up

DAY0 = 1_795_132_800.0  # 2026-11-20 00:00:00 UTC
HOURS = 24


def samples(interval: float, phase: float, seed: int) -> list[WorkloadSample]:
    """A workload idling at 0.05 cores that bursts to several cores for a tenth of the time."""
    rng, out, at = random.Random(seed), [], DAY0 + phase
    while at <= DAY0 + HOURS * 3600 + interval:
        cores = rng.lognormvariate(1.0, 0.6) if rng.random() < 0.1 else 0.05
        out.append(
            WorkloadSample(
                taken_at=at,
                interval_s=interval,
                workload="agents",
                source=AccountingSource.POLLED,
                cpu_s=cores * interval,
                memory_bytes=1 << 30,
                io_read_bytes=0,
                io_write_bytes=0,
                processes=1,
                started=0,
            )
        )
        at += interval
    return out


def compare(interval: float, folder: Path) -> str:
    data = samples(interval, phase=interval * 0.4, seed=11)
    raw = RawFile(folder / f"raw-{interval}.db")
    for sample in data:
        batch = SampleBatch(
            taken_at=sample.taken_at,
            interval_s=interval,
            gap=False,
            processes=(),
            exited=(),
            logical_cores=8,
            cpu_busy_s=0.0,
            memory_available_bytes=0,
        )
        raw.write(batch, [sample], {})
    hourly = {bucket.start: bucket for bucket in roll_up(data, width_s=3600, logical_cores=8)}
    minutes = roll_up(data, width_s=60, logical_cores=8)
    worst_window = worst_merge = 0.0
    over = 0
    for hour in range(1, HOURS - 1):
        start = DAY0 + hour * 3600
        window = sum(s.cpu_s for s in raw.workload_samples(start, start + 3600))
        merged = merge(
            [b for b in minutes if start <= b.start < start + 3600], start=start, width_s=3600
        )
        tier = hourly[start].cpu_s
        worst_window = max(worst_window, abs(tier - window) / window)
        over += abs(tier - window) / window > 0.001
        worst_merge = max(worst_merge, abs(tier - merged.cpu_s) / tier)
    raw.close()
    odd = sum(1 for b in minutes if b.covered_s > b.width_s * 1.5)
    present = {b.start for b in minutes}
    missing = sum(1 for minute in range(60, (HOURS - 1) * 60) if DAY0 + minute * 60 not in present)
    return (
        f"hour tier against end-time window: {over:>2} of {HOURS - 2} hours differ by more than "
        f"0.1%, worst {100 * worst_window:6.3f}%; against merged minutes: worst "
        f"{100 * worst_merge:.0e}%; minute buckets empty {missing}, over 1.5 widths {odd}"
    )


def main() -> None:
    print("gate: CPU-hours from the hourly tier match the raw sum within 0.1%")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as name:
        for label, interval in (
            ("active 1 s (default)", 1.0),
            ("idle 5 s (default)", 5.0),
            ("idle 5 s on battery x2", 10.0),
            ("idle or cold 30 s", 30.5),
            ("idle or cold 60 s", 60.5),
        ):
            print(f"   {label:<24} {compare(interval, Path(name))}")
    soak = 30 * 60
    print(
        f"a {soak // 60}-minute soak covers at most {100 * soak / 3600:.0f}% of one hour bucket, "
        "or parts of two; a bucket is final 30 s after its hour ends, and one under half covered "
        "is left out of trends"
    )


if __name__ == "__main__":
    main()
