"""Tests for the raw store and the rollup functions."""

from __future__ import annotations

from pathlib import Path

import pytest

from submeter.attribution.rules import Attributor, RuleSet, aggregate
from submeter.collector.sampler import Sampler
from submeter.core.models import (
    ProcessCounters,
    ProcessKey,
    ProcessSample,
    SampleBatch,
    Snapshot,
    SystemCounters,
    WorkloadSample,
)
from submeter.store.raw import RawFile
from submeter.store.rollup import merge, roll_up, well_covered

DAY0 = 1_795_132_800.0  # 2026-11-20 00:00:00 UTC
HOUR = 3600.0


def workload(at: float, cpu: float, interval: float, **extra: object) -> WorkloadSample:
    fields: dict[str, object] = {"workload": "steady", "source": "polled", "memory_bytes": 100}
    fields |= {"io_read_bytes": 0, "io_write_bytes": 0, "processes": 1, "started": 0, **extra}
    return WorkloadSample(taken_at=at, interval_s=interval, cpu_s=cpu, **fields)


def batch(at: float, interval: float, **extra: object) -> SampleBatch:
    fields: dict[str, object] = {"gap": False, "processes": (), "exited": (), "logical_cores": 8}
    fields |= {"cpu_busy_s": 0.0, "memory_available_bytes": 1, **extra}
    return SampleBatch(taken_at=at, interval_s=interval, **fields)


def process(pid: int, cpu: float, **extra: object) -> ProcessSample:
    fields: dict[str, object] = {"exe": "tool", "cmdline": ("tool",), "cwd": None, "threads": 1}
    fields |= {"parent_pid": None, "io_read_bytes": 0, "io_write_bytes": 0, "memory_bytes": 100}
    fields |= {"first_seen": True, "restricted": False, **extra}
    return ProcessSample(key=ProcessKey(pid=pid, started=1.0), cpu_s=cpu, **fields)


def snap(at: float, cpu: float) -> Snapshot:
    process = ProcessCounters(key=ProcessKey(pid=7, started=1.0), cpu_s=cpu, memory_bytes=100)
    system = SystemCounters(
        logical_cores=2, cpu_busy_s=(cpu, 0.0), memory_total_bytes=2, memory_available_bytes=1
    )
    return Snapshot(taken_at=at, monotonic=at - DAY0, processes=(process,), system=system)


def test_one_hour_read_and_rolled_up_matches_the_whole_day_rollup(tmp_path: Path) -> None:
    """R53: the reader and roll_up put a sample in the bucket that holds its end."""
    raw, written, at = RawFile(tmp_path / "day.db"), [], DAY0 + 0.3 * 5.0
    while at < DAY0 + 4 * HOUR:
        written.append(workload(at, 5.0, 5.0))  # exactly one core, first tick 0.3 x 5 s late
        raw.write(batch(at, 5.0), written[-1:], {})
        at += 5.0
    hour = DAY0 + 2 * HOUR
    read = RawFile.workload_samples(raw.path, hour, hour + HOUR)
    buckets = roll_up(read, width_s=HOUR, logical_cores=8)
    raw.close()
    whole_day = [b for b in roll_up(written, width_s=HOUR, logical_cores=8) if b.start == hour]
    assert [(b.start - hour, b.cpu_s) for b in buckets] == [(0.0, HOUR)]
    assert buckets == whole_day


def test_a_gap_adds_its_sums_but_no_covered_time(tmp_path: Path) -> None:
    """R39: a 3600 s stall in which both clocks advance is stored and rolled up as a gap."""
    sampler, attributor, raw = Sampler(), Attributor(RuleSet()), RawFile(tmp_path / "day.db")
    for at in [DAY0 + 1000 + 5 * k for k in range(121)] + [DAY0 + 5200 + 5 * k for k in range(121)]:
        tick = sampler.ingest(snap(at, 2 * (at - DAY0)))  # two cores, then the stall, then two
        if tick is not None:
            raw.write(tick, aggregate(tick, attributor.assign(tick.processes)), {})
    before, after = roll_up(
        RawFile.workload_samples(raw.path, DAY0, DAY0 + 2 * HOUR), width_s=HOUR, logical_cores=2
    )
    raw.close()
    assert (after.covered_s, after.samples, well_covered(after)) == (600.0, 120, False)
    gap = workload(DAY0 + 9, 5.0, HOUR, gap=True, workload=before.series)
    alone = roll_up([gap], width_s=HOUR, logical_cores=2)
    assert [(b.cpu_s, b.covered_s, b.memory_mean) for b in alone] == [(5.0, 0.0, None)]
    assert merge([*alone, before], start=DAY0, width_s=HOUR).memory_mean == before.memory_mean


def test_a_bucket_keeps_its_interval_bounds_and_capacity_in_core_seconds() -> None:
    """R94: merging across a core-count change keeps the capacity of each part."""
    mixed = [workload(DAY0 + 1, 1.0, 1.0), workload(DAY0 + 6, 5.0, 5.0)]
    four = roll_up(mixed, width_s=HOUR, logical_cores=4)[0]
    eight = roll_up([workload(DAY0 + HOUR + 5, 5.0, 5.0)], width_s=HOUR, logical_cores=8)[0]
    merged = merge([four, eight], start=DAY0, width_s=2 * HOUR)
    assert merged.capacity_core_s == four.covered_s * 4 + eight.covered_s * 8 == 64.0
    assert (four.interval_min_s, four.interval_max_s) == (1.0, 5.0)
    assert (merged.interval_min_s, merged.interval_max_s) == (1.0, 5.0)


def test_reading_a_raw_file_never_writes_to_it(tmp_path: Path) -> None:
    """R91: the reader opens the file read-only, so the collector stays its only writer."""
    with pytest.raises(FileNotFoundError):
        RawFile.workload_samples(tmp_path / "2026-11-21.db", DAY0, DAY0 + HOUR)
    assert list(tmp_path.iterdir()) == []
    writer = RawFile(tmp_path / "day.db")
    for k in range(1, 11):
        writer.write(batch(DAY0 + k, 1.0), [workload(DAY0 + k, 0.5, 1.0)], {})
    wal = tmp_path / "day.db-wal"
    size = wal.stat().st_size
    assert len(RawFile.workload_samples(writer.path, DAY0, DAY0 + HOUR)) == 10
    assert wal.stat().st_size == size > 0
    writer.close()


def test_undecodable_text_and_a_failed_write_do_not_stop_later_writes(tmp_path: Path) -> None:
    """R54: undecodable text no longer fails every write, and a failed write is undone whole."""
    raw = RawFile(tmp_path / "day.db", redaction="scrub")
    odd = process(1, 0.0, exe="t\udcffl", cmdline=("tool", "caf\udce9"))
    for k in range(1, 4):
        raw.write(batch(DAY0 + k, 1.0, processes=(odd,)), [workload(DAY0 + k, 0.0, 1.0)], {})
    huge = process(3, 0.5, memory_bytes=2**63)  # SQLite cannot store it, so the write fails
    with pytest.raises(OverflowError):
        raw.write(batch(DAY0 + 4, 1.0, processes=(process(2, 0.5), huge)), [], {})
    raw.write(batch(DAY0 + 5, 1.0, processes=(process(2, 0.5),)), [], {})
    assert (raw.count("workload_raw"), raw.count("process"), raw.process_cpu_total()) == (3, 2, 0.5)
    raw.close()
    assert b"tool caf\\udce9" in raw.path.read_bytes() and b"t\\udcffl" in raw.path.read_bytes()
