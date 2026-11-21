"""Tests for the analysis arithmetic: histogram percentiles and local days."""

from __future__ import annotations

import sys
import time
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from submeter.analysis.growth import daily_minimums
from submeter.core import histogram


@pytest.fixture
def london(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    if sys.platform == "win32":
        pytest.skip("time.tzset exists only on POSIX")
    monkeypatch.setenv("TZ", "GMT0BST,M3.5.0/1,M10.5.0")  # Europe/London's rule, no zone files
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


def test_top_percentile_is_the_highest_filled_bin_with_float_weights() -> None:
    counts = histogram.empty(histogram.CORES)
    for step in range(10):  # ten 0.1 s intervals, as a monotonic clock gives them
        histogram.add(counts, histogram.CORES, 0.5 * (step + 1), 0.1)
    highest = histogram.CORES.edges(histogram.CORES.index(5.0))[1]
    assert histogram.percentile(counts, histogram.CORES, 100) == highest  # not 256 cores


def utc(day: int, hour: int, minute: int = 0) -> float:
    return datetime(2026, 10, day, hour, minute, tzinfo=UTC).timestamp()


@pytest.mark.usefixtures("london")
def test_local_days_follow_the_daylight_saving_change() -> None:
    # Clocks go back at 01:00 UTC on 25 October 2026, so that local day lasts 25 hours.
    times = [utc(24, 23, 30), utc(25, 23, 30), utc(26, 0, 30)]  # 00:30 BST, 23:30 and 00:30 GMT
    assert daily_minimums(times, [5.0, 3.0, 7.0]) == [(utc(24, 23), 3.0), (utc(26, 0), 7.0)]
