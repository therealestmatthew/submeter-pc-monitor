"""Probe: what long sampling intervals and a cold set do to the samples and to a bucket.

Reads and measures only. Nothing is written to disk.

    .venv/bin/python docs/review/probes/c-storage/long_intervals.py

Part 1: settings that docs/08-configuration.md allows give intervals over the sampler's fixed
30-second gap threshold. Part 2: a cold set read every 10 s beside a hot set read every 1 s,
fed to the baseline Sampler in the two ways its interface allows, then rolled up. Part 3: with
the gap threshold out of the way, what samples as long as or longer than a minute do to minute
buckets, and whether they arrive before a bucket is final, 30 s after it ends.
"""

from __future__ import annotations

from _synth import DAY0, pipeline, proc, snap

from submeter.collector.sampler import Sampler
from submeter.core.config import load_settings
from submeter.store.rollup import bucket_start, cores_percentile, roll_up, well_covered

COLD = 40  # quiet processes, each using 0.3% of a core
HOT_RATE, COLD_RATE = 0.5, 0.003


def part_one() -> None:
    cases = (
        ("idle_interval 45s", {"idle_interval": "45s"}, 45.0),
        (
            "idle_interval 20s, on_battery_multiplier 2",
            {"idle_interval": "20s", "on_battery_multiplier": 2},
            40.0,
        ),
        ("cold_interval 60s", {"cold_interval": "60s"}, 60.0),
        (
            "idle_interval 60s, on_battery_multiplier 10",
            {"idle_interval": "60s", "on_battery_multiplier": 10},
            600.0,
        ),
        ("defaults on battery: idle 5s x 2", {}, 10.0),
    )
    for label, sampling, step in cases:
        load_settings(overrides={"sampling": sampling})  # raises if the settings are refused
        shots = [snap(DAY0 + step * k, [proc(1, 0.5 * step * k)]) for k in range(21)]
        batches = [batch for batch, _, _ in pipeline(shots)]
        kept = sum(sample.cpu_s for batch in batches for sample in batch.processes)
        gaps = sum(batch.gap for batch in batches)
        print(
            f"  {label:<44} accepted; {step:5.0f} s between samples: {gaps} of {len(batches)} "
            f"batches are gaps, CPU kept {kept:.0f} of {0.5 * step * 20:.0f} s"
        )


def cold_set(partial: bool) -> None:
    """One hot process at 0.5 cores and 40 cold ones at 0.003 cores each, for ten minutes."""
    shots, seen = [], [0.0] * COLD
    for second in range(601):
        fresh = second % 10 == 0
        if fresh:
            seen = [COLD_RATE * second] * COLD
        processes = [proc(1, HOT_RATE * second)]
        if fresh or not partial:  # a hot-only snapshot, or the cold counters as last read
            processes += [proc(100 + index, cpu) for index, cpu in enumerate(seen)]
        shots.append(snap(DAY0 + second, processes))
    steps = list(pipeline(shots))
    samples = [workloads[0] for _, workloads, _ in steps]
    truth = (HOT_RATE + COLD * COLD_RATE) * 600
    hour = roll_up(samples, width_s=3600, logical_cores=4)[0]
    exits = sum(len(batch.exited) for batch, _, _ in steps)
    peak = max(sample.cpu_s / sample.interval_s for sample in samples)
    print(
        f"  cpu {hour.cpu_s:.1f} of {truth:.1f} s; p50 {cores_percentile(hour, 50):.2f}, "
        f"p95 {cores_percentile(hour, 95):.2f}, highest sample {peak:.2f} cores "
        f"(true: {truth / 600:.2f} throughout); processes counted as started {hour.started}, "
        f"reported exited {exits}"
    )


def minute_buckets(step: float, phase: float) -> tuple[list, float]:
    """An hour of one process at 0.5 cores, sampled every `step` s. Buckets and worst lateness."""
    count = int(3600 / step) + 1
    shots = [snap(DAY0 + phase + step * k, [proc(1, 0.5 * step * k)]) for k in range(count)]
    samples = [w for _, ws, _ in pipeline(shots, Sampler(gap_after_s=1e9)) for w in ws]
    ends = (bucket_start(s.taken_at - s.interval_s / 2, 60) + 60 for s in samples)
    late = max(s.taken_at - end for s, end in zip(samples, ends, strict=True))
    return roll_up(samples, width_s=60, logical_cores=4), late


def part_three() -> None:
    for step in (10.0, 60.0, 120.0, 600.0):
        minutes, _ = minute_buckets(step, 7.0)
        covered = sorted({bucket.covered_s for bucket in minutes})
        late = max(minute_buckets(step, float(phase))[1] for phase in range(60))
        print(
            f"  {step:4.0f} s samples: {len(minutes)} minute buckets exist in the hour, covered_s "
            f"{covered[0]:.0f} to {covered[-1]:.0f} of 60, well covered "
            f"{sum(map(well_covered, minutes))}; a sample is written up to {late:.0f} s after "
            f"its bucket ended (a bucket is final after 30 s)"
        )


def main() -> None:
    print("part 1: allowed settings against the 30 s gap threshold (Sampler default)")
    part_one()
    print("part 2a: hot-only snapshots, the cold set present every 10th second")
    cold_set(partial=True)
    print("part 2b: every snapshot complete, cold counters refreshed every 10th second")
    cold_set(partial=False)
    print("part 3: samples as long as a minute bucket or longer, gap threshold lifted")
    part_three()


if __name__ == "__main__":
    main()
