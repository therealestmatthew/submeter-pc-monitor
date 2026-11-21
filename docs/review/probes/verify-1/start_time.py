"""Verify G5: ProcessKey.started is psutil's wall-clock start time; what a wall-clock step does.

Reads and measures only. The wall clock is never touched: the step is simulated by replacing
psutil's Linux boot_time() inside this process. The probe starts one child, `sleep 3`, of its
own and waits for it to end.

    uv run python docs/review/probes/verify-1/start_time.py

1. Is /proc/stat btime re-read on every create_time() of a new psutil.Process?
2. Through the real PsutilProvider, Sampler and Attributor: this process is cached before a
   simulated one-hour step back; a child born after it gets a start time an hour earlier than
   its parent. Does a rule with include_children still reach the child?
3. A provider whose objects are not cached (a /proc reader recomputing the start time each
   tick, or psutil after its cache is cleared) when btime moves by one second: how many keys
   change, and what does the Sampler make of it?
"""

from __future__ import annotations

import os
import subprocess

import psutil
import psutil._pslinux as pslinux
from _helpers import DAY0  # noqa: F401  (puts src on the path)

from submeter.attribution.rules import Attributor, Rule, RuleSet
from submeter.collector.sampler import Sampler
from submeter.providers.psutil_provider import PsutilProvider

real_boot_time = pslinux.boot_time


def part1() -> None:
    print("1. psutil create_time() for a fresh Process, before and after btime moves by 1 s")
    before = psutil.Process(os.getpid()).create_time()
    pslinux.boot_time = lambda: real_boot_time() - 1.0
    try:
        after = psutil.Process(os.getpid()).create_time()
    finally:
        pslinux.boot_time = real_boot_time
    print(f"   same process, two fresh objects: start times differ by {before - after:.3f} s")


def part2() -> None:
    print("2. one-hour step back between two snapshots, child born after it")
    provider, sampler = PsutilProvider(), Sampler()
    sampler.ingest(provider.snapshot())  # this process is now cached with the real btime
    pslinux.boot_time = lambda: real_boot_time() - 3600.0
    child = subprocess.Popen(["sleep", "3"])
    try:
        batch = sampler.ingest(provider.snapshot())
    finally:
        pslinux.boot_time = real_boot_time
        child.wait()
    assert batch is not None
    by_pid = {p.key.pid: p for p in batch.processes}
    me, kid = by_pid[os.getpid()], by_pid[child.pid]
    rules = RuleSet(rule=(Rule(workload="probe", exe=(me.exe,), include_children=True),))
    assignment = Attributor(rules).assign(batch.processes)
    print(
        f"   child start minus parent start {kid.key.started - me.key.started:.0f} s; "
        f"parent -> {assignment[me.key].workload!r}, child -> {assignment[kid.key].workload!r} "
        f"({assignment[kid.key].reason})"
    )


def part3() -> None:
    print("3. no cache: every process re-read with btime one second lower than the tick before")
    provider, sampler = PsutilProvider(), Sampler()
    psutil._pmap.clear()  # type: ignore[attr-defined]
    sampler.ingest(provider.snapshot())
    psutil._pmap.clear()  # type: ignore[attr-defined]
    pslinux.boot_time = lambda: real_boot_time() - 1.0
    try:
        batch = sampler.ingest(provider.snapshot())
    finally:
        pslinux.boot_time = real_boot_time
        psutil._pmap.clear()  # type: ignore[attr-defined]
    assert batch is not None
    seen = sum(p.first_seen for p in batch.processes)
    print(
        f"   {len(batch.processes)} processes; first_seen {seen}; reported exited "
        f"{len(batch.exited)}; CPU credited {sum(p.cpu_s for p in batch.processes):.3f} s, "
        f"machine busy {batch.cpu_busy_s:.3f} s"
    )


if __name__ == "__main__":
    part1()
    part2()
    part3()
