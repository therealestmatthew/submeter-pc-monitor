"""Coverage check for working-notes lead 38, and the part of lead 29 that R100 leaves.

Logic only. Nothing is timed and no process is read. Raw day files are empty
placeholders in a temporary folder, so only the baseline's own expiry rule
(FileMap.expired_raw) and tier rule (choose_tier) run; the rest is arithmetic
on the brief's stated design.

    uv run python docs/review/probes/coverage/session_retention.py

1. The brief's promises about session totals, read from the documents.
2. Which raw day files of a 72 h session expired_raw() lists when the session
   ends, at the default 48 h and at the 24 h floor of the disk budget.
3. What a summary built at the end still holds, per tier, for a workload
   at a steady 2.0 cores.
4. Top executables: the session's true top executable against the hourly
   top-ten lists that exe_1h keeps (docs/06:75). Constructed case.
5. choose_tier() once the budget has cut raw toward its 24 h floor: a
   20-minute window 40 h back is still sent to raw.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from submeter.store.files import FileMap
from submeter.store.query import choose_tier

ROOT = Path(__file__).resolve().parents[4]
DOCS = ROOT / "docs"
HOUR = 3600.0
CORES = 2.0


def quote(name: str, needle: str) -> None:
    for number, line in enumerate((DOCS / name).read_text(encoding="utf-8").splitlines(), 1):
        if needle in line:
            print(f"  docs/{name}:{number}: {line.strip()[:220]}")
            return
    print(f"  docs/{name}: '{needle}' NOT FOUND")


def ts(text: str) -> float:
    return datetime.fromisoformat(text).replace(tzinfo=UTC).timestamp()


def iso(stamp: float) -> str:
    return datetime.fromtimestamp(stamp, UTC).strftime("%Y-%m-%d %H:%M:%S")


def part1() -> None:
    print("1. What the brief promises")
    quote("06-storage.md", "summarised when it ends")
    quote("17-build-prompt.md", "exact totals per workload")
    quote("15-phases-and-decisions.md", "before and after its raw data is deleted")
    quote("17-build-prompt.md", "never going below 24 hours")
    quote("08-configuration.md", "override the interval for its own duration")
    quote("06-storage.md", "top ten executables")
    quote("08-configuration.md", "raw retention about 13 h")
    quote("08-configuration.md", "raw retention about 38 h")
    print()


def part2_and_3(start: float, end: float) -> None:
    print("2. Raw day files a 72 h session has lost by the time it ends")
    print(f"  session: {iso(start)} to {iso(end)} UTC ({(end - start) / HOUR:.1f} h)")
    truth = (end - start) * CORES
    with tempfile.TemporaryDirectory() as home:
        files = FileMap.discover(env={"SUBMETER_HOME": home})
        files.raw_dir.mkdir(parents=True)
        day = datetime.fromtimestamp(start, UTC).date()
        while day <= datetime.fromtimestamp(end, UTC).date():
            files.raw_file(day).touch()
            day += timedelta(days=1)
        rows = []
        for label, retention in (("48h (default)", 48 * HOUR), ("24h (budget floor)", 24 * HOUR)):
            expired = files.expired_raw(end, retention)
            names = [p.name for p in expired]
            kept_from = start
            if expired:
                last = date.fromisoformat(expired[-1].stem) + timedelta(days=1)
                kept_from = max(start, datetime.combine(last, datetime.min.time(), UTC).timestamp())
            print(f"  retention {label}: expired_raw at session end -> {names}")
            print(
                f"    raw still on disk covers {iso(kept_from)} to {iso(end)}: "
                f"{(end - kept_from) / HOUR:.1f} of {(end - start) / HOUR:.1f} h"
            )
            rows.append((f"raw at end, retention {label}", (end - kept_from) * CORES))
    print()
    print(f"3. Session CPU from each tier, workload at a steady {CORES} cores")
    print(f"  truth: {truth:,.0f} CPU-s")
    for label, value in rows:
        print(f"  {label:<38} {value:>10,.0f} CPU-s  ({value / truth:6.1%} of truth)")
    tiers = (("minute buckets", 60.0), ("hourly buckets (minute tier cut, R147)", HOUR))
    for label, width in tiers:
        edge = start - (start // width) * width
        print(
            f"  {label:<38} {truth + edge * CORES:>10,.0f} CPU-s if the edge bucket is "
            f"kept, {truth - (width - edge) * CORES:,.0f} if dropped "
            f"(start edge {edge:.0f} s into its bucket)"
        )
    print()


def part4() -> None:
    print("4. Session top executable from hourly top-ten lists (constructed case)")
    hours = 72
    per_hour: list[dict[str, float]] = []
    for hour in range(hours):
        active = range(1, 11) if hour % 2 == 0 else range(11, 21)
        cpu = {f"burst{i:02d}": (600.0 if i in active else 0.0) for i in range(1, 21)}
        cpu["steady"] = 400.0
        per_hour.append(cpu)
    totals: dict[str, float] = {}
    kept: dict[str, float] = {}
    steady_listed = 0
    for cpu in per_hour:
        for name, value in cpu.items():
            totals[name] = totals.get(name, 0.0) + value
        top_ten = sorted(cpu.items(), key=lambda item: -item[1])[:10]
        steady_listed += any(name == "steady" for name, _ in top_ten)
        for name, value in top_ten:
            kept[name] = kept.get(name, 0.0) + value
    true_top = max(totals, key=lambda name: totals[name])
    kept_top = max(kept, key=lambda name: kept[name])
    print("  20 bursty executables at 600 CPU-s in alternate hours; one steady at 400 every hour")
    print(f"  true session top: {true_top} with {totals[true_top]:,.0f} CPU-s")
    print(f"  'steady' appears in {steady_listed} of {hours} hourly top-ten lists")
    print(f"  top from the exe_1h lists: {kept_top} with {kept[kept_top]:,.0f} CPU-s")
    print()


def part5() -> None:
    print("5. choose_tier() reads retention from settings, not from the files left on disk")
    now = ts("2026-11-19T12:00:00")
    start = now - 40 * HOUR
    choice = choose_tier(
        start=start,
        end=start + 20 * 60,
        now=now,
        raw_retention_s=48 * HOUR,
        minute_retention_s=30 * 24 * HOUR,
    )
    print(f"  20-minute window starting {iso(start)} (40 h back), retention.raw 48h")
    print(f"  choose_tier -> tier={choice.tier.value} step={choice.step_s:g}s")
    print(f"  reason: '{choice.reason}'")
    with tempfile.TemporaryDirectory() as home:
        files = FileMap.discover(env={"SUBMETER_HOME": home})
        files.raw_dir.mkdir(parents=True)
        for offset in range(3):
            files.raw_file(date(2026, 11, 17) + timedelta(days=offset)).touch()
        floor = files.expired_raw(now, 24 * HOUR)
        print(f"  files the budget may delete at its 24 h floor: {[p.name for p in floor]}")
        holding = datetime.fromtimestamp(start, UTC).date().isoformat() + ".db"
        gone = holding in [p.name for p in floor]
        print(f"  the window lies in {holding}; deleted under the floor: {gone}")


def main() -> None:
    part1()
    start = ts("2026-11-16T06:20:30")
    part2_and_3(start, start + 72 * HOUR)
    part4()
    part5()


if __name__ == "__main__":
    main()
