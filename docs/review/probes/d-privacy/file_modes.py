"""Show the permissions the baseline gives the folders and files it creates.

Run:  uv run python docs/review/probes/d-privacy/file_modes.py

For three umasks it points SUBMETER_HOME at a temporary folder, calls FileMap.ensure, opens a
RawFile (so the write-ahead log and its index exist) and takes an InstanceLock, then prints the
mode of everything created. The brief says every data file and the API token are restricted to
the current user. The temporary folder is removed at the end and the umask is put back.
"""

from __future__ import annotations

import os
import stat
import tempfile
from datetime import date
from pathlib import Path

from submeter.store.files import FileMap, InstanceLock
from submeter.store.raw import RawFile


def describe(path: Path) -> str:
    mode = stat.S_IMODE(path.stat().st_mode)
    who = [
        name for name, bit in (("group", stat.S_IRGRP), ("everyone", stat.S_IROTH)) if mode & bit
    ]
    return f"{mode:04o}  readable by owner" + "".join(f", {name}" for name in who)


def create_and_list(root: Path) -> None:
    files = FileMap.discover({"SUBMETER_HOME": str(root)})
    files.ensure()
    raw = RawFile(files.raw_file(date(2026, 11, 20)))
    raw.record_event(0.0, "probe", "x")  # leaves the -wal and -shm files in place while open
    lock = InstanceLock(files.lock_file("collector"))
    lock.acquire()
    for path in sorted(root.rglob("*")):
        kind = "dir " if path.is_dir() else "file"
        print(f"    {kind} {describe(path)}  {path.relative_to(root)}")
    lock.release()
    raw.close()


def main() -> None:
    home = stat.S_IMODE(Path.home().stat().st_mode)
    print(f"the home folder itself is {home:04o}; the umask this was run with is listed first")
    start = os.umask(0)
    os.umask(start)
    try:
        with tempfile.TemporaryDirectory() as name:
            for mask in dict.fromkeys((start, 0o022, 0o077)):
                os.umask(mask)
                print(f"  umask {mask:04o}")
                create_and_list(Path(name) / f"{mask:04o}")
            os.umask(0o022)
            nested = Path(name) / "a" / "b" / "c"
            nested.mkdir(mode=0o700, parents=True)
            shown = [f"{stat.S_IMODE(p.stat().st_mode):04o}" for p in (nested.parents[1], nested)]
            print(f"  Path.mkdir(mode=0o700, parents=True): parent {shown[0]}, leaf {shown[1]}")
    finally:
        os.umask(start)


if __name__ == "__main__":
    main()
