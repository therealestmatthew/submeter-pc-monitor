"""Tests for the raw store and the rollup functions."""

from __future__ import annotations

from pathlib import Path

from submeter.core.models import SampleBatch, WorkloadSample
from submeter.store.raw import RawFile
from submeter.store.rollup import roll_up

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


def test_one_hour_read_and_rolled_up_matches_the_whole_day_rollup(tmp_path: Path) -> None:
    """R53: the reader and roll_up put a sample in the bucket that holds its end."""
    raw, written, at = RawFile(tmp_path / "day.db"), [], DAY0 + 0.3 * 5.0
    while at < DAY0 + 4 * HOUR:
        written.append(workload(at, 5.0, 5.0))  # exactly one core, first tick 0.3 x 5 s late
        raw.write(batch(at, 5.0), written[-1:], {})
        at += 5.0
    hour = DAY0 + 2 * HOUR
    buckets = roll_up(raw.workload_samples(hour, hour + HOUR), width_s=HOUR, logical_cores=8)
    raw.close()
    whole_day = [b for b in roll_up(written, width_s=HOUR, logical_cores=8) if b.start == hour]
    assert [(b.start - hour, b.cpu_s) for b in buckets] == [(0.0, HOUR)]
    assert buckets == whole_day
