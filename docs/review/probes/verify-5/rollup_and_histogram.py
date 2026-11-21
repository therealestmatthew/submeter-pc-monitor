"""Probe: re-check the hourly-tier convention and the top percentile (clusters M7, M11).

Logic only, on synthetic samples and histograms through the baseline's own functions.
Nothing is timed, no process is read, nothing is written.

    uv run python docs/review/probes/verify-5/rollup_and_histogram.py

M7: the raw reader selects samples by end time, ts > start AND ts <= end
(store/raw.py workload_samples), while roll_up() gives a whole sample to the bucket that
holds the middle of its interval (store/rollup.py:110). A server that reads one hour with
the reader and rolls it up is simulated for a steady 1-core workload, at several cadences
and tick phases, and compared with a roll_up() over the whole day and with the raw sum.
M11: histogram.percentile(q=100) on time-weighted bins whose weights are float intervals.
"""

from __future__ import annotations

import math
import random

from submeter.core import histogram
from submeter.core.models import AccountingSource, WorkloadSample
from submeter.store.rollup import roll_up

DAY0 = 1_795_132_800.0  # 2026-11-20 00:00:00 UTC
HOUR = 3600.0


def day_of_samples(interval: float, phase: float) -> list[WorkloadSample]:
    """A workload using exactly 1 core, sampled every `interval`, first tick at DAY0 + phase."""
    out, at = [], DAY0 + phase
    while at <= DAY0 + 6 * HOUR:
        out.append(
            WorkloadSample(
                taken_at=at,
                interval_s=interval,
                workload="steady",
                source=AccountingSource.POLLED,
                cpu_s=interval,
                memory_bytes=1,
                io_read_bytes=0,
                io_write_bytes=0,
                processes=1,
                started=0,
            )
        )
        at += interval
    return out


def m7() -> None:
    print("M7. one bucket read with the raw reader's rule, then rolled up (steady 1 core)")
    print("   width  cadence  phase  buckets back  bucket cpu_s  whole-day roll_up  raw read  gap")
    for width in (HOUR, 60.0):
        for interval in (1.0, 5.0, 10.0, 60.0):
            if interval >= width:
                continue
            for share in (0.3, 0.7):
                samples = day_of_samples(interval, share * interval)
                start = DAY0 + 2 * HOUR
                read = [s for s in samples if start < s.taken_at <= start + width]  # raw.py:199
                buckets = roll_up(read, width_s=width, logical_cores=8)
                mine = next(b.cpu_s for b in buckets if b.start == start)
                whole = next(
                    b.cpu_s
                    for b in roll_up(samples, width_s=width, logical_cores=8)
                    if b.start == start
                )
                raw = sum(s.cpu_s for s in read)
                gap = 100 * (mine - raw) / raw
                print(
                    f"   {width:>5.0f}  {interval:>5.0f} s  {share:.1f}x  {len(buckets):>12}"
                    f"  {mine:>12.0f}  {whole:>17.0f}  {raw:>8.0f}  {gap:+.3f}%"
                )


def naive_top(counts: list[float]) -> tuple[float, float]:
    running = 0.0
    for count in counts:
        if count > 0:
            running += count
    return running, sum(counts)


def m11() -> None:
    print("\nM11. histogram.percentile(q=100) on minute buckets with float interval weights")
    rng = random.Random(7)
    top_of_scale = below = 0
    trials = 1000
    for _ in range(trials):
        counts = histogram.empty(histogram.CORES)
        observed = 0.0
        for _ in range(60):
            value = rng.uniform(0.5, 4.0)
            observed = max(observed, value)
            histogram.add(counts, histogram.CORES, value, rng.uniform(0.995, 1.005))
        p100 = histogram.percentile(counts, histogram.CORES, 100)
        running, total = naive_top(counts)
        top_of_scale += p100 == histogram.CORES.high
        below += running < total
    print(f"   {trials} buckets of 60 samples between 0.5 and 4 cores, weights 0.995 to 1.005 s")
    print(f"   q=100 returned {histogram.CORES.high:g} cores (top of scale) in {top_of_scale}")
    print(f"   naive running total below sum(counts) in {below}")
    counts = histogram.empty(histogram.CORES)
    for _ in range(60):
        histogram.add(counts, histogram.CORES, rng.uniform(0.5, 4.0), 1.0)
    whole = histogram.percentile(counts, histogram.CORES, 100)
    print(f"   control, integer weights of exactly 1.0 s: q=100 gives {whole:.2f} cores")
    print(f"   fsum vs plain loop on 0.1 x 10: {math.fsum([0.1] * 10)!r}, {naive_top([0.1] * 10)}")


if __name__ == "__main__":
    m7()
    m11()
