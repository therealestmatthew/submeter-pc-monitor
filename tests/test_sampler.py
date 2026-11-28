"""Tests for the sampler: counters into deltas, new processes, pid reuse and gaps."""

from __future__ import annotations

import pytest
from builders import proc, snap

from submeter.collector.sampler import Sampler
from submeter.core import models
from submeter.core.models import ProcessCounters, ProcessKey


def test_sampler_deltas_new_processes_and_pid_reuse() -> None:
    sampler = Sampler()
    assert sampler.ingest(snap(1000, [proc(1, 5.0), proc(2, 1.0)], busy=10)) is None
    batch = sampler.ingest(
        snap(
            1001,
            [
                proc(1, 5.4),
                proc(2, 9.0, started=1000.5),
                proc(3, 0.3, started=1000.2),
                proc(4, 7.0, started=50),
            ],
            busy=11.5,
        )
    )
    assert batch is not None and not batch.gap and batch.interval_s == 1.0
    by_pid = {sample.key.pid: sample for sample in batch.processes}
    assert by_pid[1].cpu_s == pytest.approx(0.4)
    assert (
        by_pid[2].cpu_s == 9.0 and by_pid[2].first_seen
    )  # same pid, new start time: a new process
    assert by_pid[3].cpu_s == 0.3  # born in this interval: all of its CPU belongs here
    assert by_pid[4].cpu_s == 0.0  # older than the last snapshot: no baseline yet
    assert batch.exited == (ProcessKey(pid=2, started=100.0),)
    assert batch.cpu_busy_s == pytest.approx(1.5)


def test_sampler_records_a_gap_instead_of_a_spike() -> None:
    sampler = Sampler()
    sampler.ingest(snap(1000, [proc(1, 5.0)], mono=10).model_copy(update={"awake": 10.0}))
    batch = sampler.ingest(
        snap(4600, [proc(1, 5.2)], mono=3610).model_copy(update={"awake": 11.0})
    )  # an hour asleep: the clock that stops during suspend moved 1 s
    assert batch is not None and batch.gap and batch.interval_s == 3600
    assert batch.processes[0].cpu_s == 0.0 and batch.cpu_busy_s == 0.0


def tick(
    wall: float, clock: float, awake: float | None, *processes: ProcessCounters
) -> models.Snapshot:
    system = models.SystemCounters(
        logical_cores=4, cpu_busy_s=(clock,), memory_total_bytes=0, memory_available_bytes=0
    )
    return models.Snapshot(
        taken_at=wall, monotonic=clock, awake=awake, processes=processes, system=system
    )


def test_suspend_is_told_by_the_clock_that_stops_not_by_the_wall_clock() -> None:
    sampler = Sampler()
    sampler.ingest(tick(10_000, 100, 100))
    asleep = sampler.ingest(tick(6_400, 104, 101))  # 3 s asleep; wall clock stepped back an hour
    awake = sampler.ingest(tick(6_501, 105, 102))  # both clocks agree; wall clock stepped ahead
    assert asleep is not None and asleep.gap
    assert awake is not None and not awake.gap
