"""Verifier probe for S1: do workload_samples and roll_up agree on which bucket a sample is in.

Reads and measures only. Writes raw files in a temporary folder. Nothing is timed.

    uv run python docs/review/probes/verify-6/v6_membership.py

Independent of the lead's probe. One hour at 1 CPU-second per second, one workload, written
through RawFile with a tick phase that is not a whole second, plus two minutes either side. The
raw sum of the hour is given both ways: by sample end, as a SQL sum over the raw file's ts would
give it, and by sample middle, as roll_up assigns. Each minute is then rolled up the
way docs/17-build-prompt.md:269 directs ("built on the existing rollup functions"):
  1 query the minute's window (start, start+60] and keep the bucket at start;
  2 the same, with the window widened by one interval at each end (a builder's possible fix);
  3 one roll_up over the whole hour at once.
It also checks which UTC-day file a sample that ends exactly at midnight is written to.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from submeter.core.models import SampleBatch, WorkloadSample
from submeter.store.files import FileMap, utc_day
from submeter.store.raw import RawFile, RawStore
from submeter.store.rollup import roll_up

DAY0 = 1_795_132_800.0  # 2026-11-20 00:00:00 UTC
HOUR = DAY0 + 10 * 3600


def batch(at: float, interval: float) -> SampleBatch:
    return SampleBatch(
        taken_at=at,
        interval_s=interval,
        gap=False,
        processes=(),
        exited=(),
        logical_cores=8,
        cpu_busy_s=0.0,
        memory_available_bytes=1 << 33,
    )


def sample(at: float, interval: float) -> WorkloadSample:
    return WorkloadSample(
        taken_at=at,
        interval_s=interval,
        workload="w",
        source="polled",
        cpu_s=interval,
        memory_bytes=1 << 27,
        io_read_bytes=0,
        io_write_bytes=0,
        processes=1,
        started=0,
    )


def run(folder: Path, interval: float, phase: float) -> None:
    raw = RawFile(folder / f"{interval:g}-{phase:g}.db")
    at = HOUR - 120 + phase
    while at <= HOUR + 3720:
        raw.write(batch(at, interval), [sample(at, interval)], {})
        at += interval
    rows = raw.workload_samples(HOUR - 200, HOUR + 3800)
    total = sum(s.cpu_s for s in rows if HOUR < s.taken_at <= HOUR + 3600)
    by_middle = sum(s.cpu_s for s in rows if HOUR <= s.taken_at - s.interval_s / 2 < HOUR + 3600)
    asked = widened = 0.0
    for minute in range(60):
        start = HOUR + 60 * minute
        for b in roll_up(raw.workload_samples(start, start + 60), width_s=60, logical_cores=8):
            asked += b.cpu_s if b.start == start else 0.0
        wide = raw.workload_samples(start - interval, start + 60 + interval)
        for b in roll_up(wide, width_s=60, logical_cores=8):
            widened += b.cpu_s if b.start == start else 0.0
    whole = sum(
        b.cpu_s
        for b in roll_up(raw.workload_samples(HOUR - 60, HOUR + 3660), width_s=60, logical_cores=8)
        if HOUR <= b.start < HOUR + 3600
    )
    print(
        f"interval {interval:g} s, phase {phase:g} s: raw sum by end {total:.0f}, "
        f"by middle {by_middle:.0f}; "
        f"1 per-minute window {asked:.0f} ({asked / total - 1:+.2%}); "
        f"2 widened window {widened:.0f} ({widened / total - 1:+.2%}); "
        f"3 whole hour {whole:.0f} ({whole / total - 1:+.2%})"
    )
    raw.close()


def midnight(folder: Path) -> None:
    files = FileMap.discover({"SUBMETER_HOME": str(folder / "home")})
    store, edge = RawStore(files), DAY0 + 86400
    for at in (edge - 1.0, edge, edge + 0.2):
        store.write(batch(at, 1.0), [sample(at, 1.0)], {})
    store.close()
    for at in (edge, edge + 0.2):
        end_bucket = "23:59" if edge - 60 < at <= edge else "00:00"
        mid_bucket = "23:59" if at - 0.5 < edge else "00:00"
        print(
            f"sample ending {at - edge:+.1f} s from midnight is in file {utc_day(at)}; "
            f"end rule puts it in {end_bucket}, roll_up's middle rule in {mid_bucket} "
            f"(of {utc_day(edge - 1)})"
        )


def main() -> None:
    with tempfile.TemporaryDirectory() as name:
        folder = Path(name)
        for interval, phase in ((1.0, 0.2), (1.0, 0.7), (5.0, 2.0), (2.0, 0.5)):
            run(folder, interval, phase)
        midnight(folder)


if __name__ == "__main__":
    main()
