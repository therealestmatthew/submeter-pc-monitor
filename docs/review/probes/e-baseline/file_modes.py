"""Probe: who may read the folders and files the baseline creates, on Linux.

docs/17-build-prompt.md says "Restrict every data file and the API token to the current user."
This creates the file map, a raw file and an instance lock under a temporary SUBMETER_HOME
(removed afterwards) with the session's own umask, and prints each one's permission bits.
Run from the repository root:

    uv run python docs/review/probes/e-baseline/file_modes.py
"""

from __future__ import annotations

import os
import stat
import tempfile
from datetime import date
from pathlib import Path

from submeter.store.files import FileMap, InstanceLock
from submeter.store.raw import RawFile


def mode(path: Path) -> str:
    return stat.filemode(path.stat().st_mode)


def main() -> None:
    current = os.umask(0)
    os.umask(current)
    print(f"umask {current:03o}")
    with tempfile.TemporaryDirectory() as name:
        files = FileMap.discover({"SUBMETER_HOME": name})
        files.ensure()
        raw = RawFile(files.raw_file(date(2026, 11, 20)))
        lock = InstanceLock(files.lock_file("collector"))
        assert lock.acquire()
        for label, path in (
            ("data folder", files.data_dir),
            ("raw folder", files.raw_dir),
            ("raw file", raw.path),
            ("raw write-ahead log", Path(f"{raw.path}-wal")),
            ("state folder", files.state_dir),
            ("lock file", files.lock_file("collector")),
            ("pid file", lock.pid_file),
        ):
            print(f"   {label:<20} {mode(path)}")
        lock.release()
        raw.close()


if __name__ == "__main__":
    main()
