"""Probe: the raw schema against the table list, the word "unavailable", and a later version.

Reads and measures only. Writes raw files in a temporary folder.

    .venv/bin/python docs/review/probes/c-storage/schema_gaps.py

1. The tables raw.py creates against the list in docs/13-build-list.md, and their columns.
2. Whether a workload row or a bucket can say that a figure was unavailable.
3. A newer collector reopening today's file: the probe swaps in a version 2 schema with one more
   column (by setting two module names in memory, no file is edited) and opens a version 1 file.
4. Opening a day that has no file through RawFile, as a reader might.
"""

from __future__ import annotations

import re
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

from _synth import DAY0, pipeline, proc, snap
from pydantic import ValidationError

from submeter.core.models import Bucket, WorkloadSample
from submeter.store import raw
from submeter.store.files import FileMap

DOCS = Path(__file__).resolve().parents[3]


def tables(path: Path) -> dict[str, list[tuple[str, str, int]]]:
    db = sqlite3.connect(path)
    names = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
    out = {
        name: [(row[1], row[2], row[3]) for row in db.execute(f"PRAGMA table_info({name})")]
        for name in names
    }
    db.close()
    return out


def main() -> None:
    with tempfile.TemporaryDirectory() as name:
        files = FileMap.discover({"SUBMETER_HOME": name})
        path = files.raw_file(date(2026, 11, 20))
        first = raw.RawFile(path)
        shots = [snap(DAY0 + t, [proc(1, 0.5 * t, io_read_bytes=None)]) for t in range(3)]
        for batch, workloads, names in pipeline(shots):
            first.write(batch, workloads, names)
            sample = workloads[0]
        first.close(at=DAY0 + 2)

        found = tables(path)
        text = (DOCS / "13-build-list.md").read_text(encoding="utf-8")
        listed = re.findall(
            r"`(\w+)`", text[text.index("- Raw file, one per day:") :].split("\n")[0]
        )
        print(f"1. tables in a raw file match docs/13: {sorted(found) == sorted(listed)}")
        for table, columns in found.items():
            nullable = [column for column, _, notnull in columns if not notnull]
            print(
                f"   {table}: {', '.join(column for column, _, _ in columns)}"
                f" | may be NULL: {nullable or 'none'}"
            )

        print(
            f"2. a process whose I/O could not be read (io_read_bytes None) is totalled into a "
            f"workload row with io_read_bytes = {sample.io_read_bytes}"
        )
        try:
            WorkloadSample(**{**sample.model_dump(), "io_read_bytes": None})
            refused = "accepted"
        except ValidationError:
            refused = "refused"
        optional = [f for f, info in Bucket.model_fields.items() if not info.is_required()]
        print(
            f"   a WorkloadSample with io_read_bytes = None is {refused}; Bucket fields that may "
            f"be left out or None: {optional or 'none'}"
        )

        old_schema, old_version = raw._SCHEMA, raw.SCHEMA_VERSION
        raw._SCHEMA = old_schema.replace(
            "started INTEGER NOT NULL,\n    PRIMARY KEY (ts, workload)",
            "started INTEGER NOT NULL, uss_bytes INTEGER,\n    PRIMARY KEY (ts, workload)",
        )
        raw.SCHEMA_VERSION = 2
        assert old_schema != raw._SCHEMA, "the stand-in schema must differ"
        try:
            raw.RawFile(path).close()
            fresh = files.raw_file(date(2026, 11, 21))
            raw.RawFile(fresh).close()
        finally:
            raw._SCHEMA, raw.SCHEMA_VERSION = old_schema, old_version
        db = sqlite3.connect(path)
        version = db.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()[0]
        try:
            db.execute("INSERT INTO workload_raw VALUES (1, 'a', 'polled', 1, 0, 0, 0, 0, 0, 0, 0)")
            outcome = "accepted"
        except sqlite3.Error as error:
            outcome = f"fails: {error}"
        db.close()
        print(
            f"3. a version 2 collector reopened the version 1 file without an error. The file "
            f"still says schema_version {version} and workload_raw has "
            f"{len(tables(path)['workload_raw'])} columns (a fresh version 2 file has "
            f"{len(tables(fresh)['workload_raw'])}). Its 11-value insert then {outcome}"
        )

        missing = files.raw_file(date(2026, 1, 1))
        raw.RawFile(missing).close()
        print(
            f"4. RawFile on a day with no data created {missing.name} ({missing.stat().st_size} B)"
            f"; RawFile has no way to open a file without writing to it"
        )


if __name__ == "__main__":
    main()
