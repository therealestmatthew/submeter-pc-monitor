"""Probe: does a bucket filled by a time-window query get exactly its own samples?

Reads and measures only. Writes raw files in a temporary folder.

    .venv/bin/python docs/review/probes/c-storage/bucket_membership.py

RawFile.workload_samples selects by the END of a sample (ts > start AND ts <= end).
roll_up assigns by the MIDDLE of a sample (taken_at - interval_s / 2). The baseline test uses
whole-second timestamps, where the two agree. A real collector ticks at a fraction of a second.
One hour of samples, each worth 1 CPU-second per second, is written and then rolled up minute by
minute in three ways a server could plausibly use. The raw sum is the reference; the phase 1 gate
allows 0.1%.
"""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

from _synth import DAY0, clock, empty_batch, workload

from submeter.core.models import Bucket
from submeter.store.files import FileMap
from submeter.store.raw import RawFile, RawStore
from submeter.store.rollup import SeriesAccumulator, roll_up

HOUR = DAY0 + 9 * 3600


def fill(raw: RawFile, interval: float, phase: float) -> float:
    """Write one hour of samples ending at HOUR + phase + k * interval. Returns the raw sum."""
    total, at = 0.0, HOUR + phase
    while at <= HOUR + 3600:
        raw.write(empty_batch(at, interval), [workload(at, interval, interval=interval)], {})
        total += interval
        at += interval
    return total


def by_window(raw: RawFile, keep_all: bool) -> dict[float, Bucket]:
    """Query each minute's window, roll it up, and store what comes back, as an upsert would."""
    stored: dict[float, Bucket] = {}
    for minute in range(60):
        start = HOUR + 60 * minute
        for bucket in roll_up(raw.workload_samples(start, start + 60), width_s=60, logical_cores=4):
            if keep_all or bucket.start == start:
                stored[bucket.start] = bucket
    return stored


def by_accumulator(raw: RawFile) -> dict[float, Bucket]:
    """Query each minute's window and put every row into that minute's accumulator."""
    stored: dict[float, Bucket] = {}
    for minute in range(60):
        start = HOUR + 60 * minute
        one = SeriesAccumulator(series="agents", start=start, width_s=60, logical_cores=4)
        for sample in raw.workload_samples(start, start + 60):
            one.add(sample)
        bucket = one.close()
        if bucket is not None:
            stored[start] = bucket
    return stored


def report(label: str, buckets: dict[float, Bucket], raw_sum: float) -> None:
    inside = [b for start, b in buckets.items() if HOUR <= start < HOUR + 3600]
    cpu = sum(bucket.cpu_s for bucket in inside)
    covered = sorted({round(bucket.covered_s, 2) for bucket in inside})
    print(
        f"  {label:<44} cpu {cpu:7.1f} of {raw_sum:.1f} ({cpu / raw_sum - 1:+.2%}), "
        f"covered_s per minute {covered[0]:g} to {covered[-1]:g}"
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as folder:
        for interval, phase in ((1.0, 0.37), (1.0, 0.63), (5.0, 1.2), (10.0, 3.3)):
            raw = RawFile(Path(folder) / f"i{interval:g}-p{phase:g}.db")
            raw_sum = fill(raw, interval, phase)
            print(f"interval {interval:g} s, first tick {phase:g} s after the minute:")
            report("A window query, roll_up, keep the asked bucket", by_window(raw, False), raw_sum)
            report("B window query, roll_up, upsert every bucket", by_window(raw, True), raw_sum)
            report("C window query, one accumulator per bucket", by_accumulator(raw), raw_sum)
            if (interval, phase) == (1.0, 0.37):
                window = raw.workload_samples(HOUR + 60, HOUR + 120)
                for bucket in roll_up(window, width_s=60, logical_cores=4):
                    print(
                        f"    the 09:01 window alone gives a bucket at {clock(bucket.start)} "
                        f"with {bucket.samples} samples, covered_s {bucket.covered_s:g}"
                    )
            raw.close()

        files = FileMap.discover({"SUBMETER_HOME": folder})
        store, midnight = RawStore(files), DAY0 + 86400
        for at in (midnight - 0.63, midnight, midnight + 0.37):
            store.write(empty_batch(at), [workload(at, 1.0)], {})
        store.close()
        print("three samples around midnight UTC, written through RawStore:")
        for day in (date(2026, 11, 20), date(2026, 11, 21)):
            raw = RawFile(files.raw_file(day))
            for sample in raw.workload_samples(0, 2 * midnight):
                bucket = roll_up([sample], width_s=60, logical_cores=4)[0]
                in_window = midnight - 60 < sample.taken_at <= midnight
                print(
                    f"  file {day}: sample ending {clock(sample.taken_at)} -> roll_up bucket "
                    f"{clock(bucket.start)}; inside the 23:59 window query: {in_window}"
                )
            raw.close()


if __name__ == "__main__":
    main()
