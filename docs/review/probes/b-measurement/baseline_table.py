"""Probe: the baseline table in docs/07 against the baseline's usual_range(), and the
slow-growth check against the baseline's daily_minimums() and check_growth().

Logic only, on the numbers printed in docs/07 and on synthetic series. No process is read.

    uv run python docs/review/probes/b-measurement/baseline_table.py

1. Recompute the usual range for days 8 to 30 two ways: with the 0.03 GB floor applied to the
   median absolute deviation before scaling (the sentence in docs/07), and with it applied to
   the scaled spread (what usual_range(floor=0.03) does). Compare each with the table.
2. The same rule on minute buckets, which is where docs/17 says baselines come from.
3. Slow growth: a 10 MiB/h leak for 7 days, fitted on daily minimums with the defaults.
"""

from __future__ import annotations

import random
from statistics import median

from submeter.analysis.growth import check_growth, daily_minimums, usual_range
from submeter.core.config import load_settings

PEAKS = [
    3.44, 3.45, 3.34, 3.42, 3.32, 3.42, 3.44, 3.39, 3.48, 3.35, 3.46, 3.45, 3.43, 3.30, 3.39,
    3.36, 3.48, 3.36, 3.45, 3.44, 3.35, 3.30, 4.31, 4.19, 4.20, 4.17, 4.24, 4.35, 4.20, 4.17,
]  # fmt: skip
TABLE = {
    8: (3.25, 3.60), 9: (3.24, 3.60), 10: (3.25, 3.60), 11: (3.23, 3.61), 12: (3.24, 3.61),
    13: (3.25, 3.61), 14: (3.25, 3.61), 15: (3.25, 3.61), 16: (3.23, 3.61), 17: (3.14, 3.67),
    18: (3.23, 3.61), 19: (3.13, 3.68), 20: (3.23, 3.62), 21: (3.19, 3.69), 22: (3.13, 3.70),
    **{day: (3.09, 3.73) for day in range(23, 31)},
}  # fmt: skip
MIB = 1024**2


def doc_range(values: list[float]) -> tuple[float, float]:
    middle = median(values)
    deviation = max(0.03, median(abs(value - middle) for value in values))
    return middle - 4 * 1.4826 * deviation, middle + 4 * 1.4826 * deviation


def code_range(values: list[float]) -> tuple[float, float]:
    low, _, high = usual_range(values, sensitivity=4.0, floor=0.03) or (0.0, 0.0, 0.0)
    return low, high


def replay(name: str, rule: object) -> None:
    kept: list[float] = []
    off, flags = [], []
    for day, peak in enumerate(PEAKS, start=1):
        if day >= 8:
            low, high = rule(kept[-14:])  # type: ignore[operator]
            want = TABLE[day]
            if abs(low - want[0]) > 0.0151 or abs(high - want[1]) > 0.0151:
                off.append(f"day {day}: {low:.2f} to {high:.2f}, table {want[0]} to {want[1]}")
            if not low <= peak <= high:
                flags.append(day)
                continue
        kept.append(peak)
    print(f"   {name}")
    print(f"      days flagged: {flags}")
    print(f"      ranges more than 0.015 GB from the table: {len(off)} of 23")
    for line in off[:4]:
        print(f"         {line}")


def main() -> None:
    print("1. docs/07 table, replayed from its own daily peaks")
    replay("floor on the deviation, as the sentence in docs/07 says", doc_range)
    replay("floor on the scaled spread, as usual_range(floor=0.03) does", code_range)
    halves = [f"{(TABLE[day][1] - TABLE[day][0]) / 2:.3f}" for day in range(8, 17)]
    print(
        f"      half-widths printed for days 8 to 16: {' '.join(halves)}\n"
        f"      a floor of 0.03 on the deviation gives {4 * 1.4826 * 0.03:.3f}; "
        f"on the scaled spread it gives {4 * 0.03:.3f}"
    )
    week = PEAKS[:7]
    print(
        f"      day 8 from days 1 to 7: sentence {doc_range(week)[0]:.3f} to "
        f"{doc_range(week)[1]:.3f}, code {code_range(week)[0]:.3f} to {code_range(week)[1]:.3f}"
    )
    print(
        "      usual_range() defaults: floor=0.0 and min_values=5; core/config.py has no floor "
        "setting"
    )
    flat = [3.40] * 13 + [3.41]
    print(f"      a steady series with the default floor: {usual_range(flat)} for {flat[-2:]}")

    print("\n2. the same rule on minute buckets: 14 days of history, then one more day")
    rng = random.Random(7)
    for name, draw in (
        (
            "cores in use, lognormal(0.5, 0.8) as in the histogram test",
            lambda: rng.lognormvariate(0.5, 0.8),
        ),
        ("memory in GB, 3.4 with normal noise of 0.05", lambda: rng.gauss(3.4, 0.05)),
    ):
        history = [draw() for _ in range(14 * 1440)]
        low, middle, high = usual_range(history, sensitivity=4.0) or (0.0, 0.0, 0.0)
        outside = sum(1 for _ in range(1440) if not low <= draw() <= high)
        print(
            f"   {name}: range {low:.2f} to {high:.2f} around {middle:.2f}; "
            f"{outside} of 1440 ordinary minutes fall outside"
        )

    print("\n3. slow growth: 10 MiB/h for 7 days on hourly buckets, defaults from core/config.py")
    settings = load_settings().settings.analysis
    print(
        f"   settings: slow_growth has {sorted(type(settings.slow_growth).model_fields)}; "
        f"leak.min_slope is {settings.leak.min_slope * 3600 / MIB:.0f} MiB/h"
    )
    for label, offset_h in (("window starts at midnight", 0), ("window starts at 09:00", 9)):
        hours = [3600.0 * (offset_h + i) for i in range(7 * 24)]
        values = [3.0 * 1024**3 + 10 * MIB * i for i in range(7 * 24)]
        lows = daily_minimums(hours, values)
        xs, ys = [day for day, _ in lows], [low for _, low in lows]
        for slope_name, slope in (
            ("leak.min_slope", settings.leak.min_slope),
            ("no threshold", 0.0),
        ):
            result = check_growth(
                xs, ys, min_duration_s=settings.slow_growth.window, min_slope_per_s=slope
            )
            span = (xs[-1] - xs[0]) / 86400
            print(
                f"   {label}: {len(lows)} daily minimums spanning {span:.0f} days, "
                f"{slope_name}: flagged={result.flagged}, {result.reason}"
            )


if __name__ == "__main__":
    main()
