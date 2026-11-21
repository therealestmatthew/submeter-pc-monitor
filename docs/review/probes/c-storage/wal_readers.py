"""Probe: the write-ahead log with a writer in one process and readers in another.

Reads and measures only. Writes raw files in a temporary folder. Linux only (select on a pipe).
No timing is reported: sizes and counts only.

    .venv/bin/python docs/review/probes/c-storage/wal_readers.py

1. How many log pages one realistic tick commits, so how many ticks pass between automatic
   checkpoints, which are the only moments the log is synced under synchronous=NORMAL.
2. A read-only connection in this process polls while a child process writes.
3. A reader that leaves one cursor unfinished: how large the log grows, and whether it shrinks.
4. Closing order: the writer closes first, then a read-only reader. Which side files are left.
5. With strace, if it is installed: how many sync calls 600 ticks make under synchronous=NORMAL,
   which the baseline sets, and under FULL.

    wal_readers.py --write PATH [full]     (the child: writes until a line arrives on stdin)
"""

from __future__ import annotations

import itertools
import select
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from _synth import DAY0, pipeline, proc, snap, workload

from submeter.store.raw import RawFile

PROCESSES, BUSY, FRAME = 300, 30, 4096 + 24
NAMES = ("agents", "browser", "ide", "builds", "system", "restricted", "unattributed", "submeter")


def ticks(first: int = 0):
    """300 processes, 30 of them busy enough to be written every tick, and 8 workload rows."""
    shots = (
        snap(DAY0 + t, [proc(pid, (0.2 if pid < BUSY else 0.0) * t) for pid in range(PROCESSES)])
        for t in range(first, 10**9)
    )
    for batch, _, names in pipeline(shots):
        rows = [workload(batch.taken_at, 0.75, name=name) for name in NAMES]
        yield batch, rows, names


def child(path: Path, full: bool) -> None:
    raw, last = RawFile(path), DAY0
    if full:
        raw._db.execute("PRAGMA synchronous=FULL")  # the probe's only reach into a private name
    for batch, rows, names in ticks():
        raw.write(batch, rows, names)
        last = batch.taken_at
        print(round(last - DAY0), flush=True)
        if select.select([sys.stdin], [], [], 0)[0]:
            break
    raw.close(at=last)
    print("closed", flush=True)


def size(path: Path, suffix: str) -> int:
    side = path.with_name(path.name + suffix)
    return side.stat().st_size if side.exists() else -1


def pages_per_tick(folder: Path) -> None:
    path = folder / "pages.db"
    raw, sizes = RawFile(path), []
    for batch, rows, names in ticks():
        raw.write(batch, rows, names)
        sizes.append(size(path, "-wal"))
        if len(sizes) > 3 and sizes[-1] == sizes[-2]:  # the log was reset and is being reused
            break
    grown = [(b - a) // FRAME for a, b in itertools.pairwise(sizes) if b > a]
    steady = sorted(grown)[len(grown) // 2]
    print(
        f"1. log pages per tick: median {steady}, first tick (opening keyframe) "
        f"{(sizes[0] - 32) // FRAME}; the log reached {sizes[-1] / 2**20:.1f} MiB and was reset "
        f"after {len(sizes) - 1} ticks. At a 1 s interval that is one log sync every "
        f"{(len(sizes) - 1) / 60:.1f} minutes"
    )
    raw.close()


def wait_for(writer: subprocess.Popen[str], count: int) -> int:
    assert writer.stdout is not None
    tick = 0
    for _ in range(count):
        tick = int(writer.stdout.readline())
    return tick


def main() -> None:
    with tempfile.TemporaryDirectory() as name:
        folder = Path(name)
        pages_per_tick(folder)
        path = folder / "2026-11-20.db"
        writer = subprocess.Popen(
            [sys.executable, __file__, "--write", str(path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        wait_for(writer, 50)
        reader = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        counts, errors = [], 0
        for _ in range(40):
            wait_for(writer, 25)
            try:
                counts.append(reader.execute("SELECT COUNT(*) FROM workload_raw").fetchone()[0])
            except sqlite3.Error:
                errors += 1
        print(
            f"2. read-only connection in a second process: 40 polls, {errors} errors, counts "
            f"rising throughout: {counts == sorted(counts) and counts[0] < counts[-1]}"
        )

        before, held_from = size(path, "-wal"), wait_for(writer, 1)
        cursor = reader.execute("SELECT ts FROM workload_raw")
        cursor.fetchone()  # one row read, the rest left waiting: a read transaction stays open
        held_to = wait_for(writer, 4000)
        during = size(path, "-wal")
        cursor.close()
        wait_for(writer, 1500)
        after = size(path, "-wal")
        print(
            f"3. log size {before / 2**20:.1f} MiB before; {during / 2**20:.1f} MiB after an "
            f"unfinished cursor was held across {held_to - held_from} ticks "
            f"({(during - before) / (held_to - held_from) / 1024:.0f} KiB a tick); "
            f"{after / 2**20:.1f} MiB 1500 ticks after the cursor closed "
            f"(journal_size_limit is 64 MiB)"
        )

        stop(writer)
        print(f"4. writer closed with a reader still connected; side files: {sides(path)}")
        reader.close()
        print(f"   the read-only reader then closed, the last connection: {sides(path)}")
        again = sqlite3.connect(path)
        again.execute("SELECT COUNT(*) FROM meta").fetchone()
        again.close()
        print(f"   after a read-write connection read the file and closed: {sides(path)}")
        sync_counts(folder)


def stop(writer: subprocess.Popen[str]) -> int:
    """Ask the child to close its file cleanly. Returns the last tick it wrote."""
    assert writer.stdin is not None and writer.stdout is not None
    writer.stdin.write("stop\n")
    writer.stdin.flush()
    last = 0
    while (line := writer.stdout.readline().strip()) != "closed":
        last = int(line)
    writer.wait()
    return last


def sides(path: Path) -> str:
    found = {suffix: size(path, suffix) for suffix in ("-wal", "-shm")}
    return ", ".join(f"{k} {'gone' if v < 0 else f'{v} B'}" for k, v in found.items())


def sync_counts(folder: Path) -> None:
    if shutil.which("strace") is None:
        print("5. strace is not installed, so sync calls were not counted")
        return
    for mode in ("normal", "full"):
        trace = folder / f"{mode}.trace"
        command = ["strace", "-f", "-y", "-e", "trace=fsync,fdatasync", "-o", str(trace)]
        command += [sys.executable, __file__, "--write", str(folder / f"{mode}.db")]
        writer = subprocess.Popen(
            command + (["full"] if mode == "full" else []),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        last = max(wait_for(writer, 600), stop(writer))
        calls = [line for line in trace.read_text().splitlines() if "sync(" in line]
        log = sum("-wal>" in line for line in calls)
        print(
            f"5. synchronous={mode}: {len(calls)} fsync or fdatasync calls in {last} ticks and "
            f"one clean close; {log} of them on the log, so the log was synced about every "
            f"{last / max(log, 1):.0f} ticks"
        )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--write":
        child(Path(sys.argv[2]), full=len(sys.argv) > 3)
    else:
        main()
