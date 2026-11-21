"""Severity audit probe for cluster P3: what the raw file holds after the bad process exits.

Logic only. Builds hand-made SampleBatch objects (fake names, no real process is read), writes
them through the baseline's RawFile into a temporary folder that is removed, and prints counts.
Nothing is timed and nothing is sent anywhere.

    uv run python docs/review/probes/audit/audit_p3_state_desync.py

Tick 1: process A (new, valid text) is listed before process B (new, its last argument holds a
lone surrogate, as psutil returns for a non-UTF-8 byte). Tick 2: B has exited, A is still
running. The question is whether tick 2 restores A's process row, which tick 1 rolled back.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from submeter.core.models import ProcessKey, ProcessSample, SampleBatch
from submeter.store.raw import RawFile

T0 = 1_795_132_800.0 + 3600.0
A = ProcessKey(pid=101, started=T0 - 50)
B = ProcessKey(pid=102, started=T0 - 40)


def sample(key: ProcessKey, cmdline: tuple[str, ...]) -> ProcessSample:
    return ProcessSample(
        key=key,
        parent_pid=1,
        exe="tool",
        cmdline=cmdline,
        cwd=None,
        cpu_s=0.5,
        io_read_bytes=0,
        io_write_bytes=0,
        memory_bytes=100 * 1024**2,
        threads=4,
        first_seen=True,
        restricted=False,
    )


def batch(at: float, processes: tuple[ProcessSample, ...], exited: tuple[ProcessKey, ...]):
    return SampleBatch(
        taken_at=at,
        interval_s=1.0,
        gap=False,
        processes=processes,
        exited=exited,
        logical_cores=8,
        cpu_busy_s=1.0,
        memory_available_bytes=8 * 1024**3,
    )


def main() -> None:
    good = sample(A, ("tool", "--run", "job"))
    bad = sample(B, ("tool", "caf\udce9-FAKE"))
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "p3.db"
        raw = RawFile(path, redaction="scrub")
        try:
            raw.write(batch(T0, (good, bad), ()), [], {})
            print("tick 1: ok")
        except UnicodeEncodeError as error:
            print(f"tick 1: {type(error).__name__}")
        raw.write(batch(T0 + 1, (sample(A, good.cmdline or ()),), (B,)), [], {})
        print("tick 2: ok (B has exited)")
        raw.close(T0 + 2)
        db = sqlite3.connect(path)
        rows = db.execute("SELECT COUNT(*) FROM process WHERE pid = ?", (A.pid,)).fetchone()[0]
        raws = db.execute("SELECT COUNT(*) FROM process_raw WHERE pid = ?", (A.pid,)).fetchone()
        cpu = db.execute("SELECT COALESCE(SUM(cpu_s), 0) FROM process_raw").fetchone()[0]
        db.close()
        print(f"A: process rows {rows}, process_raw rows {raws[0]}")
        print(f"CPU stored for A over two ticks: {cpu:.1f} s of 1.0 s read")


if __name__ == "__main__":
    main()
