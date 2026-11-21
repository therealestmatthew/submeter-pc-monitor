"""Would a small change make the baseline's files private whatever the umask? POSIX only.

Run:  uv run python docs/review/probes/d-privacy/private_files.py

file_modes.py shows what the baseline creates today. This probe tries the change the review
proposes, under a umask of 0022, and prints the resulting modes:
1. each folder made on its own with os.mkdir(path, 0o700), never through parents=True;
2. each database file made empty with os.open(..., 0o600) before SQLite opens it, to see
   whether SQLite then gives the write-ahead log and its index the same mode;
3. the token written through os.open(..., O_EXCL, 0o600), and the pid file the same way;
4. a backup made with SQLite's online backup into a file that was, and was not, made first.
Everything happens in a temporary folder, and the umask is put back.
"""

from __future__ import annotations

import os
import sqlite3
import stat
import tempfile
from pathlib import Path


def mode(path: Path) -> str:
    return f"{stat.S_IMODE(path.stat().st_mode):04o}"


def private_dir(path: Path) -> None:
    for folder in (*reversed(path.parents), path):
        if not folder.exists():
            os.mkdir(folder, 0o700)


def private_file(path: Path, data: bytes = b"") -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)


def main() -> None:
    old = os.umask(0o022)
    try:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "home"
            raw, state = root / "data" / "raw", root / "state"
            private_dir(raw)
            private_dir(state)
            print(f"1. folders: home {mode(root)}, data {mode(raw.parent)}, raw {mode(raw)}")

            database = raw / "2026-11-20.db"
            private_file(database)
            db = sqlite3.connect(database)
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE t (x)")
            db.execute("INSERT INTO t VALUES (1)")
            db.commit()
            side = {p.name[len(database.name) :]: mode(p) for p in raw.glob("*.db-*")}
            print(f"2. database {mode(database)}, side files made by SQLite: {side}")

            private_file(state / "api-token", b"FAKE-token")
            private_file(state / "collector.pid", b"1")
            print(f"3. token {mode(state / 'api-token')}, pid file {mode(state / 'collector.pid')}")

            plain, made_first = raw / "plain-backup.db", raw / "private-backup.db"
            private_file(made_first)
            for target in (plain, made_first):
                copy = sqlite3.connect(target)
                db.backup(copy)
                copy.close()
            modes = f"{mode(plain)}, into a file made first {mode(made_first)}"
            print(f"4. backup into a new file {modes}")
            db.close()
    finally:
        os.umask(old)


if __name__ == "__main__":
    main()
