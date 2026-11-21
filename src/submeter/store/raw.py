"""One raw file per UTC day: every sample at full resolution, written by the collector alone.

Workload totals are written every interval. A process row is written only when
the process has used a noticeable amount of CPU or its memory has moved, and
the CPU it used in between is carried into the next row, so sums stay exact.
A keyframe writes every live process in full; one opens each file and one
follows every keyframe interval, so no reader has to search far back to know
a process's state.

Command lines are redacted here, on the way to disk, whatever the caller did.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from contextlib import closing, contextmanager
from datetime import date
from pathlib import Path
from typing import Final

from submeter.core.models import (
    AccountingSource,
    ProcessKey,
    ProcessSample,
    SampleBatch,
    WorkloadSample,
)
from submeter.privacy.redact import Mode, redact_cmdline
from submeter.store.files import FileMap, utc_day

SCHEMA_VERSION: Final = 1
HELD_CPU_LIMIT_S: Final = 60.0  # a quiet process's CPU is written at least this often

_SCHEMA: Final = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS event (ts REAL NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS command (id INTEGER PRIMARY KEY, text TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS process (
    pid INTEGER NOT NULL, started REAL NOT NULL, parent_pid INTEGER, exe TEXT NOT NULL,
    command_id INTEGER REFERENCES command(id), workload TEXT NOT NULL, first_seen REAL NOT NULL,
    PRIMARY KEY (pid, started)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS workload_raw (
    ts REAL NOT NULL, workload TEXT NOT NULL, source TEXT NOT NULL, interval_s REAL NOT NULL,
    cpu_s REAL NOT NULL, memory_bytes INTEGER NOT NULL, io_read_bytes INTEGER NOT NULL,
    io_write_bytes INTEGER NOT NULL, processes INTEGER NOT NULL, started INTEGER NOT NULL,
    gap INTEGER NOT NULL, PRIMARY KEY (ts, workload)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS process_raw (
    ts REAL NOT NULL, pid INTEGER NOT NULL, started REAL NOT NULL, cpu_s REAL NOT NULL,
    memory_bytes INTEGER NOT NULL, threads INTEGER, keyframe INTEGER NOT NULL,
    PRIMARY KEY (ts, pid, started)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS system_raw (
    ts REAL PRIMARY KEY, interval_s REAL NOT NULL, logical_cores INTEGER NOT NULL,
    cpu_busy_s REAL NOT NULL, memory_available_bytes INTEGER NOT NULL,
    gap INTEGER NOT NULL) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS gap (start REAL NOT NULL, end REAL NOT NULL, reason TEXT NOT NULL);
"""


def _storable(text: str) -> str:
    """Text SQLite can store: an undecodable byte the OS handed over is kept as an escape."""
    return text.encode("utf-8", "backslashreplace").decode("utf-8")


def open_read_only(path: Path) -> sqlite3.Connection:
    """Open a raw file to read. It never creates the file, writes to it or checkpoints its log."""
    if not path.is_file():
        raise FileNotFoundError(f"no raw file at {path}")
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


