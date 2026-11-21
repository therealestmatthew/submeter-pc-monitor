"""Verifier probe for S7 and S6: what reading a raw file through the baseline does to the file.

Reads and measures only. Writes raw files in a temporary folder. Nothing is timed, but one step
waits for SQLite's default 5 s busy timeout.

    uv run python docs/review/probes/verify-6/v6_read_path.py

1. RawFile opened on a day that has no file: is a file created?
2. RawFile opened, as a server reader would, while the collector's connection holds a write
   transaction on the same file: does opening need the write lock?
3. After a writer is killed (simulated by never closing it, then copying the files), does
   opening and closing through RawFile change the collector's .db?
4. FileMap.expired_raw against a day that has -wal and -shm side files beside it.
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

from submeter.core.models import SampleBatch, WorkloadSample
from submeter.store.files import FileMap
from submeter.store.raw import RawFile

DAY0 = 1_795_132_800.0  # 2026-11-20 00:00:00 UTC


def tick(raw: RawFile, at: float) -> None:
    batch = SampleBatch(
        taken_at=at,
        interval_s=1.0,
        gap=False,
        processes=(),
        exited=(),
        logical_cores=8,
        cpu_busy_s=0.0,
        memory_available_bytes=1 << 33,
    )
    work = WorkloadSample(
        taken_at=at,
        interval_s=1.0,
        workload="w",
        source="polled",
        cpu_s=0.5,
        memory_bytes=1 << 27,
        io_read_bytes=0,
        io_write_bytes=0,
        processes=1,
        started=0,
    )
    raw.write(batch, [work], {})


def sizes(path: Path) -> str:
    found = sorted(path.parent.glob(path.name + "*"))
    return ", ".join(f"{p.name} {p.stat().st_size} B" for p in found) or "nothing"


def main() -> None:
    with tempfile.TemporaryDirectory() as name:
        folder = Path(name)
        missing = folder / "2026-01-01.db"
        reader = RawFile(missing)
        rows = reader.workload_samples(0, 2e9)
        reader.close()
        print(f"1. reading a day with no file returned {len(rows)} rows and left: {sizes(missing)}")

        today = folder / "2026-11-20.db"
        collector = RawFile(today)
        tick(collector, DAY0 + 1)
        holder = sqlite3.connect(today)
        holder.execute("BEGIN IMMEDIATE")
        try:
            RawFile(today).close()
            outcome = "opened"
        except sqlite3.OperationalError as error:
            outcome = f"refused: {error}"
        holder.rollback()
        holder.close()
        print(f"2. RawFile opened while the collector holds the write lock: {outcome}")

        crashed = folder / "crash" / "2026-11-19.db"
        writer = RawFile(crashed)
        for second in range(1, 121):
            tick(writer, DAY0 - 86400 + second)
        copy = folder / "copy"
        copy.mkdir()
        for path in crashed.parent.glob("*"):
            shutil.copy(path, copy / path.name)
        target = copy / crashed.name
        before = target.stat().st_size
        print(f"3. killed writer's files (copied while it is still open): {sizes(target)}")
        reader = RawFile(target)
        count = len(reader.workload_samples(0, 2e9))
        reader.close()
        print(
            f"   RawFile read {count} rows and on close the .db went from {before} B to "
            f"{target.stat().st_size} B; left: {sizes(target)}"
        )
        writer.close()

        files = FileMap.discover({"SUBMETER_HOME": str(folder / "home")})
        files.ensure()
        day = files.raw_file(date(2026, 11, 10))
        for suffix, size in (("", 4096), ("-wal", 1 << 20), ("-shm", 32768)):
            Path(str(day) + suffix).write_bytes(b"\0" * size)
        expired = files.expired_raw(DAY0, 48 * 3600)
        files_after = [p.name for p in files.raw_dir.iterdir() if p not in expired]
        print(
            f"4. expired_raw returns {[p.name for p in expired]}; deleting those leaves "
            f"{sorted(files_after)}, which disk_use counts under raw: "
            f"{files.disk_use()['raw'] - 4096} B after the .db is gone"
        )


if __name__ == "__main__":
    main()
