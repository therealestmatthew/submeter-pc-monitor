"""Verify G4: the wall clock stepped back or forward while the collector runs.

Reads and measures only. Raw files go to a temporary folder. Clocks are synthetic, but each
tick's wall time carries a sub-millisecond offset, as time.time() does, so that two ticks never
share a timestamp by construction (the lead's probe used whole seconds).

    uv run python docs/review/probes/verify-1/clock_step.py

One process uses one core throughout, so true CPU equals the monotonic seconds that passed.
1. Back 30 s at noon. 2. Back 50 s just after UTC midnight. 3. Forward 5 s (an NTP step).
"""

from __future__ import annotations

import sqlite3
import tempfile
from collections.abc import Callable
from pathlib import Path

from _helpers import DAY0, proc, snap

from submeter.attribution.rules import Attributor, RuleSet, aggregate
from submeter.collector.sampler import Sampler
from submeter.store.files import FileMap
from submeter.store.raw import RawFile, RawStore
from submeter.store.rollup import roll_up


def jitter(k: int) -> float:
    return ((k * 7919) % 1000) / 1_000_000 + 0.000123


def run(folder: Path, name: str, wall: Callable[[int], float], ticks: int = 120) -> None:
    files = FileMap.discover({"SUBMETER_HOME": str(folder / name)})
    store, sampler, attributor = RawStore(files), Sampler(), Attributor(RuleSet())
    order: list[str] = []
    original = RawFile.write

    def recording(self: RawFile, *args: object, keyframe: bool = False) -> int:
        if not order or order[-1] != self.path.name:
            order.append(self.path.name)
        return original(self, *args, keyframe=keyframe)  # type: ignore[arg-type]

    RawFile.write = recording  # type: ignore[method-assign]
    credited = gaps = 0.0
    backwards = 0
    last_at = None
    try:
        for k in range(ticks + 1):
            at = wall(k) + jitter(k)
            batch = sampler.ingest(snap(at, [proc(1, float(k))], mono=float(k)))
            if batch is None:
                last_at = at
                continue
            backwards += batch.taken_at < (last_at or 0)
            last_at = batch.taken_at
            credited += sum(p.cpu_s for p in batch.processes)
            gaps += batch.gap
            store.write(batch, aggregate(batch, attributor.assign(batch.processes)), {})
        store.close()
    finally:
        RawFile.write = original  # type: ignore[method-assign]
    stored = rows = 0.0
    samples = []
    for path in sorted(files.raw_dir.glob("*.db")):
        db = sqlite3.connect(path)
        n, cpu = db.execute("SELECT COUNT(*), COALESCE(SUM(cpu_s), 0) FROM workload_raw").fetchone()
        db.close()
        rows += n
        stored += cpu
        raw = RawFile(path)
        samples += raw.workload_samples(0.0, 1e12)
        raw.close()
    fullest = max(roll_up(samples, width_s=60, logical_cores=4), key=lambda b: b.covered_s)
    print(
        f"   {name}: true CPU {ticks} s; sampler credited {credited:.0f}; stored rows {rows:.0f}, "
        f"stored CPU {stored:.0f}; gap batches {gaps:.0f}; batches stamped earlier than the one "
        f"before {backwards}; fullest minute covered_s {fullest.covered_s:.0f} of 60 with cpu_s "
        f"{fullest.cpu_s:.0f}; files written in order {order}"
    )


if __name__ == "__main__":
    noon, midnight = DAY0 + 12 * 3600, DAY0 + 86400
    with tempfile.TemporaryDirectory() as name:
        folder = Path(name)
        print("one process at 1.00 cores, 120 one-second ticks, one wall-clock step at tick 60")
        run(folder, "back-30s", lambda k: noon + k - (30 if k >= 60 else 0))
        run(folder, "back-50s-midnight", lambda k: midnight - 40 + k - (50 if k >= 60 else 0))
        run(folder, "forward-5s", lambda k: noon + k + (5 if k >= 60 else 0))
