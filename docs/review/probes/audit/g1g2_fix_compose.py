"""Audit G1 and G2: do the two proposed fixes compose in store/rollup.py?

Reads only. Clocks and samples are synthetic; nothing is timed and nothing is written.

    uv run python docs/review/probes/audit/g1g2_fix_compose.py

G1's fix keeps the CPU delta of a gap batch (the counters are cumulative, so it is exact).
G2's fix marks the sample as a gap and, for it, adds cpu_s, I/O and started to the sums but
nothing to covered_s, samples, active_s, the memory weight or the histograms.

The unchanged roll_up() places a sample in the bucket that holds its midpoint,
taken_at - interval_s / 2. For a gap sample that midpoint lies inside the suspend, where no
other sample exists. This probe applies G2's add() rule literally in a subclass and shows
what the unchanged close() then does with that bucket, under the two ways a builder could
read "the memory weight": leave the memory gauges alone, or set them.

Part 2: G2 also proposes "Reject a non-gap sample whose interval_s exceeds width_s", while
G1 proposes splitting long samples across bucket edges. It loads idle_interval = 60s (and
60s x on_battery_multiplier 10), which load_settings accepts, and compares a tick that
arrives 50 ms late with the 60 s minute width.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))

from submeter.core.config import load_settings
from submeter.core.models import AccountingSource, WorkloadSample
from submeter.store.rollup import SeriesAccumulator, bucket_start

DAY0 = 1_795_132_800.0


class GapAware(SeriesAccumulator):
    """G2's proposed add(): a gap sample adds only its sums."""

    def __init__(self, *, set_memory_gauges: bool, **kw: object) -> None:
        super().__init__(**kw)  # type: ignore[arg-type]
        self._set_gauges = set_memory_gauges

    def add_gap(self, sample: WorkloadSample) -> None:
        self._cpu_s += sample.cpu_s
        self._read += sample.io_read_bytes
        self._write += sample.io_write_bytes
        self._started += sample.started
        if self._set_gauges:
            self._memory_min = sample.memory_bytes
            self._memory_max = self._memory_last = sample.memory_bytes


def main() -> None:
    # Resume after a one-hour suspend: the gap batch keeps the 4 CPU-s used in the
    # seconds around the suspend (G1's fix).
    gap = WorkloadSample(
        taken_at=DAY0 + 4201.0,
        interval_s=3601.0,
        workload="agent",
        source=AccountingSource.POLLED,
        cpu_s=4.0,
        memory_bytes=50 * 1024**2,
        io_read_bytes=0,
        io_write_bytes=0,
        processes=1,
        started=0,
    )
    start = bucket_start(gap.taken_at - gap.interval_s / 2, 60.0)
    resume_bucket = bucket_start(gap.taken_at, 60.0)
    print(
        f"gap sample: taken_at +{gap.taken_at - DAY0:.0f} s, interval {gap.interval_s:.0f} s, "
        f"cpu_s {gap.cpu_s}"
    )
    print(
        f"roll_up's midpoint rule puts it in the minute bucket at +{start - DAY0:.0f} s "
        f"(the resume is in the bucket at +{resume_bucket - DAY0:.0f} s)"
    )
    for set_gauges in (False, True):
        acc = GapAware(
            set_memory_gauges=set_gauges,
            series="agent",
            start=start,
            width_s=60.0,
            logical_cores=4,
        )
        acc.add_gap(gap)
        label = "memory gauges set" if set_gauges else "memory gauges left alone"
        try:
            bucket = acc.close()
        except ZeroDivisionError as error:
            print(f"  {label:<26} close() raised ZeroDivisionError: {error}")
            continue
        if bucket is None:
            print(f"  {label:<26} close() returned None: the {gap.cpu_s} CPU-s G1 kept are lost")
        else:
            print(f"  {label:<26} bucket cpu_s {bucket.cpu_s}, covered_s {bucket.covered_s}")

    print("part 2: G2's reject rule against intervals the settings accept")
    for overrides, factor in (
        ({"sampling": {"idle_interval": "60s"}}, 1),
        ({"sampling": {"idle_interval": "60s", "on_battery_multiplier": 10}}, 10),
    ):
        sampling = load_settings(overrides=overrides).settings.sampling
        interval = sampling.idle_interval * factor + 0.05
        print(
            f"  idle_interval {sampling.idle_interval:.0f} s x {factor}: a tick 50 ms late covers "
            f"{interval:.2f} s > minute width 60 s: {interval > 60.0} (rejected under G2's rule)"
        )


if __name__ == "__main__":
    main()
