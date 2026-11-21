"""Verify G7: a stand-in zero CPU counter used as the baseline for the next delta.

Reads and measures only.

    uv run python docs/review/probes/verify-1/zero_baseline.py

1. Real Sampler: a process the provider could not read (cpu_s 0.0, restricted), readable a
   second later with 5000 s of lifetime CPU. Then the same with the start time unreadable
   (the provider's started=0.0 stand-in), readable a second later.
2. How often each psutil read that feeds the stand-in raises AccessDenied on this machine, run
   as an ordinary user: create_time, cpu_times, memory_info, num_threads (the stand-in path),
   and io_counters and cmdline (which only set restricted).
"""

from __future__ import annotations

from collections import Counter

import psutil
from _helpers import DAY0, proc, snap

from submeter.collector.sampler import Sampler


def part1() -> None:
    print("1. Sampler across a restricted-then-readable flip, 1 s apart")
    sampler = Sampler()
    sampler.ingest(snap(DAY0, [proc(7, 0.0, started=50.0, restricted=True)], mono=0.0))
    batch = sampler.ingest(snap(DAY0 + 1, [proc(7, 5000.0, started=50.0)], mono=1.0))
    assert batch is not None
    p = batch.processes[0]
    print(
        f"   cpu stand-in: interval {batch.interval_s:.0f} s, first_seen {p.first_seen}, "
        f"credited {p.cpu_s:.0f} CPU-s on a {batch.logical_cores}-core machine"
    )
    sampler = Sampler()
    sampler.ingest(snap(DAY0, [proc(8, 0.0, started=0.0, restricted=True)], mono=0.0))
    batch = sampler.ingest(snap(DAY0 + 1, [proc(8, 5000.0, started=50.0)], mono=1.0))
    assert batch is not None
    p = batch.processes[0]
    print(
        f"   start-time stand-in: exited {len(batch.exited)}, first_seen {p.first_seen}, "
        f"credited {p.cpu_s:.0f} CPU-s"
    )


def part2() -> None:
    print("2. AccessDenied per psutil call, every process on this machine, as this user")
    denied: Counter[str] = Counter()
    total = 0
    calls = ("create_time", "cpu_times", "memory_info", "num_threads", "io_counters", "cmdline")
    for process in psutil.process_iter():
        try:
            with process.oneshot():
                total += 1
                for call in calls:
                    try:
                        getattr(process, call)()
                    except psutil.AccessDenied:
                        denied[call] += 1
        except psutil.NoSuchProcess:
            continue
    print(f"   {total} processes: " + ", ".join(f"{c} {denied[c]}" for c in calls))


if __name__ == "__main__":
    part1()
    part2()
