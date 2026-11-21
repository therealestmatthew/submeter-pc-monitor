"""Probe: recompute every figure of the disk arithmetic in the brief, and check its units.

Reads only. Run from the repository root:

    .venv/bin/python docs/review/probes/c-storage/budget_arithmetic.py

1. The results table of docs/08-configuration.md, row by row, from the formulas printed above it.
2. The "Disk use after a year" table of docs/06-storage.md.
3. The volumes in docs/05-data-flow.md.
4. The store status sample in docs/03-cli-output.md: its total, its units and its expiry notes.
"""

from __future__ import annotations

import math
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from submeter.core.config import load_settings
from submeter.core.units import format_size, parse_size

DOCS = Path(__file__).resolve().parents[3]
GB, GIB, ROW = 1e9, 1024**3, 90


def seconds(text: str) -> float:
    number, unit = text.split()
    return float(number) / (1000 if unit == "ms" else 1)


def model(active: float, cold: float, processes: int) -> tuple[float, float, float]:
    """Overhead in percent, raw rows per 48 h and the share of short-lived CPU, as docs/08 says."""
    overhead = (1.5 + 0.012 * processes) / (active * 1000) * 100 + 0.2
    hot = max(10.0, 0.1 * processes)
    rows = hot * 172800 / active + (processes - hot) * 172800 / cold / 3 + 8 * 172800 / active
    return overhead, rows, (0.3 / active) * (1 - math.exp(-active / 0.3)) * 100


def configuration_table() -> None:
    budget = load_settings().settings.storage.disk_budget
    print(
        f'1. docs/08 results table. The setting "2GB" parses to {budget:,} bytes '
        f"({budget / GB:.3f} GB)"
    )
    text = (DOCS / "08-configuration.md").read_text(encoding="utf-8")
    cells = [r"(\d+ m?s)", r"(\d+ s)", r"(\d+)", r"([\d.]+)%", r"([\d.]+) M", r"([\d.]+) GB"]
    cells += [r"(\d+)%", r"(.*)"]
    pattern = re.compile(r"^\| " + r" \| ".join(cells) + r" \|$", re.MULTILINE)
    for a_text, c_text, p_text, overhead, rows_m, disk, capture, status in pattern.findall(text):
        got = model(seconds(a_text), seconds(c_text), int(p_text))
        size = got[1] * ROW
        same = (
            f"{got[0]:.1f}" == overhead
            and f"{got[1] / 1e6:.1f}" == rows_m
            and f"{size / GB:.2f}" == disk
            and f"{got[2]:.0f}" == capture
        )
        over = "over" if size > budget else "under"
        print(
            f"   {a_text:>6} {c_text:>4} {p_text:>4}: doc {overhead}% {rows_m} M {disk} GB "
            f"{capture}% | recomputed {got[0]:.1f}% {got[1] / 1e6:.1f} M {size / GB:.2f} GB "
            f"{got[2]:.0f}% {'match' if same else 'DIFFERS'} | {size / GIB:.2f} GiB, {over} the "
            f"parsed budget | doc status: {status}"
        )


def storage_table() -> None:
    rows = model(1.0, 10.0, 300)[1]
    raw_48, raw_72 = rows * ROW / GB, rows * 1.5 * ROW / GB
    minute_day = 9 * 1440 * 250
    hourly_year = 9 * 24 * 365 * 250
    print(
        f"2. docs/06 table. raw: {rows / 1e6:.2f} M rows x {ROW} B = {raw_48:.2f} GB per 48 h and "
        f"{raw_72:.2f} GB at 72 h (doc: 0.7 to 1.1). minute: 9 x 1,440 x 250 B = "
        f"{minute_day / 1e6:.2f} MB a day, {minute_day * 30 / GB:.2f} to "
        f"{minute_day * 37 / GB:.2f} GB for 30 to 37 days (doc: 0.1). hourly buckets alone: "
        f"{hourly_year / 1e6:.0f} MB a year (doc: history 0.1 GB a year with executables). "
        f"logs: 2 x 5 x 5 MB = {2 * 5 * 5 / 1000:.2f} GB (doc: 0.05). total with 0.1 history and "
        f"0.3 backups: {raw_48 + 0.1 + 0.1 + 0.3 + 0.05:.2f} to "
        f"{raw_72 + 0.1 + 0.1 + 0.3 + 0.05:.2f} GB (doc: about 1.6)"
    )


def data_flow_volumes() -> None:
    rows = model(1.0, 10.0, 300)[1]
    print(
        f"3. docs/05 volumes per day. workload rows: 8 x 86,400 = {8 * 86400 / 1e6:.2f} M (doc: "
        f"0.7 M). raw rows: {rows / 2 / 1e6:.2f} M with the workload rows, "
        f"{(rows / 2 - 8 * 86400) / 1e6:.2f} M without (doc: 3 to 4 M). minute rows: 9 x 1,440 = "
        f"{9 * 1440:,} (doc: 13 K). hourly rows: 9 x 24 = {9 * 24} buckets, leaving about "
        f"{2000 - 9 * 24:,} of the doc's 2 K for executables, {(2000 - 216) / 8 / 24:.1f} per "
        f"workload and hour"
    )


def status_sample() -> None:
    text = (DOCS / "03-cli-output.md").read_text(encoding="utf-8")
    block = text[text.index("$ submeter store status") : text.index("Epoch   14")]
    sizes = [int(number) for number in re.findall(r"\s(\d+) MB", block)]
    total = sum(sizes)
    now = datetime(2026, 11, 20, 9, tzinfo=UTC)
    raw_end = datetime(2026, 11, 19, tzinfo=UTC) + timedelta(hours=48)
    week_end = datetime.combine(
        date.fromisocalendar(2026, 43, 1) + timedelta(days=7), datetime.min.time(), UTC
    ) + timedelta(days=30)
    print(
        f"4. docs/03 sample. {len(sizes)} sizes add up to {total} MB. Shown: 1.19 GB of 2 GB. "
        f"Decimal: {total / 1000:.2f} GB. The baseline's format_size prints "
        f"{format_size(total * 1024**2)!r} for that many MiB and {format_size(total * 1e6)!r} "
        f"for that many MB, and parse_size('2GB') is {parse_size('2GB') / GB:.3f} decimal GB. "
        f"If the sample was taken at 09:00 UTC on the 20th: raw 11-18 expires in "
        f"{(raw_end - now).total_seconds() / 3600:.0f} h (shown: 15 h), minute W43 in "
        f"{(week_end - now).total_seconds() / 86400:.1f} d (shown: 5 d), and today's raw file "
        f"is {212 / 371:.0%} of yesterday's size {9 / 24:.0%} of the way through the day"
    )


if __name__ == "__main__":
    configuration_table()
    storage_table()
    data_flow_volumes()
    status_sample()
