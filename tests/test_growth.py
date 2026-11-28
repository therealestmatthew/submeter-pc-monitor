"""Tests for the growth arithmetic: slopes, plateaus, usual ranges and local days."""

from __future__ import annotations

import random
import sys
import time
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from builders import MB

from submeter.analysis.growth import (
    GrowthResult,
    check_growth,
    daily_minimums,
    theil_sen,
    usual_range,
)


def grows(xs: list[float], ys: list[float]) -> GrowthResult:
    return check_growth(xs, ys, min_duration_s=2 * 3600.0, min_slope_per_s=50 * MB / 3600)


def test_growth_flags_a_leak_and_clears_a_warm_up() -> None:
    rng = random.Random(9)
    minutes = [60.0 * i for i in range(300)]  # five hours of minute buckets
    noise = [rng.uniform(-3e7, 3e7) for _ in minutes]
    leak = [3.1e9 + 105_000 * t + n for t, n in zip(minutes, noise, strict=True)]  # ~380 MB/h
    warm = [
        3.6e9 + 9e8 * (1 - 2.718 ** (-t / 1200)) + n for t, n in zip(minutes, noise, strict=True)
    ]
    late = [3.1e9 + 100_000 * min(t, 12_600.0) + n for t, n in zip(minutes, noise, strict=True)]
    flat = [3.4e9 + n for n in noise]
    assert grows(minutes, leak).flagged
    assert not grows(minutes, warm).flagged  # a cache filling in the first half hour
    assert grows(minutes, late).reason == "growth has levelled off"  # climbed, then stopped
    assert grows(minutes, flat).reason == "growth is below the threshold"
    assert grows(minutes[:60], leak[:60]).reason == "not enough data yet"
    spiked = [2.0 * x if x != 10 else 1000.0 for x in range(20)]
    assert theil_sen([float(x) for x in range(20)], spiked) == pytest.approx(
        2.0
    )  # one spike changes nothing


def test_usual_range_and_daily_minimums() -> None:
    low, middle, high = usual_range([3.4, 3.35, 3.45, 3.4, 3.38, 3.42, 3.41]) or (0, 0, 0)
    assert low < 3.35 and high > 3.45 and middle == 3.4 and not low < 4.25 < high
    assert usual_range([1.0, 2.0]) is None
    day0, day1 = (datetime(2026, 11, day).timestamp() for day in (20, 21))  # local midnights
    assert daily_minimums([day0 + 10, day0 + 20, day1 + 5], [5.0, 3.0, 7.0]) == [
        (day0, 3.0),
        (day1, 7.0),
    ]


@pytest.fixture
def london(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    if sys.platform == "win32":
        pytest.skip("time.tzset exists only on POSIX")
    monkeypatch.setenv("TZ", "GMT0BST,M3.5.0/1,M10.5.0")  # Europe/London's rule, no zone files
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


def utc(day: int, hour: int, minute: int = 0) -> float:
    return datetime(2026, 10, day, hour, minute, tzinfo=UTC).timestamp()


@pytest.mark.usefixtures("london")
def test_local_days_follow_the_daylight_saving_change() -> None:
    # Clocks go back at 01:00 UTC on 25 October 2026, so that local day lasts 25 hours.
    times = [utc(24, 23, 30), utc(25, 23, 30), utc(26, 0, 30)]  # 00:30 BST, 23:30 and 00:30 GMT
    assert daily_minimums(times, [5.0, 3.0, 7.0]) == [(utc(24, 23), 3.0), (utc(26, 0), 7.0)]
