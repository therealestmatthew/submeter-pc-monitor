"""Probe: drive the real RawFile and RawStore with synthetic batches and read the file back.

Writes only to a temporary folder, which it removes. Run from the repository root:

    uv run python docs/review/probes/e-baseline/raw_store_cases.py

Cases: the process table when a process changes program or workload, what a kill loses, what
the raw schema can hold per process, and (as controls) the exit, rollover and keyframe paths.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from submeter.collector.sampler import Sampler
from submeter.core.models import (
    ProcessCounters,
    ProcessKey,
    SampleBatch,
    Snapshot,
    SystemCounters,
    WorkloadSample,
)
from submeter.store.files import FileMap
from submeter.store.raw import RawFile, RawStore

MB = 1024**2
DAY0 = 1_795_132_800.0  # 2026-11-20 00:00:00 UTC


def proc(pid: int, cpu: float, *, started: float = 100.0, **extra: object) -> ProcessCounters:
    fields: dict[str, object] = {"exe": "tool", "cmdline": ("tool",), "memory_bytes": 50 * MB}
    fields.update(extra)
    return ProcessCounters(key=ProcessKey(pid=pid, started=started), cpu_s=cpu, **fields)


def snap(at: float, processes: list[ProcessCounters]) -> Snapshot:
    system = SystemCounters(
        logical_cores=4,
        cpu_busy_s=(0.0, 0.0, 0.0, 0.0),
        memory_total_bytes=16 * 1024**3,
        memory_available_bytes=8 * 1024**3,
    )
    return Snapshot(taken_at=at, monotonic=at, processes=tuple(processes), system=system)


def total(batch: SampleBatch, name: str = "all") -> list[WorkloadSample]:
    return [
        WorkloadSample(
            taken_at=batch.taken_at,
            interval_s=batch.interval_s,
            workload=name,
            source="polled",
            cpu_s=sum(sample.cpu_s for sample in batch.processes),
            memory_bytes=sum(sample.memory_bytes for sample in batch.processes),
            io_read_bytes=0,
            io_write_bytes=0,
            processes=len(batch.processes),
            started=0,
        )
    ]


def rows(path: Path, sql: str) -> list[tuple[object, ...]]:
    db = sqlite3.connect(path)
    try:
        return db.execute(sql).fetchall()
    finally:
        db.close()


def process_table_is_frozen(folder: Path) -> None:
    print("1. A process that changes program (exec) and workload after it is first seen")
    path = folder / "frozen.db"
    sampler, raw = Sampler(), RawFile(path)
    key = ProcessKey(pid=5, started=100.0)
    sampler.ingest(snap(1000, [proc(5, 0.0, exe="sh", cmdline=("sh", "run-node"))]))
    first = sampler.ingest(snap(1001, [proc(5, 0.1, exe="sh", cmdline=("sh", "run-node"))]))
    assert first is not None
    raw.write(first, total(first, "unattributed"), {key: "unattributed"})
    used = 0.1
    for tick in range(2, 12):  # the wrapper has exec'd node; a rule now claims it
        batch = sampler.ingest(
            snap(1000 + tick, [proc(5, 0.1 + 0.9 * (tick - 1), exe="node", cmdline=("node", "x"))])
        )
        assert batch is not None
        used += 0.9
        raw.write(batch, total(batch, "builds"), {key: "builds"})
    raw.close(at=1011)
    joined = rows(
        path,
        "SELECT p.exe, c.text, p.workload, ROUND(SUM(r.cpu_s), 2) FROM process_raw r"
        " JOIN process p USING (pid, started) LEFT JOIN command c ON c.id = p.command_id"
        " GROUP BY 1, 2, 3",
    )
    by_workload = rows(path, "SELECT workload, ROUND(SUM(cpu_s), 2) FROM workload_raw GROUP BY 1")
    print(f"   process table joined to process_raw (exe, command, workload, cpu_s): {joined}")
    print(f"   workload_raw totals: {by_workload}; the process really used {used:.2f} CPU-s")


def kill_loses_pending(folder: Path) -> None:
    print("2. The collector is killed between keyframes (no close)")
    path = folder / "killed.db"
    sampler, raw = Sampler(), RawFile(path)
    quiet = range(100, 400)  # 300 processes, each using 0.4% of a core
    sampler.ingest(snap(1000, [proc(pid, 0.0) for pid in quiet]))
    used = 0.0
    for tick in range(1, 541):  # nine minutes, one minute short of the next keyframe
        batch = sampler.ingest(snap(1000 + tick, [proc(pid, 0.004 * tick) for pid in quiet]))
        assert batch is not None
        used += sum(sample.cpu_s for sample in batch.processes)
        raw.write(batch, total(batch), {}, keyframe=tick == 1)
    del raw  # no close(at): what a kill or a power cut leaves behind
    stored = rows(path, "SELECT COALESCE(SUM(cpu_s), 0), COUNT(*) FROM process_raw")[0]
    workload = rows(path, "SELECT SUM(cpu_s) FROM workload_raw")[0][0]
    print(
        f"   processes used {used:.1f} CPU-s over 540 s; process_raw holds {stored[0]:.1f} in "
        f"{stored[1]} rows; workload_raw holds {workload:.1f}"
    )


def schema_columns(folder: Path) -> None:
    print("3. Columns the raw schema has for one process and for one workload")
    path = folder / "schema.db"
    RawFile(path).close()
    for table in ("process", "process_raw", "workload_raw", "system_raw"):
        columns = [
            f"{row[1]}{'' if row[3] else '?'}" for row in rows(path, f"PRAGMA table_info({table})")
        ]
        print(f"   {table}: {', '.join(columns)}   (? marks a column that may be NULL)")


def controls(folder: Path) -> None:
    print("4. Controls: CPU pending at exit, at midnight and at a keyframe is written")
    files = FileMap.discover({"SUBMETER_HOME": str(folder / "home")})
    store, sampler = RawStore(files, keyframe_interval_s=600), Sampler()
    start = DAY0 - 700
    sampler.ingest(snap(start, [proc(1, 0.0), proc(2, 0.0)]))
    used = 0.0
    for tick in range(1, 1401):  # crosses midnight at tick 700; pid 2 exits at tick 300
        alive = [proc(1, 0.001 * tick)] + ([proc(2, 0.001 * tick)] if tick < 300 else [])
        batch = sampler.ingest(snap(start + tick, alive))
        assert batch is not None
        used += sum(sample.cpu_s for sample in batch.processes)
        store.write(batch, total(batch), {})
    store.close()
    stored, keyframes = 0.0, []
    for path in sorted(files.raw_dir.glob("*.db")):
        stored += float(rows(path, "SELECT COALESCE(SUM(cpu_s), 0) FROM process_raw")[0][0])
        marks = rows(path, "SELECT DISTINCT ts FROM process_raw WHERE keyframe = 1 ORDER BY ts")
        keyframes.append((path.name, [round(float(row[0]) - DAY0) for row in marks]))
    print(
        f"   used {used:.3f} CPU-s, stored {stored:.3f}; keyframes (s from midnight): {keyframes}"
    )


def main() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as name:
        folder = Path(name)
        process_table_is_frozen(folder)
        kill_loses_pending(folder)
        schema_columns(folder)
        controls(folder)


if __name__ == "__main__":
    main()
