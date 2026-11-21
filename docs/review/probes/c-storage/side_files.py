"""Probe: the side files (-wal, -shm) a raw file carries, and what readers and deleters meet.

Reads and measures only. Writes raw files in a temporary folder. No timing is reported.

    .venv/bin/python docs/review/probes/c-storage/side_files.py

The design calls retention "a file delete" and tells the server to open closed files only for
the length of a query. This probe checks, on this machine's SQLite, how many files one day of
raw data really is in each state, what each way of opening a file for reading leaves behind,
whether a read-only reader can read a file whose writer was killed, and what happens to a
file that is moved or deleted without its side files. The writer is crash_kill.py --write.
"""

from __future__ import annotations

import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from _synth import DAY0, pipeline, proc, snap

from submeter.store.raw import RawFile

WRITER = Path(__file__).with_name("crash_kill.py")


def names(folder: Path) -> str:
    found = sorted(f"{p.name} {p.stat().st_size} B" for p in folder.iterdir() if p.is_file())
    return ", ".join(found) or "nothing"


def clean_file(path: Path, ticks: int = 50) -> None:
    raw = RawFile(path)
    shots = (snap(DAY0 + t, [proc(pid, 0.2 * t) for pid in range(20)]) for t in range(ticks + 1))
    for batch, workloads, assigned in pipeline(shots):
        raw.write(batch, workloads, assigned)
    raw.close(at=DAY0 + ticks)


def killed_file(path: Path, ticks: int, first: int = 0) -> int:
    """Run the writer for some ticks, kill it with SIGKILL, return the last tick it reported."""
    child = subprocess.Popen(
        [sys.executable, str(WRITER), "--write", str(path), str(first)],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert child.stdout is not None
    seen = [child.stdout.readline() for _ in range(ticks)]
    child.send_signal(signal.SIGKILL)
    seen += child.stdout.read().split()
    child.wait()
    return int(seen[-1])


def read_ticks(uri: str) -> str:
    try:
        db = sqlite3.connect(uri, uri=True)
        try:
            count, last = db.execute("SELECT COUNT(*), MAX(ts) FROM system_raw").fetchone()
            return f"reads {count} ticks, last {round(last - DAY0)}"
        finally:
            db.close()
    except sqlite3.Error as error:
        return f"fails with {type(error).__name__}: {error}"


def after_clean_close(folder: Path) -> None:
    for label, query in (
        ("read-only (mode=ro)", "?mode=ro"),
        ("read-write (the default)", ""),
        ("immutable (immutable=1)", "?immutable=1"),
    ):
        home = folder / label.split()[0]
        home.mkdir()
        path = home / "2026-11-19.db"
        clean_file(path)
        before = names(home)
        result = read_ticks(f"file:{path}{query}")
        print(f"  {label:<26} {result}; before: {before}; after: {names(home)}")


def after_a_kill(folder: Path) -> None:
    home = folder / "killed"
    home.mkdir()
    path = home / "2026-11-20.db"
    acknowledged = killed_file(path, 120)
    print(f"  the writer reported tick {acknowledged} and was killed; on disk: {names(home)}")
    for label, query in (("immutable=1", "?immutable=1"), ("mode=ro", "?mode=ro")):
        print(f"  {label:<12} reader: {read_ticks(f'file:{path}{query}')}")

    apart = folder / "quarantine"
    apart.mkdir()
    shutil.copy2(path, apart / path.name)  # the database file alone, as a careless move would
    print(f"  the .db alone, moved elsewhere: {read_ticks(f'file:{apart / path.name}')}")
    print(f"  read-write   reader: {read_ticks(f'file:{path}')}; on disk after: {names(home)}")

    # the day's file is taken away without its log, and the collector then starts the day again
    acknowledged = killed_file(path, 60, first=acknowledged + 1)
    stale = path.with_name(path.name + "-wal").stat().st_size
    path.unlink()
    RawFile(path).close()
    db = sqlite3.connect(path)
    ticks = db.execute("SELECT COUNT(*) FROM system_raw").fetchone()[0]
    check = db.execute("PRAGMA integrity_check").fetchone()[0]
    db.close()
    print(
        f"  .db deleted with a {stale} B log left behind, then created again under the same "
        f"name: integrity {check}, {ticks} ticks in the new file; on disk: {names(home)}"
    )


def delete_while_open(folder: Path) -> None:
    home = folder / "open"
    home.mkdir()
    path = home / "2026-11-18.db"
    clean_file(path)
    reader = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    reader.execute("SELECT COUNT(*) FROM system_raw").fetchone()
    try:
        path.unlink()
        outcome = "allowed"
    except OSError as error:
        outcome = f"refused ({type(error).__name__})"
    held = [
        os.readlink(link).rsplit("/", 1)[-1]
        for link in Path("/proc/self/fd").iterdir()
        if link.is_symlink() and "2026-11-18" in os.readlink(link)
    ]
    still = reader.execute("SELECT COUNT(*) FROM system_raw").fetchone()[0]
    print(
        f"  deleting the .db under an open reader on {sys.platform}: {outcome}; the reader still "
        f"reads {still} ticks; this process still holds {sorted(held)}; left in the folder: "
        f"{names(home)}"
    )
    reader.close()
    print(f"  after the reader closed: {names(home)}")


def main() -> None:
    print(f"SQLite {sqlite3.sqlite_version} on {sys.platform}")
    with tempfile.TemporaryDirectory() as name:
        folder = Path(name)
        print("1. a cleanly closed file, opened for one query and closed again:")
        after_clean_close(folder)
        print("2. a file whose writer was killed:")
        after_a_kill(folder)
        print("3. retention while a reader has the file open:")
        delete_while_open(folder)


if __name__ == "__main__":
    main()
