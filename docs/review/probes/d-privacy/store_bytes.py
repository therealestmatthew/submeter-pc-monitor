"""Write processes through the baseline's own path (Sampler, then RawFile) and search the file.

Run:  uv run python docs/review/probes/d-privacy/store_bytes.py

For each redaction mode it stores six made-up processes and one event, closes the file, and
reports which fake secrets and which other fields are present in the bytes on disk. It writes
only inside a temporary folder, which is removed at the end.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import get_args

from submeter.collector.sampler import Sampler
from submeter.core.models import ProcessCounters, ProcessKey, Snapshot, SystemCounters
from submeter.privacy.redact import Mode
from submeter.store.raw import RawFile

# (what the case shows, exe, command line as the provider hands it over, marker to search for)
PROCESSES: list[tuple[str, str, tuple[str, ...], str]] = [
    (
        "flag then value, split (the tested form)",
        "tool",
        ("tool", "--api-key", "FAKE-A1"),
        "FAKE-A1",
    ),
    ("HTTP header, split", "curl", ("curl", "-H", "Authorization: Bearer FAKE-B2"), "FAKE-B2"),
    ("shell wrapper, split", "bash", ("bash", "-c", "tool --api-key FAKE-C3"), "FAKE-C3"),
    ("one unsplit string", "app.exe", (r"C:\t\app.exe --api-key FAKE-D4",), "FAKE-D4"),
    ("rewritten title, unsplit", "postgres", ("postgres: alice FAKE-E5 idle",), "FAKE-E5"),
    ("exe given as a full path", r"C:\Users\FAKE-F6\bin\tool.exe", ("tool.exe",), "FAKE-F6"),
]
CWD_MARKER, EVENT_MARKER = "FAKE-G7", "FAKE-H8"


def snapshot(at: float, cpu: float) -> Snapshot:
    system = SystemCounters(
        logical_cores=4,
        cpu_busy_s=(cpu, 0.0, 0.0, 0.0),
        memory_total_bytes=16 * 1024**3,
        memory_available_bytes=8 * 1024**3,
    )
    processes = tuple(
        ProcessCounters(
            key=ProcessKey(pid=100 + index, started=50.0),
            exe=exe,
            cmdline=cmdline,
            cwd=f"/work/{CWD_MARKER}",
            cpu_s=cpu,
            memory_bytes=50 * 1024**2,
        )
        for index, (_, exe, cmdline, _) in enumerate(PROCESSES)
    )
    return Snapshot(taken_at=at, monotonic=at, processes=processes, system=system)


def stored_bytes(folder: Path, mode: Mode) -> bytes:
    path = folder / f"{mode}.db"
    sampler, raw = Sampler(), RawFile(path, redaction=mode)
    sampler.ingest(snapshot(1000.0, 1.0))
    batch = sampler.ingest(snapshot(1001.0, 1.5))
    assert batch is not None
    raw.write(batch, [], {}, keyframe=True)
    raw.record_event(1001.0, "provider", f"fell back while reading: tool --api-key {EVENT_MARKER}")
    raw.close(at=1001.0)
    return b"".join(found.read_bytes() for found in sorted(folder.glob(f"{mode}.db*")))


def main() -> None:
    with tempfile.TemporaryDirectory() as name:
        for mode in get_args(Mode):
            data = stored_bytes(Path(name), mode)
            print(f"redaction = {mode}")
            for what, _, _, marker in PROCESSES:
                found = "ON DISK" if marker.encode() in data else "absent"
                print(f"  {found:<9}{what}")
            for what, marker in (("working folder", CWD_MARKER), ("event detail", EVENT_MARKER)):
                found = "ON DISK" if marker.encode() in data else "absent"
                print(f"  {found:<9}{what}")


if __name__ == "__main__":
    main()
