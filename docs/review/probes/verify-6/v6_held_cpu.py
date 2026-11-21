"""Verifier probe for S4: how much per-process CPU sits only in memory, and where it is written.

Reads and measures only. Writes a raw file in a temporary folder. Nothing is timed.

    uv run python docs/review/probes/verify-6/v6_held_cpu.py

Independent of the lead's probes. 40 processes each use 0.4% of a core (under the 0.5-point
change threshold) and keep a steady memory size, at a 1 s interval through RawStore with the
default 600 s keyframe. Ticks start at 10:55 UTC. Before closing, a second connection opened
read-only sees what a crash would leave. The probe reports the CPU missing from process_raw,
and how much of the CPU used from 10:55 to 11:00 process rows stamp in that hour.
"""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import date
from pathlib import Path

from submeter.core.models import ProcessKey, ProcessSample, SampleBatch, WorkloadSample
from submeter.store.files import FileMap
from submeter.store.raw import RawStore

DAY0 = 1_795_132_800.0  # 2026-11-20 00:00:00 UTC
START = DAY0 + 10 * 3600 + 55 * 60
N, SHARE, TICKS = 40, 0.004, 900


def proc(pid: int) -> ProcessSample:
    return ProcessSample(
        key=ProcessKey(pid=pid, started=1.0),
        parent_pid=None,
        exe="quiet",
        cmdline=None,
        cwd=None,
        cpu_s=SHARE,
        io_read_bytes=0,
        io_write_bytes=0,
        memory_bytes=50 << 20,
        threads=2,
        first_seen=False,
        restricted=False,
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as name:
        files = FileMap.discover({"SUBMETER_HOME": str(Path(name))})
        store = RawStore(files)
        for tick in range(1, TICKS + 1):
            at = START + tick
            batch = SampleBatch(
                taken_at=at,
                interval_s=1.0,
                gap=False,
                processes=tuple(proc(pid) for pid in range(1, N + 1)),
                exited=(),
                logical_cores=8,
                cpu_busy_s=N * SHARE,
                memory_available_bytes=1 << 33,
            )
            work = WorkloadSample(
                taken_at=at,
                interval_s=1.0,
                workload="quiet",
                source="polled",
                cpu_s=N * SHARE,
                memory_bytes=N * (50 << 20),
                io_read_bytes=0,
                io_write_bytes=0,
                processes=N,
                started=0,
            )
            store.write(batch, [work], {proc(p).key: "quiet" for p in range(1, N + 1)})
        path = files.raw_file(date(2026, 11, 20))
        reader = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        process = reader.execute("SELECT SUM(cpu_s) FROM process_raw").fetchone()[0]
        workload = reader.execute("SELECT SUM(cpu_s) FROM workload_raw").fetchone()[0]
        stamps = sorted(
            {round(t - START) for (t,) in reader.execute("SELECT DISTINCT ts FROM process_raw")}
        )
        hour10 = reader.execute(
            "SELECT SUM(cpu_s) FROM process_raw WHERE ts <= ?", (DAY0 + 11 * 3600,)
        ).fetchone()[0]
        reader.close()
        used_hour10 = 300 * N * SHARE  # ticks ending 10:55:01 to 11:00:00
        print(
            f"{N} processes at {SHARE:.1%} of a core for {TICKS} s from 10:55: workload_raw "
            f"holds {workload:.2f} CPU-s, process_raw holds {process:.2f}; a crash now loses "
            f"{workload - process:.2f} CPU-s of process rows"
        )
        print(f"seconds after 10:55 at which process rows were written: {stamps}")
        print(
            f"10:00 hour: these processes used {used_hour10:.2f} CPU-s; process rows stamped in "
            f"that hour hold {hour10:.2f}; the rest is stamped at the 11:05 keyframe"
        )
        store.close()


if __name__ == "__main__":
    main()
