"""Probe: what one full process snapshot costs on this machine, three ways.

Reads and measures only. Run from the repository root:

    uv run python docs/review/probes/measure/snapshot_cost.py

1. The baseline psutil provider, 20 runs (the measurement the execution prompt asks for).
2. A direct /proc reader, written here only to price the design's Linux hot path:
   stat only, then stat + statm + io, 20 runs each.
3. The whole baseline pipeline per tick (snapshot, deltas, attribution, totals), as CPU time
   of this process, which is what the 1% and 3% overhead limits are about.
"""

from __future__ import annotations

import os
import statistics
import sys
import time

from submeter.attribution.rules import Attributor, RuleSet, aggregate
from submeter.collector.sampler import Sampler
from submeter.providers.psutil_provider import PsutilProvider

RUNS = 20
TARGET_PROCESSES = 300
RULE_MS = 10.0


def timed(action: object) -> tuple[float, float, float, float]:
    """Median and worst wall time, then median and worst CPU time of this process, in ms."""
    wall, cpu = [], []
    for _ in range(RUNS):
        wall_0, cpu_0 = time.perf_counter(), time.process_time()
        action()  # type: ignore[operator]
        wall.append((time.perf_counter() - wall_0) * 1000)
        cpu.append((time.process_time() - cpu_0) * 1000)
    return statistics.median(wall), max(wall), statistics.median(cpu), max(cpu)


def pids() -> list[int]:
    return [int(name) for name in os.listdir("/proc") if name.isdigit()]


def read(path: str) -> bytes | None:
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError:
        return None


def proc_stat_only() -> int:
    seen = 0
    for pid in pids():
        data = read(f"/proc/{pid}/stat")
        if data is None:
            continue
        fields = data[data.rfind(b")") + 2 :].split()
        _ = int(fields[11]) + int(fields[12]), int(fields[19]), int(fields[21]), int(fields[17])
        seen += 1
    return seen


def proc_stat_statm_io() -> int:
    seen = 0
    for pid in pids():
        data = read(f"/proc/{pid}/stat")
        if data is None:
            continue
        fields = data[data.rfind(b")") + 2 :].split()
        _ = int(fields[11]) + int(fields[12]), int(fields[19])
        statm = read(f"/proc/{pid}/statm")
        if statm is not None:
            _ = [int(part) for part in statm.split()[:3]]
        io = read(f"/proc/{pid}/io")
        if io is not None:
            _ = {line.split(b":")[0]: int(line.split(b":")[1]) for line in io.splitlines() if line}
        seen += 1
    return seen


def report(name: str, count: int, numbers: tuple[float, float, float, float]) -> None:
    median, worst, cpu_median, cpu_worst = numbers
    scaled = median * TARGET_PROCESSES / max(count, 1)
    print(
        f"{name}\n"
        f"  {count} processes: wall median {median:.1f} ms, worst {worst:.1f} ms; "
        f"CPU median {cpu_median:.1f} ms, worst {cpu_worst:.1f} ms over {RUNS} runs\n"
        f"  scaled to {TARGET_PROCESSES} processes: {scaled:.1f} ms "
        f"({scaled / RULE_MS:.1f} times the {RULE_MS:.0f} ms switching rule)\n"
        f"  as a share of one core: {cpu_median / 10:.1f}% at a 1 s interval, "
        f"{cpu_median / 50:.1f}% at 5 s (limits: 3% active, 1% idle)"
    )


def main() -> int:
    print(f"python {sys.version.split()[0]} on {sys.platform}; load average {os.getloadavg()}")
    provider = PsutilProvider()
    count = len(provider.snapshot().processes)
    report("1. baseline psutil provider, snapshot()", count, timed(provider.snapshot))

    if sys.platform.startswith("linux"):
        report("2a. direct /proc reader, stat only", proc_stat_only(), timed(proc_stat_only))
        report(
            "2b. direct /proc reader, stat + statm + io",
            proc_stat_statm_io(),
            timed(proc_stat_statm_io),
        )

    sampler, attributor = Sampler(), Attributor(RuleSet(), self_pid=os.getpid())
    sampler.ingest(provider.snapshot())

    def tick() -> None:
        batch = sampler.ingest(provider.snapshot())
        assert batch is not None
        aggregate(batch, attributor.assign(batch.processes))

    report(
        "3. baseline pipeline per tick (snapshot + deltas + attribution + totals)",
        count,
        timed(tick),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
