"""Tests for the log-binned histograms: merging and percentiles. Run with: uv run pytest"""

from __future__ import annotations

import random

from submeter.core import histogram


def test_histogram_merges_exactly_and_bounds_error() -> None:
    rng = random.Random(1)
    values = [rng.lognormvariate(0.5, 0.8) for _ in range(4000)]
    first, second, both = (histogram.empty(histogram.CORES) for _ in range(3))
    for index, value in enumerate(values):
        histogram.add(first if index % 2 else second, histogram.CORES, value)
        histogram.add(both, histogram.CORES, value)
    assert histogram.merge(first, second) == tuple(both)
    exact = sorted(values)[int(0.95 * len(values))]
    estimate = histogram.percentile(both, histogram.CORES, 95)
    assert estimate is not None and exact / 1.18 < estimate < exact * 1.18
    assert histogram.percentile(histogram.empty(histogram.CORES), histogram.CORES, 50) is None


def test_top_percentile_is_the_highest_filled_bin_with_float_weights() -> None:
    counts = histogram.empty(histogram.CORES)
    for step in range(10):  # ten 0.1 s intervals, as a monotonic clock gives them
        histogram.add(counts, histogram.CORES, 0.5 * (step + 1), 0.1)
    highest = histogram.CORES.edges(histogram.CORES.index(5.0))[1]
    assert histogram.percentile(counts, histogram.CORES, 100) == highest  # not 256 cores
