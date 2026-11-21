"""Probe: does "the parts sum to the whole within 2%" hold when untagged processes are short-lived?

Reads and measures only. It starts its own short-lived children, which do arithmetic and exit.

    uv run python docs/review/probes/measure/reconcile_under_spawn.py [SECONDS_PER_PHASE]

Three phases, sampled at 1 s with the baseline psutil provider and sampler:
quiet, one spawner (about one core of children that live about 0.1 s), four spawners.
For each it prints the machine's busy CPU time, the sum over every process the sampler saw,
and the difference as a share of capacity, which is what the reconciliation invariant bounds.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time

from submeter.collector.sampler import Sampler
from submeter.providers.psutil_provider import PsutilProvider

CHILD = "sum(i * i for i in range(600_000))"


def spawner(stop: threading.Event, lifetimes: list[float]) -> None:
    while not stop.is_set():
        started = time.perf_counter()
        subprocess.run([sys.executable, "-S", "-c", CHILD], check=False)
        lifetimes.append(time.perf_counter() - started)


def phase(name: str, spawners: int, seconds: int) -> None:
    stop, lifetimes = threading.Event(), []
    threads = [
        threading.Thread(target=spawner, args=(stop, lifetimes), daemon=True)
        for _ in range(spawners)
    ]
    for thread in threads:
        thread.start()
    time.sleep(1.0)
    provider, sampler = PsutilProvider(), Sampler()
    me = os.getpid()
    sampler.ingest(provider.snapshot())
    children_before = os.times()
    busy = seen = capacity = own = 0.0
    for _ in range(seconds):
        time.sleep(1.0)
        batch = sampler.ingest(provider.snapshot())
        assert batch is not None and not batch.gap
        busy += batch.cpu_busy_s
        seen += sum(sample.cpu_s for sample in batch.processes)
        own += sum(sample.cpu_s for sample in batch.processes if sample.key.pid == me)
        capacity += batch.interval_s * batch.logical_cores
    children_after = os.times()
    stop.set()
    for thread in threads:
        thread.join()
    reaped = (
        children_after.children_user
        + children_after.children_system
        - children_before.children_user
        - children_before.children_system
    )
    missing = busy - seen
    life = f"{1000 * sum(lifetimes) / len(lifetimes):.0f} ms" if lifetimes else "n/a"
    print(
        f"{name}: {len(lifetimes)} children, mean life {life}\n"
        f"  machine busy {busy:.2f} CPU-s of {capacity:.0f} available "
        f"({100 * busy / capacity:.1f}%)\n"
        f"  seen in processes {seen:.2f} CPU-s; missing {missing:.2f} CPU-s = "
        f"{100 * missing / capacity:.1f}% of capacity, {100 * missing / busy:.0f}% of busy time "
        "(invariant: 2% of capacity)\n"
        f"  children this probe reaped used {reaped:.2f} CPU-s, of which the snapshots "
        f"could have seen little; the probe itself used {own:.2f} CPU-s"
    )


def main() -> int:
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    print(
        f"python {sys.version.split()[0]} on {sys.platform}, {os.cpu_count()} logical cores; "
        f"load average {os.getloadavg()}"
    )
    phase("quiet", 0, seconds)
    phase("one spawner", 1, seconds)
    phase("four spawners", 4, seconds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
