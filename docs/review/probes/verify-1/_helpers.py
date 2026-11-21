"""Shared synthetic snapshots for the verify-1 probes. Not a probe itself.

The probes beside it import it. Run each from the repository root:

    uv run python docs/review/probes/verify-1/NAME.py
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))

from submeter.core.models import ProcessCounters, ProcessKey, Snapshot, SystemCounters

MB = 1024**2
DAY0 = 1_795_132_800.0  # 2026-11-20 00:00:00 UTC


def proc(pid: int, cpu: float, *, started: float = 100.0, **extra: object) -> ProcessCounters:
    """One process's cumulative counters, 50 MiB unless told otherwise."""
    fields: dict[str, object] = {"exe": "tool", "cmdline": ("tool",), "memory_bytes": 50 * MB}
    fields.update(extra)
    return ProcessCounters(key=ProcessKey(pid=pid, started=started), cpu_s=cpu, **fields)


def snap(
    at: float, processes: Iterable[ProcessCounters], *, mono: float, busy: float = 0.0
) -> Snapshot:
    """A snapshot of a 4-core machine with both clocks given."""
    system = SystemCounters(
        logical_cores=4,
        cpu_busy_s=(busy, 0.0, 0.0, 0.0),
        memory_total_bytes=16 * 1024**3,
        memory_available_bytes=8 * 1024**3,
    )
    return Snapshot(taken_at=at, monotonic=mono, processes=tuple(processes), system=system)
