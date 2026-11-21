"""Probe: can check_growth meet "50 MB an hour is flagged within two hours" at the defaults?

Nothing is read from the machine and nothing is written. Run from the repository root:

    uv run python docs/review/probes/e-baseline/growth_cases.py

It feeds check_growth one point a minute, the tier the brief names for this check, with the
default settings: min_duration 2h and min_slope 50MB/h. Each series is a steady leak with a
little noise. It reports when, if ever, the leak is first flagged.
"""

from __future__ import annotations

import random

from submeter.analysis.growth import check_growth
from submeter.core.config import Settings

MB = 1024**2
LEAK = Settings().analysis.leak


def first_flag(rate_mb_per_hour: float, noise_mb: float, seed: int) -> tuple[int | None, str]:
    """Minutes until the first flag, checking once a minute for six hours."""
    rng = random.Random(seed)
    xs = [60.0 * minute for minute in range(361)]
    ys = [
        3e9 + rate_mb_per_hour * MB * x / 3600 + rng.uniform(-noise_mb, noise_mb) * MB for x in xs
    ]
    reason = ""
    for points in range(2, len(xs) + 1):
        result = check_growth(
            xs[:points],
            ys[:points],
            min_duration_s=LEAK.min_duration,
            min_slope_per_s=LEAK.min_slope,
        )
        reason = result.reason
        if result.flagged:
            return points - 1, reason
    return None, reason


def main() -> None:
    print(
        f"defaults: min_duration {LEAK.min_duration / 3600:g} h, "
        f"min_slope {LEAK.min_slope * 3600 / MB:g} MB/h"
    )
    at_two_hours = check_growth(
        [60.0 * m for m in range(120)],
        [3e9 + 80 * MB * m / 60 for m in range(120)],
        min_duration_s=LEAK.min_duration,
        min_slope_per_s=LEAK.min_slope,
    )
    print(
        "an 80 MB/h leak with no noise, 120 minute buckets (two hours of data): "
        f"flagged={at_two_hours.flagged}, reason={at_two_hours.reason!r}, "
        f"duration_s={at_two_hours.duration_s:g}"
    )
    decimal = 50e6 / MB  # "50 MB" read as 50,000,000 bytes, in the binary MB used here
    for rate, noise in (
        (50.0, 0.0),
        (50.0, 2.0),
        (50.0, 20.0),
        (decimal, 0.0),
        (55.0, 20.0),
        (75.0, 20.0),
    ):
        results = [first_flag(rate, noise, seed) for seed in range(20)]
        flagged = sorted(minutes for minutes, _ in results if minutes is not None)
        never = [reason for minutes, reason in results if minutes is None]
        prompt = sum(1 for minutes in flagged if minutes <= 125)
        when = f"first flag after {flagged[0]} to {flagged[-1]} min" if flagged else "never"
        print(
            f"leak {rate:g} MB/h, noise +/-{noise:g} MB, 20 runs of 6 h: {prompt} flagged within "
            f"125 min, {len(flagged)} flagged at all ({when}), {len(never)} never"
            + (f" ({never[0]})" if never else "")
        )


if __name__ == "__main__":
    main()
