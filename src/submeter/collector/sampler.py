"""Turn cumulative counters into what happened during each interval.

Providers hand over running totals. The sampler keeps the previous snapshot,
subtracts, and returns one batch per interval. Because it works from totals,
a change of cadence never loses or invents CPU time: a longer interval simply
carries a larger delta.

Three cases need care, and each is handled here and nowhere else:
- a process seen for the first time, whose whole CPU time belongs to this
  interval if it was born during it, and to no interval if it is older;
- a pid that has been reused, which is a different process because identity
  is pid plus start time;
- a sleep or stall, where the interval was not observed and must be recorded
  as a gap instead of one enormous sample.
"""

from __future__ import annotations

from submeter.core.models import (
    ProcessCounters,
    ProcessKey,
    ProcessSample,
    SampleBatch,
    Snapshot,
)


def _delta(now: int | None, before: int | None) -> int | None:
    if now is None or before is None:
        return None
    return max(0, now - before)


def _zero(value: int | None) -> int | None:
    return None if value is None else 0


class Sampler:
    def __init__(self, *, gap_after_s: float = 30.0, suspend_slack_s: float = 2.0) -> None:
        self._gap_after_s = gap_after_s
        self._suspend_slack_s = suspend_slack_s
        self._previous: Snapshot | None = None
        self._known: dict[ProcessKey, ProcessCounters] = {}

    def ingest(self, snapshot: Snapshot) -> SampleBatch | None:
        """Return the batch for the interval ending here. The first call returns None."""
        previous, known = self._previous, self._known
        self._previous = snapshot
        self._known = {process.key: process for process in snapshot.processes}
        if previous is None:
            return None

        elapsed = snapshot.monotonic - previous.monotonic
        wall = snapshot.taken_at - previous.taken_at
        asleep = 0.0  # how far the interval clock ran ahead of the clock that stops in suspend
        if snapshot.awake is not None and previous.awake is not None:
            asleep = elapsed - (snapshot.awake - previous.awake)
        gap = elapsed <= 0 or elapsed > self._gap_after_s or asleep > self._suspend_slack_s
        busy = sum(snapshot.system.cpu_busy_s) - sum(previous.system.cpu_busy_s)
        return SampleBatch(
            taken_at=snapshot.taken_at,
            interval_s=max(elapsed, wall) if gap else elapsed,
            gap=gap,
            processes=tuple(
                self._sample(process, known.get(process.key), previous.taken_at, gap)
                for process in snapshot.processes
            ),
            exited=tuple(key for key in known if key not in self._known),
            logical_cores=snapshot.system.logical_cores,
            cpu_busy_s=0.0 if gap else max(0.0, busy),
            memory_available_bytes=snapshot.system.memory_available_bytes,
        )

    @staticmethod
    def _sample(
        now: ProcessCounters,
        before: ProcessCounters | None,
        previous_at: float,
        gap: bool,
    ) -> ProcessSample:
        if gap:
            cpu_s, read, write = 0.0, _zero(now.io_read_bytes), _zero(now.io_write_bytes)
        elif before is not None:
            cpu_s = max(0.0, now.cpu_s - before.cpu_s)
            read = _delta(now.io_read_bytes, before.io_read_bytes)
            write = _delta(now.io_write_bytes, before.io_write_bytes)
        elif now.key.started >= previous_at - 1.0:
            cpu_s, read, write = now.cpu_s, now.io_read_bytes, now.io_write_bytes
        else:
            cpu_s, read, write = 0.0, _zero(now.io_read_bytes), _zero(now.io_write_bytes)
        return ProcessSample(
            key=now.key,
            parent_pid=now.parent_pid,
            exe=now.exe,
            name=now.name,
            cmdline=now.cmdline,
            cwd=now.cwd,
            cpu_s=cpu_s,
            io_read_bytes=read,
            io_write_bytes=write,
            memory_bytes=now.memory_bytes,
            threads=now.threads,
            first_seen=before is None,
            restricted=now.restricted,
        )


def hot_keys(batch: SampleBatch, *, cpu_threshold: float) -> frozenset[ProcessKey]:
    """Processes worth sampling at the active interval: new ones, and any above the threshold."""
    if batch.interval_s <= 0:
        return frozenset()
    return frozenset(
        sample.key
        for sample in batch.processes
        if sample.first_seen or sample.cpu_s / batch.interval_s >= cpu_threshold
    )
