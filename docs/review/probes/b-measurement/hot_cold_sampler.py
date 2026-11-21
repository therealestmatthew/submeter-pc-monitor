"""Probe: what hot and cold sets do to the baseline Sampler, aggregate and roll_up as written.

Logic only, on made-up counters and clocks. Nothing is timed and no process is read.

    uv run python docs/review/probes/b-measurement/hot_cold_sampler.py

The machine in the model: 1 hot process using half a core, and 270 cold processes each using
0.4% of a core (under the 0.5% hot threshold), 100 MiB each, on 8 logical cores. The active
interval is 1 s and the cold interval 10 s, the defaults. The truth is 1.58 cores in use.

A. The collector passes only the hot set in the nine ticks between two full snapshots.
B. The collector passes every process each tick but refreshes cold counters every 10th tick.
"""

from __future__ import annotations

from submeter.attribution.rules import Attributor, RuleSet, aggregate
from submeter.collector.sampler import Sampler, hot_keys
from submeter.core.models import ProcessCounters, ProcessKey, Snapshot, SystemCounters
from submeter.store.rollup import cores_percentile, roll_up

MIB = 1024**2
COLD, CORES, TICKS = 270, 8, 60
HOT_RATE, COLD_RATE = 0.5, 0.004
TRUE_CORES = HOT_RATE + COLD * COLD_RATE


def counters(pid: int, cpu_s: float) -> ProcessCounters:
    key = ProcessKey(pid=pid, started=100.0)
    return ProcessCounters(key=key, exe="tool", cpu_s=cpu_s, memory_bytes=100 * MIB)


def snapshot(at: float, processes: list[ProcessCounters]) -> Snapshot:
    busy = TRUE_CORES * at
    system = SystemCounters(
        logical_cores=CORES,
        cpu_busy_s=(busy, *([0.0] * (CORES - 1))),
        memory_total_bytes=32 * 1024**3,
        memory_available_bytes=16 * 1024**3,
    )
    return Snapshot(taken_at=1000.0 + at, monotonic=at, processes=tuple(processes), system=system)


def run(name: str, *, hot_only: bool) -> None:
    sampler, attributor = Sampler(), Attributor(RuleSet())
    cold_read_at = 0
    rows, promoted, samples = [], [], []
    credited = started = exited = 0.0
    for tick in range(TICKS + 1):
        full = tick % 10 == 0
        if full:
            cold_read_at = tick
        processes = [counters(1, HOT_RATE * tick)]
        if full or not hot_only:
            processes += [counters(10 + i, COLD_RATE * cold_read_at) for i in range(COLD)]
        batch = sampler.ingest(snapshot(float(tick), processes))
        if batch is None:
            continue
        totals = aggregate(batch, attributor.assign(batch.processes))
        samples.extend(totals)
        total = totals[0]
        credited += total.cpu_s
        started += total.started
        exited += len(batch.exited)
        promoted.append(len(hot_keys(batch, cpu_threshold=0.005)))
        if tick in (9, 10, 11):
            rows.append(
                f"   tick {tick:>2}: {total.processes:>3} processes, "
                f"{total.cpu_s / total.interval_s:6.2f} cores, "
                f"{total.memory_bytes / 1024**3:5.2f} GiB, started {total.started:>3}, "
                f"exited {len(batch.exited):>3}, hot set next {promoted[-1]:>3}, "
                f"missing from busy {batch.cpu_busy_s - total.cpu_s:+6.2f} CPU-s"
            )
    bucket = roll_up(samples, width_s=60, logical_cores=CORES)[0]
    print(f"{name}")
    print("\n".join(rows))
    print(
        f"   over {TICKS} s: credited {credited:.1f} CPU-s of {TRUE_CORES * TICKS:.1f} "
        f"({100 * credited / (TRUE_CORES * TICKS):.0f}%), processes 'started' {started:.0f}, "
        f"'exited' {exited:.0f} (truth: 0 and 0)"
    )
    print(
        f"   minute bucket: memory min {bucket.memory_min / 1024**3:.2f} GiB, "
        f"max {bucket.memory_max / 1024**3:.2f} GiB (truth {271 * 100 / 1024:.2f} both), "
        f"cores p50 {cores_percentile(bucket, 50):.2f}, p95 {cores_percentile(bucket, 95):.2f} "
        f"(truth {TRUE_CORES:.2f} both), capacity {CORES}"
    )


def main() -> None:
    print(f"truth: {TRUE_CORES:.2f} cores in use, 271 processes, {271 * 100 / 1024:.2f} GiB")
    run("A. hot-only snapshots between full ones, baseline Sampler as written", hot_only=True)
    run("B. cold counters carried forward and refreshed every 10th tick", hot_only=False)


if __name__ == "__main__":
    main()