class RawFile:
    def __init__(
        self,
        path: Path,
        *,
        cpu_points: float = 0.5,
        memory_step: int = 8 * 1024**2,
        redaction: Mode = "exe_only",
        redact_patterns: Sequence[str | re.Pattern[str]] = (),
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        path.touch(0o600)  # private before SQLite opens it; -wal and -shm copy its mode
        self._db = sqlite3.connect(path)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")
        self._db.execute("PRAGMA journal_size_limit=4194304")
        self._db.executescript(_SCHEMA)
        with self._db:
            self._db.execute(
                "INSERT OR IGNORE INTO meta VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),)
            )
        self._cpu_share = cpu_points / 100.0
        self._memory_step = memory_step
        self._redaction: Mode = redaction
        self._patterns = tuple(re.compile(pattern) for pattern in redact_patterns)
        self._last_at: float | None = None
        self._pending: dict[ProcessKey, float] = {}
        self._waited: dict[ProcessKey, float] = {}
        self._memory: dict[ProcessKey, int] = {}
        self._threads: dict[ProcessKey, int | None] = {}

    def write(
        self,
        batch: SampleBatch,
        workloads: Sequence[WorkloadSample],
        workload_of: Mapping[ProcessKey, str],
        *,
        keyframe: bool = False,
    ) -> int:
        """Store one batch in one transaction. Returns how many process rows were written."""
        written = 0
        full = keyframe or batch.gap
        with self._undone_on_error(), self._db:
            if self._last_at is not None and batch.taken_at // 3600 != self._last_at // 3600:
                written += self._flush(self._last_at)  # no carried CPU crosses an hour
            if batch.gap:
                start = batch.taken_at - batch.interval_s
                self._db.execute(
                    "INSERT INTO gap VALUES (?, ?, ?)", (start, batch.taken_at, "not observed")
                )
            self._db.execute(
                "INSERT OR REPLACE INTO system_raw VALUES (?, ?, ?, ?, ?, ?)",
                (
                    batch.taken_at,
                    batch.interval_s,
                    batch.logical_cores,
                    batch.cpu_busy_s,
                    batch.memory_available_bytes,
                    batch.gap,
                ),
            )
            self._db.executemany(
                "INSERT OR REPLACE INTO workload_raw VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        w.taken_at,
                        _storable(w.workload),
                        w.source.value,
                        w.interval_s,
                        w.cpu_s,
                        w.memory_bytes,
                        w.io_read_bytes,
                        w.io_write_bytes,
                        w.processes,
                        w.started,
                        w.gap,
                    )
                    for w in workloads
                ],
            )
            for sample in batch.processes:
                key = sample.key
                if key not in self._memory:
                    self._register(sample, workload_of.get(key, "unattributed"), batch.taken_at)
                pending = self._pending.get(key, 0.0) + sample.cpu_s
                waited = self._waited.get(key, 0.0) + batch.interval_s
                last = self._memory.get(key)
                moved = last is None or abs(sample.memory_bytes - last) >= self._memory_step
                held = pending > 0 and waited >= HELD_CPU_LIMIT_S
                if full or moved or held or pending >= self._cpu_share * waited:
                    self._row(
                        batch.taken_at, key, pending, sample.memory_bytes, sample.threads, full
                    )
                    self._memory[key] = sample.memory_bytes
                    pending, waited = 0.0, 0.0
                    written += 1
                self._pending[key], self._waited[key] = pending, waited
                self._threads[key] = sample.threads
            for key in batch.exited:
                written += self._finish(batch.taken_at, key)
        self._last_at = batch.taken_at
        return written

    def _flush(self, ts: float) -> int:
        """Write every process's pending CPU at ts, the last tick before a new hour."""
        held = [key for key, pending in self._pending.items() if pending > 0]
        for key in held:
            memory, threads = self._memory[key], self._threads[key]
            self._row(ts, key, self._pending[key], memory, threads, False)
            self._pending[key] = self._waited[key] = 0.0
        return len(held)

    @contextmanager
    def _undone_on_error(self) -> Iterator[None]:
        """If the transaction fails, put the in-memory state back to match the file."""
        kept = (dict(self._pending), dict(self._waited), dict(self._memory), dict(self._threads))
        try:
            yield
        except BaseException:
            self._pending, self._waited, self._memory, self._threads = kept
            raise

    def _register(self, sample: ProcessSample, workload: str, seen_at: float) -> None:
        command_id: int | None = None
        if sample.cmdline:
            cleaned = redact_cmdline(
                sample.cmdline, mode=self._redaction, exe=sample.exe, extra_patterns=self._patterns
            )
            text = _storable(" ".join(cleaned))
            self._db.execute("INSERT OR IGNORE INTO command (text) VALUES (?)", (text,))
            row = self._db.execute("SELECT id FROM command WHERE text = ?", (text,)).fetchone()
            command_id = int(row[0])
        self._db.execute(
            "INSERT OR IGNORE INTO process VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                sample.key.pid,
                sample.key.started,
                sample.parent_pid,
                _storable(sample.exe),
                command_id,
                _storable(workload),
                seen_at,
            ),
        )

    def _row(
        self,
        ts: float,
        key: ProcessKey,
        cpu_s: float,
        memory: int,
        threads: int | None,
        full: bool,
    ) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO process_raw VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ts, key.pid, key.started, cpu_s, memory, threads, int(full)),
        )

    def _finish(self, ts: float, key: ProcessKey) -> int:
        """Write whatever CPU a process still had pending, then forget it."""
        pending = self._pending.pop(key, 0.0)
        self._waited.pop(key, None)
        memory = self._memory.pop(key, 0)
        threads = self._threads.pop(key, 0)
        if pending <= 0:
            return 0
        self._row(ts, key, pending, memory, threads, False)
        return 1

    def record_event(self, ts: float, kind: str, detail: str) -> None:
        """Note something that starts a new epoch.

        That is a change of the sampling settings, the rules file, a provider's status, the
        hardware or the Submeter version, or a wall-clock step the collector detected. A cadence
        the collector changes itself does not start one.
        """
        with self._db:
            self._db.execute("INSERT INTO event VALUES (?, ?, ?)", (ts, kind, _storable(detail)))

    @staticmethod
    def workload_samples(path: Path, start: float, end: float) -> list[WorkloadSample]:
        """The workload rows with start <= ts < end, read without opening the file for writing."""
        with closing(open_read_only(path)) as db:
            rows = db.execute(
                "SELECT ts, interval_s, workload, source, cpu_s, memory_bytes, io_read_bytes,"
                " io_write_bytes, processes, started, gap FROM workload_raw"
                " WHERE ts >= ? AND ts < ? ORDER BY ts, workload",
                (start, end),
            ).fetchall()
        return [
            WorkloadSample(
                taken_at=row[0],
                interval_s=row[1],
                workload=row[2],
                source=AccountingSource(row[3]),
                cpu_s=row[4],
                memory_bytes=row[5],
                io_read_bytes=row[6],
                io_write_bytes=row[7],
                processes=row[8],
                started=row[9],
                gap=bool(row[10]),
            )
            for row in rows
        ]

    def process_cpu_total(self) -> float:
        row = self._db.execute("SELECT COALESCE(SUM(cpu_s), 0) FROM process_raw").fetchone()
        return float(row[0])

    def count(self, table: str) -> int:
        if table not in {"command", "event", "gap", "process", "process_raw", "workload_raw"}:
            raise ValueError(f"unknown table: {table}")
        return int(self._db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    def close(self, at: float | None = None) -> None:
        """Flush pending CPU so sums stay exact, shrink the write-ahead log, and close."""
        if at is not None:
            with self._db:
                for key in list(self._pending):
                    self._finish(at, key)
        self._db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self._db.close()


class RawStore:
    """Picks the day's file and decides when a keyframe is due."""

    def __init__(
        self,
        files: FileMap,
        *,
        keyframe_interval_s: float = 600.0,
        cpu_points: float = 0.5,
        memory_step: int = 8 * 1024**2,
        redaction: Mode = "exe_only",
        redact_patterns: Sequence[str] = (),
    ) -> None:
        self._files = files
        self._keyframe_interval_s = keyframe_interval_s
        self._cpu_points = cpu_points
        self._memory_step = memory_step
        self._redaction: Mode = redaction
        self._patterns = tuple(re.compile(pattern) for pattern in redact_patterns)
        self._file: RawFile | None = None
        self._day: date | None = None
        self._keyframe_at: float | None = None
        self._last_at: float | None = None

    def write(
        self,
        batch: SampleBatch,
        workloads: Sequence[WorkloadSample],
        workload_of: Mapping[ProcessKey, str],
    ) -> int:
        day = utc_day(batch.taken_at)
        if self._file is None or day != self._day:
            self.close()
            self._file = RawFile(
                self._files.raw_file(day),
                cpu_points=self._cpu_points,
                memory_step=self._memory_step,
                redaction=self._redaction,
                redact_patterns=self._patterns,
            )
            self._day, self._keyframe_at = day, None
        due = (
            self._keyframe_at is None
            or batch.taken_at - self._keyframe_at >= self._keyframe_interval_s
        )
        if due:
            self._keyframe_at = batch.taken_at
        self._last_at = batch.taken_at
        return self._file.write(batch, workloads, workload_of, keyframe=due)

    def close(self) -> None:
        if self._file is not None:
            self._file.close(self._last_at)
            self._file = None
