"""Probe: which tables the bytes of a short raw file sit in, with this machine's real processes.

Reads and measures only. Writes one raw file in a temporary folder and deletes it. Prints byte
and row counts only, never a command line or a name. Nothing is timed.

    .venv/bin/python docs/review/probes/c-storage/raw_tables_real.py [TICKS]

docs/review/probes/measure/collector_footprint.out.txt reports 120 bytes per sample row from a
120-tick run. This shows how much of such a short file is the per-day tables (process, command
and its index) and how much the sample rows themselves take, using SQLite's dbstat table.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import time

from submeter.attribution.rules import Attributor, RuleSet, aggregate
from submeter.collector.sampler import Sampler
from submeter.providers.psutil_provider import PsutilProvider
from submeter.store.files import FileMap
from submeter.store.raw import RawStore

SAMPLE_TABLES = ("process_raw", "workload_raw", "system_raw")


def main() -> None:
    ticks = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    with tempfile.TemporaryDirectory() as name:
        files = FileMap.discover({"SUBMETER_HOME": name})
        provider, sampler, store = PsutilProvider(), Sampler(), RawStore(files)
        attributor = Attributor(RuleSet(), self_pid=os.getpid())
        sampler.ingest(provider.snapshot())
        for _ in range(ticks):
            time.sleep(0.05)
            batch = sampler.ingest(provider.snapshot())
            assert batch is not None
            assignment = attributor.assign(batch.processes)
            names = {key: value.workload for key, value in assignment.items()}
            store.write(batch, aggregate(batch, assignment), names)
        store.close()
        path = next(iter(files.raw_dir.glob("*.db")))
        size = path.stat().st_size
        db = sqlite3.connect(path)
        used = dict(db.execute("SELECT name, SUM(pgsize) FROM dbstat GROUP BY name"))
        rows = {
            table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        text = db.execute("SELECT COALESCE(SUM(LENGTH(text)), 0) FROM command").fetchone()[0]
        db.close()

    sample_rows = sum(rows[table] for table in SAMPLE_TABLES)
    sample_bytes = sum(used[table] for table in SAMPLE_TABLES)
    print(f"{ticks} ticks, file {size} B; pages by table: {dict(sorted(used.items()))}")
    print(f"rows by table: {rows}; redacted command text {text} characters, stored twice")
    print(
        f"sample rows: {sample_rows} in {sample_bytes} B = {sample_bytes / sample_rows:.0f} B a "
        f"row; the whole file over the same rows = {size / sample_rows:.0f} B a row; "
        f"{1 - sample_bytes / size:.0%} of the file is not sample rows"
    )
    for table in SAMPLE_TABLES:
        print(f"  {table}: {rows[table]} rows, {used[table] / rows[table]:.0f} B a row")


if __name__ == "__main__":
    main()
