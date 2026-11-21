"""Tests for the analysis arithmetic: histogram percentiles and local days."""

from __future__ import annotations

from submeter.core import histogram


def test_top_percentile_is_the_highest_filled_bin_with_float_weights() -> None:
    counts = histogram.empty(histogram.CORES)
    for step in range(10):  # ten 0.1 s intervals, as a monotonic clock gives them
        histogram.add(counts, histogram.CORES, 0.5 * (step + 1), 0.1)
    highest = histogram.CORES.edges(histogram.CORES.index(5.0))[1]
    assert histogram.percentile(counts, histogram.CORES, 100) == highest  # not 256 cores
