"""Probe: a wall clock that is stepped forwards or backwards while the collector runs.

Reads and measures only. Writes raw files in a temporary folder. Clocks are synthetic.

    .venv/bin/python docs/review/probes/c-storage/clock_steps.py

One process uses one core throughout, so true CPU equals the seconds that really passed on the
monotonic clock. Each scenario drives the baseline's Sampler and RawStore with a wall clock that
is stepped once, as a time service or a person does, and compares what the raw files then hold
with the truth. RawFile.write is wrapped only to note which file each batch went to and whether
a keyframe was asked for. The last part looks at a process born just after a step back.
"""

from __future__ import annotations

import itertools
import sqlite3
import tempfile
from collections.abc import Callable
from pathlib import Path

from _synth import DAY0, clock, pipeline, proc, snap

from submeter.collector.sampler import Sampler
from submeter.store.files import FileMap
from submeter.store.raw import RawFile, RawStore

Wall = Callable[[int], float]
Calls = list[tuple[str, bool]]


def run(folder: Path, name: str, ticks: int, wall: Wall) -> tuple[FileMap, Calls]:
    """Feed one-second ticks through Sampler and RawStore. Returns (file, keyframe) per batch."""
    files = FileMap.discover({"SUBMETER_HOME": str(folder / name)})
    store, calls, original = RawStore(files), [], RawFile.write

    def recording(self: RawFile, *args: object, keyframe: bool = False) -> int:
        calls.append((self.path.name, keyframe))
        return original(self, *args, keyframe=keyframe)  # type: ignore[arg-type]

    RawFile.write = recording  # type: ignore[method-assign]
    try:
        shots = (snap(wall(k), [proc(1, float(k))], mono=float(k)) for k in range(ticks + 1))
        for batch, workloads, names in pipeline(shots):
            store.write(batch, workloads, names)
        store.close()
    finally:
        RawFile.write = original  # type: ignore[method-assign]
    return files, calls


def show(label: str, files: FileMap, calls: Calls) -> None:
    print(f"{label}: {len(calls)} batches written, true CPU {len(calls)} s")
    for path in sorted(files.raw_dir.glob("*.db")):
        db = sqlite3.connect(path)
        rows, cpu, covered = db.execute(
            "SELECT COUNT(*), COALESCE(SUM(cpu_s), 0), COALESCE(SUM(interval_s), 0)"
            " FROM workload_raw"
        ).fetchone()
        gaps = db.execute("SELECT COUNT(*) FROM gap").fetchone()[0]
        db.close()
        print(
            f"  {path.name}: {rows} workload rows, CPU {cpu:.0f} s, SUM(interval_s) "
            f"{covered:.0f} s, gap rows {gaps}"
        )


def main() -> None:
    noon, midnight = DAY0 + 12 * 3600, DAY0 + 86400
    with tempfile.TemporaryDirectory() as name:
        folder = Path(name)

        # 1. forwards by an hour at tick 60, with no suspend: the machine never stopped
        files, calls = run(folder, "forward", 120, lambda k: noon + k + (3600 if k >= 60 else 0))
        show("1. stepped forwards 3600 s", files, calls)

        # 2. backwards by 30 s at tick 60, ticks on whole seconds
        files, calls = run(folder, "back", 120, lambda k: noon + k - (30 if k >= 60 else 0))
        show("2. stepped backwards 30 s, whole-second ticks", files, calls)

        # 2b. the same step with ticks off the whole second, so no two rows share a timestamp
        files, calls = run(folder, "frac", 120, lambda k: noon + k - (30.25 if k >= 60 else 0))
        show("2b. stepped backwards 30.25 s", files, calls)
        db = sqlite3.connect(next(iter(files.raw_dir.glob("*.db"))))
        covered, cpu = db.execute(
            "SELECT SUM(interval_s), SUM(cpu_s) FROM workload_raw WHERE ts > ? AND ts <= ?",
            (noon, noon + 60),
        ).fetchone()
        events = db.execute("SELECT COUNT(*) FROM event").fetchone()[0]
        db.close()
        print(
            f"  the minute {clock(noon)} holds {covered:.0f} covered seconds and {cpu:.0f} CPU-s; "
            f"event rows that mark the step: {events}"
        )

        # 3. backwards across UTC midnight: 20 s into the new day, then back to 30 s before it
        files, calls = run(
            folder, "midnight", 120, lambda k: midnight - 40 + k - (50 if k >= 60 else 0)
        )
        show("3. stepped backwards 50 s across UTC midnight", files, calls)
        runs = itertools.groupby(call[0] for call in calls)
        order = [f"{key} x{len(list(group))}" for key, group in runs]
        print(f"  files written, in order: {', '.join(order)}")

        # 4. backwards by an hour at tick 900: when is the next keyframe written?
        _, calls = run(folder, "hour", 5400, lambda k: noon + k - (3600 if k >= 900 else 0))
        due = [tick for tick, (_, keyframe) in enumerate(calls, start=1) if keyframe]
        waits = [later - earlier for earlier, later in itertools.pairwise(due)]
        print(
            f"4. stepped backwards 3600 s at tick 900, keyframes due every 600 s: keyframes at "
            f"ticks {due}; the longest wait between two is {max(waits)} s"
        )

    # 5. a process born in the first interval after a step back of an hour
    sampler = Sampler()
    sampler.ingest(snap(noon, [proc(1, 0.0)], mono=0.0))
    born = noon - 3600 + 0.4
    batch = sampler.ingest(
        snap(noon - 3600 + 1, [proc(1, 1.0), proc(2, 0.5, started=born)], mono=1.0)
    )
    assert batch is not None
    child = next(sample for sample in batch.processes if sample.key.pid == 2)
    print(
        f"5. a process born 0.6 s before the first sample after a step back used 0.5 CPU-s; "
        f"the sampler credits it {child.cpu_s:.1f} s (gap flag {batch.gap})"
    )


if __name__ == "__main__":
    main()
