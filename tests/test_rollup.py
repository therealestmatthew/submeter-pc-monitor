"""Tests for the rollups: buckets, merges and the percentiles they keep."""

from __future__ import annotations

import random
from pathlib import Path

import pytest
from builders import DAY0, HOUR, MB, batch, workload, workload_store

from submeter.store.raw import RawFile
from submeter.store.rollup import cores_percentile, merge, roll_up, well_covered


def test_rollups_reproduce_totals_and_percentiles() -> None:
    rng = random.Random(5)
    samples = [
        workload(DAY0 + second, rng.random() * 4, memory=int((200 + rng.random() * 50) * MB))
        for second in range(3600)
    ]
    minutes = roll_up(samples, width_s=60, logical_cores=16)
    hour = merge(minutes, start=DAY0, width_s=3600)
    direct = roll_up(samples, width_s=3600, logical_cores=16)[0]
    assert len(minutes) == 60 and minutes[0].covered_s == 60 and well_covered(hour)
    assert hour.cpu_s == pytest.approx(sum(sample.cpu_s for sample in samples))
    assert hour.cpu_s == pytest.approx(direct.cpu_s) and hour.memory_mean == pytest.approx(
        direct.memory_mean
    )
    assert (hour.memory_min, hour.memory_max) == (direct.memory_min, direct.memory_max)
    assert cores_percentile(hour, 95) == pytest.approx(cores_percentile(direct, 95))
    with pytest.raises(ValueError, match="different series"):
        merge(
            [minutes[0], minutes[1].model_copy(update={"series": "other"})],
            start=DAY0,
            width_s=3600,
        )


def test_one_hour_read_and_rolled_up_matches_the_whole_day_rollup(tmp_path: Path) -> None:
    """R53: the reader and roll_up put a sample in the bucket that holds its end."""
    raw, written, at = RawFile(tmp_path / "day.db"), [], DAY0 + 0.3 * 5.0
    while at < DAY0 + 4 * HOUR:
        written.append(workload_store(at, 5.0, 5.0))  # exactly one core, first tick 0.3 x 5 s late
        raw.write(batch(at, 5.0), written[-1:], {})
        at += 5.0
    hour = DAY0 + 2 * HOUR
    read = RawFile.workload_samples(raw.path, hour, hour + HOUR)
    buckets = roll_up(read, width_s=HOUR, logical_cores=8)
    raw.close()
    whole_day = [b for b in roll_up(written, width_s=HOUR, logical_cores=8) if b.start == hour]
    assert [(b.start - hour, b.cpu_s) for b in buckets] == [(0.0, HOUR)]
    assert buckets == whole_day


def test_a_bucket_keeps_its_interval_bounds_and_capacity_in_core_seconds() -> None:
    """R94: merging across a core-count change keeps the capacity of each part."""
    mixed = [workload_store(DAY0 + 1, 1.0, 1.0), workload_store(DAY0 + 6, 5.0, 5.0)]
    four = roll_up(mixed, width_s=HOUR, logical_cores=4)[0]
    eight = roll_up([workload_store(DAY0 + HOUR + 5, 5.0, 5.0)], width_s=HOUR, logical_cores=8)[0]
    merged = merge([four, eight], start=DAY0, width_s=2 * HOUR)
    assert merged.capacity_core_s == four.covered_s * 4 + eight.covered_s * 8 == 64.0
    assert (four.interval_min_s, four.interval_max_s) == (1.0, 5.0)
    assert (merged.interval_min_s, merged.interval_max_s) == (1.0, 5.0)
