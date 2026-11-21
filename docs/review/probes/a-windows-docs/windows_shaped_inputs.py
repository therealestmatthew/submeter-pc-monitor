"""Feeds the baseline psutil provider and sampler the shapes psutil returns on Windows.

Nothing here runs on Windows. psutil is replaced by stand-ins that return what its Windows code
returns, according to these sources (see the review report for the quotes):
- per-core times are (user, system, idle, interrupt, dpc), where psutil computes
  system = KernelTime - IdleTime and reports interrupt and dpc separately (psutil cpu.c);
- Microsoft: "% DPC Time is a component of % Privileged Time because DPCs are executed in
  privileged mode", so KernelTime - IdleTime already holds DPC (and interrupt) time;
- psutil lists pid 0, names it "System Idle Process" without opening it, and on AccessDenied
  for pid 0 its cpu_times falls back to the whole-system query, whose pid 0 entry carries the
  Idle process's time; Microsoft: Task Manager shows the Idle process's processor time as the
  System Idle Process.
It then checks two things: what the provider's per-core busy sum becomes, and whether the
per-process CPU sum can exceed the machine's busy time once pid 0 is in the snapshot.

Run from the repository root:
    uv run python docs/review/probes/a-windows-docs/windows_shaped_inputs.py
"""

from __future__ import annotations

import contextlib
from collections import namedtuple
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import psutil

from submeter.collector.sampler import Sampler
from submeter.providers import psutil_provider
from submeter.providers.psutil_provider import PsutilProvider

CORES = 8
WinCpu = namedtuple("WinCpu", "user system idle interrupt dpc")
# One second per core: user 0.10 s; privileged time 0.05 s, of which interrupt 0.01 s and
# DPC 0.02 s; idle 0.85 s. True busy per core is 0.15 s.
USER, PRIVILEGED, INTERRUPT, DPC, IDLE = 0.10, 0.05, 0.01, 0.02, 0.85
BOOT = 1_000.0


class FakeProcess:
    """Answers the provider's calls the way psutil's Windows code does for this pid."""

    def __init__(self, pid: int, name: str, cpu: float) -> None:
        self.pid, self._name, self._cpu = pid, name, cpu

    @contextlib.contextmanager
    def oneshot(self) -> Iterator[None]:
        yield

    def create_time(self) -> float:
        return BOOT  # psutil turns pid 0's zero CreateTime into the boot time

    def cpu_times(self) -> Any:
        return SimpleNamespace(user=0.0, system=self._cpu)

    def memory_info(self) -> Any:
        return SimpleNamespace(rss=0, private=0)

    def num_threads(self) -> int:
        return CORES if self.pid == 0 else 4

    def cmdline(self) -> list[str]:
        if self.pid == 0:
            raise psutil.AccessDenied(pid=0)
        return [self._name]

    def io_counters(self) -> Any:
        return SimpleNamespace(read_bytes=0, write_bytes=0)

    def ppid(self) -> int:
        return 0

    def name(self) -> str:
        return self._name


def install(tick: int) -> None:
    """Replace the three psutil functions the provider uses with Windows-shaped answers."""
    seconds = float(tick)
    per_core = [
        WinCpu(
            USER * seconds, PRIVILEGED * seconds, IDLE * seconds, INTERRUPT * seconds, DPC * seconds
        )
        for _ in range(CORES)
    ]
    processes = [
        FakeProcess(0, "System Idle Process", IDLE * CORES * seconds),
        FakeProcess(4, "System", 0.02 * CORES * seconds),
        FakeProcess(4242, "worker.exe", (USER + 0.01) * CORES * seconds),
    ]
    fake = SimpleNamespace(
        cpu_times=lambda percpu=False: per_core,
        virtual_memory=lambda: SimpleNamespace(total=16 << 30, available=8 << 30),
        process_iter=lambda: iter(processes),
        AccessDenied=psutil.AccessDenied,
        NoSuchProcess=psutil.NoSuchProcess,
        ZombieProcess=psutil.ZombieProcess,
    )
    psutil_provider.psutil = fake  # type: ignore[assignment]


def main() -> None:
    provider, sampler = PsutilProvider(), Sampler()
    batch = None
    for tick in (10, 11):
        install(tick)
        snapshot = provider.snapshot()
        snapshot = snapshot.model_copy(update={"monotonic": float(tick), "taken_at": BOOT + tick})
        batch = sampler.ingest(snapshot)
    assert batch is not None
    true_busy = (USER + PRIVILEGED) * CORES
    print(f"interval {batch.interval_s:.1f} s, {CORES} cores, gap {batch.gap}")
    print(f"true busy core-seconds          {true_busy:.2f}")
    print(
        f"provider cpu_busy_s             {batch.cpu_busy_s:.2f}"
        f"  (over by {batch.cpu_busy_s - true_busy:.2f} = interrupt + DPC counted twice)"
    )
    by_name = {s.exe: s for s in batch.processes}
    for name, sample in by_name.items():
        print(f"process {name:20} cpu_s {sample.cpu_s:.2f} restricted {sample.restricted}")
    total = sum(s.cpu_s for s in batch.processes)
    print(f"sum of per-process CPU          {total:.2f}  vs busy {batch.cpu_busy_s:.2f}")
    print(f"per-process sum exceeds busy:   {total > batch.cpu_busy_s}")
    print(
        f"idle core-seconds in the interval {IDLE * CORES:.2f}, "
        f"charged to pid 0: {by_name['System Idle Process'].cpu_s:.2f}"
    )


if __name__ == "__main__":
    main()
