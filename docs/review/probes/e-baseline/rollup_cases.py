"""Probe: gap batches, values off the scale and the top percentile, through the real rollup code.

Writes only to a temporary folder, which it removes. Run from the repository root:

    uv run python docs/review/probes/e-baseline/rollup_cases.py

Case 1 sends a one-hour sleep through Sampler, aggregate, RawFile and roll_up, the way the
collector and server would. Cases 2 and 3 call core.histogram directly.
"""

from __future__ import annotations

import random
import tempfile
from pathlib import Path

from submeter.attribution.rules import Attributor, RuleSet, aggregate
from submeter.collector.sampler import Sampler
from submeter.core import histogram
from submeter.core.models import ProcessCounters, ProcessKey, Snapshot, SystemCounters
from submeter.store.raw import RawFile
from submeter.store.rollup import cores_percentile, merge, roll_up, well_covered

MB = 1024**2
DAY0 = 1_795_132_800.0  # 2026-11-20 00:00:00 UTC


def snap(at: float, mono: float, cpu: float) -> Snapshot:
    process = ProcessCounters(
        key=ProcessKey(pid=1, started=100.0), exe="tool", cpu_s=cpu, memory_bytes=400 * MB
    )
    system = SystemCounters(
        logical_cores=8,
        cpu_busy_s=(cpu,) + (0.0,) * 7,
        memory_total_bytes=16 * 1024**3,
        memory_available_bytes=8 * 1024**3,
    )
    return Snapshot(taken_at=at, monotonic=mono, processes=(process,), system=system)


def sleep_through_the_pipeline(folder: Path) -> None:
    print("1. Two busy hours with a one-hour sleep between them, 2 cores in use while awake")
    sampler, attributor, raw = Sampler(), Attributor(RuleSet()), RawFile(folder / "day.db")
    at, mono, cpu = DAY0, 0.0, 0.0
    sampler.ingest(snap(at, mono, cpu))
    for second in range(1, 7201):
        asleep = second == 3601  # the lid closes for an hour before this tick
        at, mono, cpu = at + (3601 if asleep else 1), mono + 1, cpu + 2.0
        batch = sampler.ingest(snap(at, mono, cpu))
        assert batch is not None and batch.gap == asleep
        assignment = attributor.assign(batch.processes)
        names = {key: value.workload for key, value in assignment.items()}
        raw.write(batch, aggregate(batch, assignment), names)
    samples = raw.workload_samples(DAY0, DAY0 + 4 * 3600)
    raw.close(at=at)
    minutes = roll_up(samples, width_s=60, logical_cores=8)
    odd = [b for b in minutes if b.covered_s > b.width_s]
    for bucket in odd:
        print(
            f"   minute bucket at +{(bucket.start - DAY0) / 60:.0f} min: covered_s="
            f"{bucket.covered_s:g} of width {bucket.width_s:g}, cpu_s={bucket.cpu_s:g}, "
            f"p50 cores={cores_percentile(bucket, 50):.3f}, well_covered={well_covered(bucket)}"
        )
    whole = merge(minutes, start=DAY0, width_s=3 * 3600)
    print(
        f"   three hours merged: covered_s={whole.covered_s:g} (awake for 7200), "
        f"cpu_s={whole.cpu_s:g}, mean cores over covered time={whole.cpu_s / whole.covered_s:.2f}, "
        f"p25={cores_percentile(whole, 25):.3f}, p50={cores_percentile(whole, 50):.3f} "
        "(the workload used 2.00 cores whenever it was observed)"
    )
    print(f"   minute buckets: {len(minutes)}, with covered_s over their width: {len(odd)}")


def off_the_scale() -> None:
    print("2. Values below and above the histogram scales")
    for label, scale, value, show in (
        ("memory 1 MiB", histogram.MEMORY, 1.0 * MB, lambda v: f"{v / MB:.1f} MiB"),
        ("memory 15 MiB", histogram.MEMORY, 15.0 * MB, lambda v: f"{v / MB:.1f} MiB"),
        ("memory 300 GiB", histogram.MEMORY, 300.0 * 1024**3, lambda v: f"{v / 1024**3:.0f} GiB"),
        ("cores 0.002", histogram.CORES, 0.002, lambda v: f"{v:.4f}"),
        ("cores 300", histogram.CORES, 300.0, lambda v: f"{v:.0f}"),
    ):
        counts = histogram.empty(scale)
        histogram.add(counts, scale, value, 60.0)
        answers = [histogram.percentile(counts, scale, q) for q in (50, 95)]
        print(f"   steady {label}: p50={show(answers[0])}, p95={show(answers[1])}")


def top_percentile() -> None:
    print("3. percentile(q=100) with float weights (sum() is compensated, the loop is not)")
    rng, wrong, differ, trials = random.Random(11), 0, 0, 2000
    for _ in range(trials):
        counts = histogram.empty(histogram.CORES)
        for _ in range(60):
            histogram.add(counts, histogram.CORES, rng.uniform(0.5, 4.0), rng.uniform(0.9, 5.1))
        top = histogram.percentile(counts, histogram.CORES, 100)
        assert top is not None
        wrong += top > 5.0
        running = 0.0
        for count in counts:
            running += count
        differ += running < sum(counts)
    print(
        f"   {trials} minute buckets of values between 0.5 and 4 cores: "
        f"{wrong} report a maximum of {histogram.CORES.high:g} cores; "
        f"in {differ} the running total is below sum(counts)"
    )
    for q in (99.0, 99.9, 99.999):
        counts = histogram.empty(histogram.CORES)
        for _ in range(60):
            histogram.add(counts, histogram.CORES, rng.uniform(0.5, 4.0), rng.uniform(0.9, 5.1))
        print(f"   control, q={q}: {histogram.percentile(counts, histogram.CORES, q):.2f} cores")


def main() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as name:
        sleep_through_the_pipeline(Path(name))
    off_the_scale()
    top_percentile()


if __name__ == "__main__":
    main()
