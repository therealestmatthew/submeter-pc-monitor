"""Probe: what the retention rules in store/files.py keep and offer for deletion, day by day.

Reads and measures only. Creates empty files in a temporary folder. Nothing is timed.

    .venv/bin/python docs/review/probes/c-storage/retention_calendar.py

1. ISO-week file names at year boundaries: every day from 2024 to 2035 maps to a week file whose
   Monday-to-Sunday span holds that day, and the names sort in time order.
2. How many raw and minute files exist, and how many hours and days they span, when retention
   runs every hour for 70 days (48 hours and 30 days, the defaults).
3. The 24-hour floor of the disk budget against whole-day files, beside the hours that
   docs/08-configuration.md prints for the same cases.
4. The server is away for five days while the collector keeps writing. What expired_raw hands
   back when the server returns, and whether anything in FileMap knows what was rolled up.
"""

from __future__ import annotations

import inspect
import tempfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from submeter.store.files import FileMap, utc_day

HOUR, DAY = 3600.0, 86400.0
RAW_KEEP, MINUTE_KEEP = 48 * HOUR, 30 * DAY


def stamp(day: date, hour: float = 0.0) -> float:
    return datetime.combine(day, datetime.min.time(), UTC).timestamp() + hour * HOUR


def week_names(files: FileMap) -> None:
    day, wrong, names, long_years = date(2024, 1, 1), 0, [], set()
    while day <= date(2035, 12, 31):
        name = files.minute_file(day).name
        year, week = name.removesuffix(".db").split("-W")
        monday = date.fromisocalendar(int(year), int(week), 1)
        wrong += not monday <= day <= monday + timedelta(days=6)
        names.append((monday, name))
        if week == "53":
            long_years.add(year)
        day += timedelta(days=1)
    in_order = sorted(set(names)) == sorted(set(names), key=lambda pair: pair[1])
    print(
        f"1. {len(names)} days checked: {wrong} map to a week file that does not hold them; "
        f"names sort in time order: {in_order}; years with a week 53: {sorted(long_years)}"
    )
    for text in ("2026-12-27", "2026-12-28", "2027-01-03", "2027-01-04", "2024-12-30"):
        print(f"   {text} -> {files.minute_file(date.fromisoformat(text)).name}")


def hourly_retention(files: FileMap) -> None:
    start, raw_counts, raw_hours, minute_counts, minute_days = date(2026, 9, 1), [], [], [], []
    for step in range(70 * 24):
        now = stamp(start) + step * HOUR + 1.0
        files.raw_file(utc_day(now)).touch()
        files.minute_file(utc_day(now)).touch()
        for path in files.expired_raw(now, RAW_KEEP) + files.expired_minute(now, MINUTE_KEEP):
            path.unlink()
        if step < 40 * 24:  # let both tiers fill before counting
            continue
        raw = sorted(date.fromisoformat(p.stem) for p in files.raw_dir.glob("*.db"))
        weeks = sorted(p.stem for p in files.minute_dir.glob("*.db"))
        year, week = weeks[0].split("-W")
        raw_counts.append(len(raw))
        raw_hours.append((now - stamp(raw[0])) / HOUR)
        minute_counts.append(len(weeks))
        minute_days.append((now - stamp(date.fromisocalendar(int(year), int(week), 1))) / DAY)
    print(
        f"2. raw: {min(raw_counts)} to {max(raw_counts)} files on disk, spanning "
        f"{min(raw_hours):.0f} to {max(raw_hours):.0f} hours (setting: 48). minute: "
        f"{min(minute_counts)} to {max(minute_counts)} files, spanning {min(minute_days):.0f} "
        f"to {max(minute_days):.0f} days (setting: 30)"
    )


def budget_floor() -> None:
    print("3. raw hours left after the budget deletes the oldest whole-day files, by time of day:")
    for hour in (0.01, 9.0, 23.99):
        three, two, one = hour + 48, hour + 24, hour
        print(
            f"   at {hour:5.2f} h UTC: 3 files hold {three:.1f} h; delete one -> {two:.1f} h; "
            f"delete two -> {one:.1f} h, which is under the 24-hour floor"
        )
    for disk_gb in (2.50, 2.15, 7.65):
        print(
            f"   docs/08 for {disk_gb:.2f} GB of raw data: 'raw retention about "
            f"{round(96 / disk_gb)} h'. Whole-day files can give 48 to 72 h or 24 to 48 h, "
            f"and the floor forbids less"
        )


def server_away(files: FileMap) -> None:
    first = date(2026, 11, 10)
    for offset in range(
        6
    ):  # the collector writes the 10th to the 15th; the server died on the 10th
        files.raw_file(first + timedelta(days=offset)).touch()
    back = stamp(first + timedelta(days=5), 9.0)
    offered = [path.name for path in files.expired_raw(back, RAW_KEEP)]
    knows = [name for name, _ in inspect.getmembers(FileMap) if "roll" in name or "final" in name]
    print(
        f"4. server back at 09:00 on the 15th after five days away: expired_raw offers "
        f"{offered} for deletion. FileMap members that record what has been rolled up: "
        f"{knows or 'none'}. Raw files on disk while it was away: 6, with nothing deleting them"
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as name:
        week_names(FileMap.discover({"SUBMETER_HOME": str(Path(name) / "a")}))
        files = FileMap.discover({"SUBMETER_HOME": str(Path(name) / "b")})
        files.ensure()
        hourly_retention(files)
        budget_floor()
        files = FileMap.discover({"SUBMETER_HOME": str(Path(name) / "c")})
        files.ensure()
        server_away(files)


if __name__ == "__main__":
    main()
