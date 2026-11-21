"""The arithmetic behind leak detection and the usual range.

A leak is sustained growth with no plateau. The slope comes from the Theil-Sen
estimator, the median of the slopes between pairs of points, which one spike
cannot move. Growth that levels off is a cache warming up and is cleared.

The usual range is the median plus or minus a number of spreads, where spread
is the median absolute deviation scaled to match a standard deviation. Both
tolerate outliers, so one bad day does not widen the range.

These functions take plain numbers. The detectors that call them decide which
tier the numbers come from: minute buckets for the hourly check, daily
minimums of hourly buckets for the slow one.
"""

from __future__ import annotations

from collections.abc import Sequence
from statistics import median

from submeter.core.models import Record

_MAD_TO_SIGMA = 1.4826


def theil_sen(xs: Sequence[float], ys: Sequence[float], *, max_points: int = 300) -> float:
    """Median slope between all pairs of points. Thinned evenly above max_points."""
    if len(xs) != len(ys):
        raise ValueError("xs and ys must be the same length")
    if len(xs) > max_points:
        stride = len(xs) / max_points
        picks = [int(i * stride) for i in range(max_points)]
        xs, ys = [xs[i] for i in picks], [ys[i] for i in picks]
    slopes = [
        (ys[j] - ys[i]) / (xs[j] - xs[i])
        for i in range(len(xs))
        for j in range(i + 1, len(xs))
        if xs[j] != xs[i]
    ]
    if not slopes:
        raise ValueError("at least two points at different times are needed")
    return median(slopes)


def plateaued(
    xs: Sequence[float], ys: Sequence[float], *, tail: float = 1 / 3, ratio: float = 0.25
) -> bool:
    """True when the last part of the series grows far more slowly than the whole."""
    cut = int(len(xs) * (1 - tail))
    if len(xs) - cut < 3:
        return False
    overall = theil_sen(xs, ys)
    return overall <= 0 or theil_sen(xs[cut:], ys[cut:]) < ratio * overall


class GrowthResult(Record):
    flagged: bool
    slope_per_s: float
    duration_s: float
    reason: str


def check_growth(
    xs: Sequence[float],
    ys: Sequence[float],
    *,
    min_duration_s: float,
    min_slope_per_s: float,
    min_points: int = 8,
) -> GrowthResult:
    """Decide whether a series is a leak: long enough, steep enough, and still climbing."""
    duration = xs[-1] - xs[0] if xs else 0.0
    if len(xs) < min_points or duration < min_duration_s:
        return GrowthResult(
            flagged=False, slope_per_s=0.0, duration_s=duration, reason="not enough data yet"
        )
    slope = theil_sen(xs, ys)
    if slope < min_slope_per_s:
        reason, flagged = "growth is below the threshold", False
    elif plateaued(xs, ys):
        reason, flagged = "growth has levelled off", False
    else:
        reason, flagged = "sustained growth with no plateau", True
    return GrowthResult(flagged=flagged, slope_per_s=slope, duration_s=duration, reason=reason)


def usual_range(
    values: Sequence[float],
    *,
    sensitivity: float = 4.0,
    floor: float = 0.0,
    min_values: int = 5,
) -> tuple[float, float, float] | None:
    """Return (low, middle, high), or None while there are too few values to say."""
    if len(values) < min_values:
        return None
    middle = median(values)
    spread = max(floor, _MAD_TO_SIGMA * median(abs(value - middle) for value in values))
    return middle - sensitivity * spread, middle, middle + sensitivity * spread


def daily_minimums(
    times: Sequence[float], values: Sequence[float], *, utc_offset_s: float = 0.0
) -> list[tuple[float, float]]:
    """The lowest value of each local day, as (start of day, minimum), in time order."""
    lows: dict[float, float] = {}
    for moment, value in zip(times, values, strict=True):
        day = ((moment + utc_offset_s) // 86400) * 86400 - utc_offset_s
        lows[day] = min(value, lows.get(day, value))
    return sorted(lows.items())
