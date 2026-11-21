"""A fixed-bin histogram that can be merged, so percentiles survive rollups.

A percentile of percentiles is not a percentile. Keeping a small histogram in
every bucket fixes that: merging two histograms is adding their bins, and a
percentile over any period is read from the merged bins.

Bins are spaced geometrically between `low` and `high`, with one bin below and
one above. A reported percentile lands in the right bin, so it is within one
bin of the true value: a factor of about 1.17 with the scales defined here.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class Scale:
    """Where the bin edges are. Two histograms can be merged only on the same scale."""

    low: float
    high: float
    bins: int = 64

    @property
    def size(self) -> int:
        return self.bins + 2

    def index(self, value: float) -> int:
        if value < self.low:
            return 0
        if value >= self.high:
            return self.bins + 1
        position = math.log(value / self.low) / math.log(self.high / self.low)
        return 1 + min(self.bins - 1, int(position * self.bins))

    def edges(self, index: int) -> tuple[float, float]:
        """Lower and upper edge of a bin. The first bin starts at zero."""
        if index <= 0:
            return 0.0, self.low
        if index > self.bins:
            return self.high, self.high
        ratio = self.high / self.low
        return (
            self.low * math.pow(ratio, (index - 1) / self.bins),
            self.low * math.pow(ratio, index / self.bins),
        )


CORES: Final = Scale(low=0.01, high=256.0)
MEMORY: Final = Scale(low=16 * 1024**2, high=256 * 1024**3)


def empty(scale: Scale) -> list[float]:
    return [0.0] * scale.size


def add(counts: list[float], scale: Scale, value: float, weight: float = 1.0) -> None:
    """Add one observation in place. Weight is usually the seconds it was observed for."""
    counts[scale.index(value)] += weight


def merge(first: Sequence[float], second: Sequence[float]) -> tuple[float, ...]:
    """Add two histograms bin by bin. They must share a scale; only the bin count is checked."""
    if len(first) != len(second):
        raise ValueError("histograms with different bin counts cannot be merged")
    return tuple(a + b for a, b in zip(first, second, strict=True))


def percentile(counts: Sequence[float], scale: Scale, q: float) -> float | None:
    """Return the q-th percentile (q from 0 to 100), or None for an empty histogram."""
    if len(counts) != scale.size:
        raise ValueError("histogram does not match the scale")
    total = sum(counts)
    if total <= 0:
        return None
    # The top of the highest filled bin. Float weights can leave the running sum short of
    # the total, so q=100 and a loop that never reaches the target both end here.
    top = scale.edges(max(index for index, count in enumerate(counts) if count > 0))[1]
    if q >= 100:
        return top
    target = total * max(q, 0.0) / 100.0
    running = 0.0
    for index, count in enumerate(counts):
        if count <= 0:
            continue
        if running + count >= target:
            lower, upper = scale.edges(index)
            inside = (target - running) / count
            if lower <= 0 or upper == lower:
                return lower + (upper - lower) * inside
            return lower * math.pow(upper / lower, inside)
        running += count
    return top
