"""Probe: what PsutilProvider returns when single calls fail, and what it returns on this machine.

Reads live processes, starts two short-lived children of its own, and writes nothing. It prints
counts only: no names, paths or command lines. Run from the repository root:

    uv run python docs/review/probes/e-baseline/provider_cases.py

Part 1 hands the provider a stand-in process whose calls fail one at a time. Parts 2 to 5 use
the real machine. Part 4 simulates a wall-clock step by patching the one function psutil reads
the boot time from; it does not touch the system clock.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import time
from collections import namedtuple
from typing import Any

import psutil

from submeter.attribution.rules import Attributor, Rule, RuleSet
from submeter.collector.sampler import Sampler
from submeter.providers.psutil_provider import PsutilProvider

CALLS = (
    "create_time",
    "cpu_times",
    "memory_info",
    "num_threads",
    "cmdline",
    "io_counters",
    "ppid",
    "name",
)
Times = namedtuple("Times", "user system")
Memory = namedtuple("Memory", "rss")
Io = namedtuple("Io", "read_bytes write_bytes")
ANSWERS: dict[str, Any] = {
    "create_time": 1000.0,
    "cpu_times": Times(30.0, 12.0),
    "memory_info": Memory(64 * 1024**2),
    "num_threads": 7,
    "cmdline": ["tool", "arg"],
    "io_counters": Io(4096, 8192),
    "ppid": 1,
    "name": "tool",
}


class StandIn:
    """Answers like a psutil.Process, except that one named call raises."""

    pid = 4242

    def __init__(self, failing: str | None, error: Exception | None = None) -> None:
        self._failing, self._error = failing, error or psutil.AccessDenied(self.pid)

    def oneshot(self) -> contextlib.AbstractContextManager[None]:
        return contextlib.nullcontext()

    def __getattr__(self, name: str) -> Any:
        def call() -> Any:
            if name == self._failing:
                raise self._error
            return ANSWERS[name]

        return call


def single_failures() -> None:
    print("1. One call fails with AccessDenied; the rest answer (42 CPU-s, 64 MiB, 7 threads)")
    provider = PsutilProvider()
    for failing in (None, *CALLS):
        found = provider._read(StandIn(failing))  # type: ignore[arg-type]
        assert found is not None
        print(
            f"   {failing or 'nothing fails':<14} started={found.key.started:g} "
            f"cpu_s={found.cpu_s:g} memory_MiB={found.memory_bytes // 1024**2} "
            f"threads={found.threads} exe={found.exe!r} io={found.io_read_bytes} "
            f"cmdline={'yes' if found.cmdline else 'no'} restricted={found.restricted}"
        )
    for error in (RuntimeError("/proc/4242/io file was empty"), OSError(31, "device failure")):
        try:
            provider._read(StandIn("io_counters", error))  # type: ignore[arg-type]
        except Exception as raised:
            print(f"   io_counters raises {type(error).__name__}: _read lets it out ({raised})")


def this_machine() -> None:
    print("2. This machine, as the signed-in user")
    processes = PsutilProvider().snapshot().processes
    restricted = [p for p in processes if p.restricted]
    print(
        f"   {len(processes)} processes, {len(restricted)} restricted; of the restricted: "
        f"{sum(p.io_read_bytes is None for p in restricted)} lack I/O counters, "
        f"{sum(p.cmdline is None for p in restricted)} lack a command line, "
        f"{sum(p.key.started == 0.0 for p in restricted)} lack a start time, "
        f"{sum(p.cpu_s == 0.0 and p.memory_bytes == 0 for p in restricted)} have zero CPU and "
        f"zero memory, {sum(p.cpu_s > 0 for p in restricted)} have CPU time above zero"
    )
    print(f"   CPU-seconds held by restricted processes: {sum(p.cpu_s for p in restricted):.0f}")


def zombie() -> None:
    print("3. A child that has exited and not yet been collected by its parent")
    child = subprocess.Popen([sys.executable, "-S", "-c", "sum(i * i for i in range(3_000_000))"])
    watched = psutil.Process(child.pid)
    while watched.status() != psutil.STATUS_ZOMBIE:
        time.sleep(0.05)
    times = watched.cpu_times()
    seen = any(p.key.pid == child.pid for p in PsutilProvider().snapshot().processes)
    child.wait()
    print(
        f"   psutil still reads its CPU time ({times.user + times.system:.2f} s); "
        f"present in the provider's snapshot: {seen}"
    )


def clock_step() -> None:
    print("4. Start times after the wall clock is set back one hour (simulated, see docstring)")
    import psutil._pslinux as linux

    me, real_boot_time = os.getpid(), linux.boot_time
    provider, sampler = PsutilProvider(), Sampler()
    first = provider.snapshot()
    sampler.ingest(first)
    mine = next(p for p in first.processes if p.key.pid == me)
    linux.boot_time = lambda: real_boot_time() - 3600.0
    child = subprocess.Popen(["sleep", "20"])  # a different program, so only inheritance applies
    try:
        time.sleep(0.3)
        batch = sampler.ingest(provider.snapshot())
        assert batch is not None
        again = next(s for s in batch.processes if s.key.pid == me)
        born = next(s for s in batch.processes if s.key.pid == child.pid)
        fresh = psutil.Process(me).create_time()
        rules = RuleSet(rule=(Rule(workload="probe", exe=(mine.exe,), include_children=True),))
        assigned = Attributor(rules).assign(batch.processes)
        print(
            f"   this process, same provider: key unchanged={again.key == mine.key}; "
            f"a new psutil.Process for it differs by {fresh - mine.key.started:+.0f} s"
        )
        print(
            f"   its child, born after the step, has a start time "
            f"{born.key.started - mine.key.started:+.0f} s from its parent's, and is "
            f"attributed to {assigned[born.key].workload!r} ({assigned[born.key].reason}); "
            f"the parent is {assigned[again.key].workload!r}"
        )
    finally:
        linux.boot_time = real_boot_time
        child.kill()
        child.wait()


def busy_sum() -> None:
    print("5. The system busy sum on Linux, per core, over two seconds")
    before, started = psutil.cpu_times(percpu=True), time.monotonic()
    low = PsutilProvider._system()
    time.sleep(2.0)
    after, elapsed = psutil.cpu_times(percpu=True), time.monotonic() - started
    high = PsutilProvider._system()
    worst = 0.0
    for old, new in zip(before, after, strict=True):
        total = sum(new) - sum(old) - (new.guest - old.guest) - (new.guest_nice - old.guest_nice)
        worst = max(worst, abs(total - elapsed))
    busy = sum(high.cpu_busy_s) - sum(low.cpu_busy_s)
    print(
        f"   fields: {', '.join(before[0]._fields)}; every core's fields (guest taken out) add "
        f"up to the {elapsed:.2f} s elapsed within {worst:.2f} s; provider busy sum {busy:.2f} s"
    )


def main() -> None:
    single_failures()
    this_machine()
    zombie()
    clock_step()
    busy_sum()


if __name__ == "__main__":
    main()
