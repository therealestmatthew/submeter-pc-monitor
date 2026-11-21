"""Shared helpers for the c-storage probes: synthetic snapshots like tests/test_baseline.py.

Not a probe. The scripts beside it import it, and each is run from the repository root:

    .venv/bin/python docs/review/probes/c-storage/NAME.py
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping

from submeter.attribution.rules import Attributor, RuleSet, aggregate
from submeter.collector.sampler import Sampler
from submeter.core.models import (
    ProcessCounters,
    ProcessKey,
    SampleBatch,
    Snapshot,
    SystemCounters,
    WorkloadSample,
)

MB = 1024**2
DAY0 = 1_795_132_800.0  # 2026-11-20 00:00:00 UTC, the day the baseline tests use
Step = tuple[SampleBatch, tuple[WorkloadSample, ...], Mapping[ProcessKey, str]]


def proc(pid: int, cpu: float, *, started: float = 100.0, **extra: object) -> ProcessCounters:
    """One process's cumulative counters, 50 MiB unless told otherwise."""
    fields: dict[str, object] = {"exe": "tool", "cmdline": ("tool",), "memory_bytes": 50 * MB}
    fields.update(extra)
    return ProcessCounters(key=ProcessKey(pid=pid, started=started), cpu_s=cpu, **fields)


def snap(
    at: float, processes: Iterable[ProcessCounters], *, mono: float | None = None, busy: float = 0.0
) -> Snapshot:
    """A snapshot of a 4-core machine. The monotonic clock follows the wall clock unless given."""
    system = SystemCounters(
        logical_cores=4,
        cpu_busy_s=(busy, 0.0, 0.0, 0.0),
        memory_total_bytes=16 * 1024**3,
        memory_available_bytes=8 * 1024**3,
    )
    return Snapshot(
        taken_at=at,
        monotonic=at if mono is None else mono,
        processes=tuple(processes),
        system=system,
    )


def workload(
    at: float, cpu: float, *, interval: float = 1.0, memory: int = 100 * MB, name: str = "agents"
) -> WorkloadSample:
    return WorkloadSample(
        taken_at=at,
        interval_s=interval,
        workload=name,
        source="polled",
        cpu_s=cpu,
        memory_bytes=memory,
        io_read_bytes=0,
        io_write_bytes=0,
        processes=1,
        started=0,
    )


def empty_batch(at: float, interval: float = 1.0) -> SampleBatch:
    """A batch with no processes, for probes that only care about workload rows."""
    return SampleBatch(
        taken_at=at,
        interval_s=interval,
        gap=False,
        processes=(),
        exited=(),
        logical_cores=4,
        cpu_busy_s=0.0,
        memory_available_bytes=8 * 1024**3,
    )


def pipeline(snapshots: Iterable[Snapshot], sampler: Sampler | None = None) -> Iterator[Step]:
    """Sampler, attribution with no rules, and totals: what a collector would hand the store."""
    sampler = sampler or Sampler()
    attributor = Attributor(RuleSet())
    for snapshot in snapshots:
        batch = sampler.ingest(snapshot)
        if batch is None:
            continue
        assignment = attributor.assign(batch.processes)
        names = {key: value.workload for key, value in assignment.items()}
        yield batch, aggregate(batch, assignment), names


def clock(at: float) -> str:
    """Seconds since DAY0 as HH:MM:SS, with a day offset when it is not day 0."""
    day, rest = divmod(at - DAY0, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, seconds = divmod(rest, 60)
    text = f"{int(hours):02d}:{int(minutes):02d}:{seconds:05.2f}"
    return text if day == 0 else f"day{int(day):+d} {text}"
