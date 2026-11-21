"""Probe: what a suspend (a GAP batch) becomes in the raw file and then in a bucket.

Reads and measures only. Writes one raw file in a temporary folder.

    .venv/bin/python docs/review/probes/c-storage/gap_in_rollup.py

One process uses 2 cores for 10 minutes, the machine sleeps for an hour, and the process uses
2 cores for 10 more minutes. The probe follows that through Sampler, aggregate, RawFile.write,
RawFile.workload_samples and roll_up, and prints what the minute and hour buckets say.
The design promises that a gap is never read as zero use (docs/06-storage.md).
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from _synth import DAY0, clock, pipeline, proc, snap

from submeter.store.raw import RawFile
from submeter.store.rollup import cores_percentile, roll_up, well_covered

START = DAY0 + 9 * 3600  # 09:00:00
SLEEP_S = 3600.0


def snapshots() -> list:
    """Wall clock and monotonic clock. The monotonic clock does not count the hour asleep."""
    out, cpu = [snap(START, [proc(1, 0.0)], mono=0.0)], 0.0
    for second in range(1, 601):
        cpu += 2.0
        out.append(snap(START + second, [proc(1, cpu)], mono=second, busy=cpu))
    for second in range(601, 1202):
        cpu += 2.0 if second > 601 else 0.0  # nothing ran while asleep
        out.append(snap(START + SLEEP_S + second, [proc(1, cpu)], mono=second, busy=cpu))
    return out


def main() -> None:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "2026-11-20.db"
        raw, gaps, true_cpu, observed_s = RawFile(path), [], 0.0, 0.0
        for batch, workloads, names in pipeline(snapshots()):
            raw.write(batch, workloads, names)
            if batch.gap:
                gaps.append(batch)
            else:
                true_cpu += sum(sample.cpu_s for sample in batch.processes)
                observed_s += batch.interval_s
        samples = raw.workload_samples(START, START + 3 * 3600)
        raw.close(at=samples[-1].taken_at)
        db = sqlite3.connect(path)
        gap_rows = db.execute("SELECT start, end, reason FROM gap").fetchall()
        odd = db.execute(
            "SELECT ts, interval_s, cpu_s, memory_bytes FROM workload_raw WHERE interval_s > 30"
        ).fetchall()
        system = db.execute(
            "SELECT SUM(interval_s), SUM(interval_s * logical_cores), SUM(cpu_busy_s)"
            " FROM system_raw"
        ).fetchone()
        columns = [row[1] for row in db.execute("PRAGMA table_info(workload_raw)")]
        db.close()

    print(f"truth: observed {observed_s:.0f} s, CPU {true_cpu:.0f} s, 2.00 cores whenever observed")
    print(f"gap batches from the sampler: {len(gaps)}, interval_s {gaps[0].interval_s:.0f}")
    for start, end, reason in gap_rows:
        print(f"gap table: {clock(start)} to {clock(end)}, {reason!r}")
    print(f"workload_raw columns: {columns} (no gap flag)")
    for ts, interval, cpu, memory in odd:
        print(
            f"workload_raw row at {clock(ts)}: interval_s {interval:.0f}, cpu_s {cpu:.1f}, "
            f"memory {memory / 2**20:.0f} MiB  <- the gap, stored as an ordinary sample"
        )
    print(
        f"system_raw: SUM(interval_s) {system[0]:.0f} s, capacity {system[1]:.0f} core-s, "
        f"busy {system[2]:.0f} s -> busy share {system[2] / system[1]:.1%} "
        f"(true while observed: {true_cpu / (observed_s * 4):.1%})"
    )

    minutes = roll_up(samples, width_s=60, logical_cores=4)
    over = [bucket for bucket in minutes if bucket.covered_s > 60.5]
    for bucket in over:
        print(
            f"minute bucket {clock(bucket.start)}: covered_s {bucket.covered_s:.0f} of 60, "
            f"samples {bucket.samples}, cpu_s {bucket.cpu_s:.0f}, seconds in the lowest cores "
            f"bin (under 0.01 cores) {bucket.cores_hist[0]:.0f}"
        )
    print("hour buckets built by roll_up(width_s=3600):")
    for bucket in roll_up(samples, width_s=3600, logical_cores=4):
        print(
            f"  {clock(bucket.start)}: covered_s {bucket.covered_s:.0f}, cpu_s {bucket.cpu_s:.0f}, "
            f"cpu_s/covered_s {bucket.cpu_s / bucket.covered_s:.2f} cores, "
            f"p50 {cores_percentile(bucket, 50):.3f}, p95 {cores_percentile(bucket, 95):.2f}, "
            f"well_covered {well_covered(bucket)}"
        )
    print("the 09:00 hour was observed for 600 s. Without the gap row it is not well covered.")


if __name__ == "__main__":
    main()
