"""Verifier probe for S11: what a fixed UTC offset in daily_minimums does to the slow-growth slope.

Reads and measures only. Creates nothing. Nothing is timed. Sets TZ for this process only.

    uv run python docs/review/probes/verify-6/v6_local_days.py

Hourly memory readings for New York, 18 October to 14 November 2026, across the 1 November
change. Memory grows 10 MiB a day with a nightly low at 00:00 to 01:00 local time. Daily minimums
are taken two ways: with the one offset the zone has on 20 November (what a caller can pass to
daily_minimums), and with each reading's own offset from the operating system through
datetime.astimezone(), which needs no zone database package. The Theil-Sen slope over the
daily minimums is compared. Also reports whether the tzdata package is installed.
"""

from __future__ import annotations

import importlib.util
import os
import time
from datetime import UTC, datetime

from submeter.analysis.growth import daily_minimums, theil_sen

MIB, DAY = 1024**2, 86400.0


def local_offset(moment: float) -> float:
    shifted = datetime.fromtimestamp(moment, UTC).astimezone()
    offset = shifted.utcoffset()
    return 0.0 if offset is None else offset.total_seconds()


def main() -> None:
    os.environ["TZ"] = "America/New_York"
    time.tzset()
    start = datetime(2026, 10, 18, 4, tzinfo=UTC).timestamp()
    times, values = [], []
    for hour in range(28 * 24):
        moment = start + hour * 3600
        local_hour = (moment + local_offset(moment)) % DAY // 3600
        nightly = 0.0 if local_hour == 0 else 200.0 * MIB
        times.append(moment)
        values.append(1000 * MIB + 10 * MIB * hour / 24 + nightly)
    fixed = local_offset(datetime(2026, 11, 20, 12, tzinfo=UTC).timestamp())
    fixed_lows = daily_minimums(times, values, utc_offset_s=fixed)
    true: dict[str, float] = {}
    for moment, value in zip(times, values, strict=True):
        day = datetime.fromtimestamp(moment, UTC).astimezone().date().isoformat()
        true[day] = min(value, true.get(day, value))
    offsets = sorted({local_offset(t) / 3600 for t in times})
    print(
        f"offsets the OS gives across the window, in hours: {offsets}; "
        f"fixed offset {fixed / 3600:g}"
    )
    wrong = [
        datetime.fromtimestamp(start_, UTC).date().isoformat()
        for start_, low in fixed_lows
        if low > 1000 * MIB + 10 * MIB * ((start_ - start) / DAY + 1)
    ]
    print(f"days whose fixed-offset minimum misses the nightly low: {wrong}")
    slope_fixed = theil_sen([t for t, _ in fixed_lows], [v for _, v in fixed_lows]) * DAY / MIB
    true_items = sorted(true.items())
    true_x = [datetime.fromisoformat(d).replace(tzinfo=UTC).timestamp() for d, _ in true_items]
    slope_true = theil_sen(true_x, [v for _, v in true_items]) * DAY / MIB
    print(
        f"Theil-Sen slope of daily minimums: fixed offset {slope_fixed:.2f} MiB/day, "
        f"per-reading offset {slope_true:.2f} MiB/day (true 10.00)"
    )
    print(f"tzdata package installed: {importlib.util.find_spec('tzdata') is not None}")


if __name__ == "__main__":
    main()
