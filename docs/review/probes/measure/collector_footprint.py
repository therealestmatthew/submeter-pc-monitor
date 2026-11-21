"""Probe: memory held by a collector-shaped process, and what the raw store really writes.

Reads and measures only. It writes a raw file to a temporary folder and deletes it.

    uv run python docs/review/probes/measure/collector_footprint.py [TICKS] [INTERVAL_S]

It runs the baseline pipeline as a collector would (snapshot, deltas, attribution, raw store)
for TICKS ticks, default 120 at 1 s, then reports:
- resident, unique and proportional memory of this process, against the 80 MB switching rule;
- rows written per tick and bytes per row, against the brief's 90 bytes and 8.1 M rows per 48 h.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import time

import psutil

from submeter.attribution.rules import Attributor, RuleSet, aggregate
from submeter.collector.sampler import Sampler
from submeter.providers.psutil_provider import PsutilProvider
from submeter.store.files import FileMap
from submeter.store.raw import RawStore

MB = 1024**2


def main() -> int:
    ticks = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    interval = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    me = psutil.Process()
    print(f"python {sys.version.split()[0]} on {sys.platform}; load average {os.getloadavg()}")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as name:
        files = FileMap.discover({"SUBMETER_HOME": name})
        files.ensure()
        provider, sampler = PsutilProvider(), Sampler()
        attributor, store = Attributor(RuleSet(), self_pid=os.getpid()), RawStore(files)
        sampler.ingest(provider.snapshot())
        process_rows, counts, cpu_started = [], [], time.process_time()
        started = time.monotonic()
        for tick in range(ticks):
            time.sleep(max(0.0, started + (tick + 1) * interval - time.monotonic()))
            batch = sampler.ingest(provider.snapshot())
            assert batch is not None
            assignment = attributor.assign(batch.processes)
            workloads = aggregate(batch, assignment)
            names = {key: value.workload for key, value in assignment.items()}
            process_rows.append(store.write(batch, workloads, names))
            counts.append(len(batch.processes))
        cpu_used, elapsed = time.process_time() - cpu_started, time.monotonic() - started
        memory = me.memory_full_info()
        store.close()
        path = next(iter(files.raw_dir.glob("*.db")))
        size = path.stat().st_size
        db = sqlite3.connect(path)
        tables = ("process_raw", "workload_raw", "system_raw", "process", "command", "gap")
        rows = {
            table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables
        }
        page_size = db.execute("PRAGMA page_size").fetchone()[0]
        db.close()

    processes = sum(counts) / len(counts)
    first, later = process_rows[0], process_rows[1:]
    per_tick = sum(later) / max(len(later), 1)
    workloads_per_tick = rows["workload_raw"] / ticks
    sample_rows = rows["process_raw"] + rows["workload_raw"] + rows["system_raw"]
    ticks_48h = 172_800 / interval
    keyframes_48h = 288 * processes
    projected = (per_tick + workloads_per_tick + 1) * ticks_48h + keyframes_48h
    print(
        f"ran {ticks} ticks at {interval:g} s over {elapsed:.0f} s with {processes:.0f} processes"
    )
    print(
        f"memory of this process: resident {memory.rss / MB:.0f} MB, "
        f"unique {memory.uss / MB:.0f} MB, proportional {memory.pss / MB:.0f} MB "
        "(switching rule: 80 MB)"
    )
    print(
        f"CPU used by this process: {cpu_used:.1f} s over {elapsed:.0f} s, "
        f"{100 * cpu_used / elapsed:.1f}% of one core (limits: 3% active, 1% idle)"
    )
    print(f"rows by table: {rows}")
    print(
        f"process rows: {first} in the opening keyframe, then {per_tick:.1f} per tick "
        f"({100 * per_tick / processes:.1f}% of processes); "
        f"workload rows {workloads_per_tick:.1f} per tick"
    )
    print(
        f"file size {size / MB:.2f} MB after close, page size {page_size}; "
        f"{size / sample_rows:.0f} bytes per sample row overall (brief assumes 90)"
    )
    print(
        f"projected for 48 h at this rate: {projected / 1e6:.1f} M rows, "
        f"{projected * size / sample_rows / 1e9:.2f} GB "
        "(brief: 8.1 M rows and 0.73 GB for 300 processes)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
