"""Probe: local days worked out from hourly buckets stored in UTC.

Reads and measures only. Nothing is written. Uses this machine's time zone database through
zoneinfo, which Windows does not have unless the tzdata package is installed.

    .venv/bin/python docs/review/probes/c-storage/local_days.py

1. analysis.growth.daily_minimums takes one fixed UTC offset. Across a daylight-saving change
   the offset of the day it is asked on is wrong for the other side of the change.
2. A zone that is not a whole number of hours from UTC puts local midnight inside an hourly
   bucket, so a local day cannot be cut exactly from the hourly tier.
"""

from __future__ import annotations

import importlib.util
import zoneinfo
from collections import Counter
from datetime import UTC, date, datetime, timedelta

from submeter.analysis.growth import daily_minimums

HOUR = 3600.0


def stamp(day: date, hour: float = 0.0) -> float:
    return datetime.combine(day, datetime.min.time(), UTC).timestamp() + hour * HOUR


def hours(first: date, days: int) -> list[float]:
    return [stamp(first) + HOUR * index for index in range(days * 24)]


def fixed_day(moment: float, offset_s: float) -> date:
    """The day daily_minimums puts a moment in, read back from the day start it returns."""
    start = daily_minimums([moment], [0.0], utc_offset_s=offset_s)[0][0]
    return datetime.fromtimestamp(start + offset_s, UTC).date()


def daylight_saving() -> None:
    zone = zoneinfo.ZoneInfo("America/New_York")
    asked = datetime(2026, 11, 20, 9, tzinfo=UTC)
    offset = asked.astimezone(zone).utcoffset().total_seconds()
    starts = hours(date(2026, 10, 25), 14)  # two weeks of hourly buckets around 1 November
    moved = [t for t in starts if fixed_day(t, offset) != datetime.fromtimestamp(t, zone).date()]
    lengths = Counter(datetime.fromtimestamp(t, zone).date() for t in starts)
    odd = {str(day): count for day, count in lengths.items() if count not in (24,)}
    print(
        f"1. New York, asked on 20 November (UTC{offset / HOUR:+.0f}): of {len(starts)} hourly "
        f"buckets from 25 October to 7 November, {len(moved)} fall in a different local day "
        f"under the fixed offset, all before the change on 1 November. Days that are not 24 "
        f"hours long, counting whole buckets inside the window: {odd}"
    )
    # a process restarted every night at 00:30 local time: its lowest memory is in that hour
    values = [1.0 if datetime.fromtimestamp(t, zone).hour == 0 else 5.0 for t in starts]
    lows = daily_minimums(starts, values, utc_offset_s=offset)
    flat = [str(datetime.fromtimestamp(s + offset, UTC).date()) for s, low in lows if low > 1.0]
    print(
        f"   a nightly low at 00:00 to 01:00 local time is present in every true local day; "
        f"with the fixed offset these days have no low at all: {flat}"
    )


def half_hour_zone() -> None:
    zone = zoneinfo.ZoneInfo("Asia/Kolkata")
    offset = datetime(2026, 11, 20, tzinfo=UTC).astimezone(zone).utcoffset().total_seconds()
    starts = hours(date(2026, 11, 10), 3)
    split = [
        t
        for t in starts
        if datetime.fromtimestamp(t, zone).date()
        != datetime.fromtimestamp(t + HOUR - 1, zone).date()
    ]
    first = datetime.fromtimestamp(split[0], zone)
    now = datetime(2026, 11, 20, tzinfo=UTC)
    odd_zones = sorted(
        name
        for name in zoneinfo.available_timezones()
        if now.astimezone(zoneinfo.ZoneInfo(name)).utcoffset() % timedelta(hours=1)
    )
    print(
        f"2. Kolkata (UTC{offset / HOUR:+.1f}): {len(split)} of {len(starts)} hourly buckets "
        f"hold parts of two local days, one every day: the bucket that starts at "
        f"{first:%H:%M} local time ends at 00:30 the next day. A daily total or minimum taken "
        f"from the hourly tier is therefore off by up to 30 minutes of data at each end. "
        f"{len(odd_zones)} zone names in this machine's database are not a whole number of "
        f"hours from UTC today"
    )


def main() -> None:
    daylight_saving()
    half_hour_zone()
    print(
        f"3. zoneinfo keys found here: {len(zoneinfo.available_timezones())}; the tzdata "
        f"package is installed: {importlib.util.find_spec('tzdata') is not None}. "
        "docs.python.org says Windows has no such database without that package"
    )


if __name__ == "__main__":
    main()
