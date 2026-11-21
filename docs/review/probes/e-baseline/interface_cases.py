"""Probe: what the shared records and the raw schema cannot express that the brief asks for.

Reads only this process's own entry under /proc (part 4) and writes nothing. Run from the
repository root:

    uv run python docs/review/probes/e-baseline/interface_cases.py

Part 1 asks the frozen records to carry "unavailable" and gets refused. Part 2 lists the fields
each record has, beside the rows of the metric catalogue in docs/06-storage.md. Part 3 shows
what the tier chooser and the settings do with values the brief allows. Part 4 computes one
process's start time three ways, because ProcessKey compares that float for equality.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import psutil
from pydantic import ValidationError

from submeter.core.config import load_settings
from submeter.core.models import (
    Availability,
    Bucket,
    Finding,
    ProcessCounters,
    ProcessKey,
    ProcessSample,
    SampleBatch,
    SystemCounters,
    WorkloadSample,
)
from submeter.store.query import choose_tier

DAY = 86400.0
NOW = 1_795_132_800.0  # 2026-11-20 00:00:00 UTC
KEY = ProcessKey(pid=1, started=1.0)

# Rows of the metric catalogue (docs/06-storage.md, "Metric catalogue") and the Bucket fields
# that could hold what each row says is "kept per bucket". An empty tuple means no field.
CATALOGUE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("CPU time: sum, histogram of cores", ("cpu_s", "cores_hist")),
    (
        "Memory for growth: min, max, mean, last, histogram",
        ("memory_min", "memory_max", "memory_mean", "memory_last", "memory_hist"),
    ),
    ("Memory for totals (USS or PSS): max, mean, age of the reading", ()),
    ("Disk bytes read and written: sum", ("io_read_bytes", "io_write_bytes")),
    ("Processes alive and started: max and mean; sum", ("processes_max", "started")),
    ("Threads and handles: max", ()),
    ("GPU load by engine type: max, mean", ()),
    ("VRAM: max, mean", ()),
    ("Connections: max, mean", ()),
    ("Load per core and frequency: min, max, mean", ()),
    ("Commit, available memory, page reads and writes", ()),
    ("Run queue and pressure stall time", ()),
    ("Disk latency and queue", ()),
    ("Submeter's own cost: max, mean", ()),
)


def refused(label: str, build: object) -> None:
    try:
        build()  # type: ignore[operator]
        print(f"   {label}: accepted")
    except (ValidationError, ValueError) as error:
        first = str(error).splitlines()[0]
        print(f"   {label}: refused ({type(error).__name__}: {first[:60]})")


def unavailable() -> None:
    print("1. Can a record say that a metric is unavailable?")
    refused(
        "ProcessCounters with cpu_s=None",
        lambda: ProcessCounters(key=KEY, cpu_s=None, memory_bytes=1),  # type: ignore[arg-type]
    )
    refused(
        "ProcessCounters with memory_bytes=None",
        lambda: ProcessCounters(key=KEY, cpu_s=1.0, memory_bytes=None),  # type: ignore[arg-type]
    )
    refused(
        "ProcessCounters with io_read_bytes=None",
        lambda: ProcessCounters(key=KEY, cpu_s=1.0, memory_bytes=1, io_read_bytes=None),
    )
    totals = {
        "taken_at": NOW,
        "interval_s": 1.0,
        "workload": "restricted",
        "source": "partial",
        "cpu_s": 0.1,
        "memory_bytes": 1,
        "io_read_bytes": 0,
        "io_write_bytes": 0,
        "processes": 1,
        "started": 0,
    }
    for field in ("io_read_bytes", "memory_bytes"):
        refused(
            f"WorkloadSample with {field}=None",
            lambda f=field: WorkloadSample(**{**totals, f: None}),
        )
    refused(
        "Availability('opaque'), as docs/03 prints for vm.guest", lambda: Availability("opaque")
    )


def fields() -> None:
    print("2. Fields the records have")
    for record in (ProcessCounters, ProcessSample, SampleBatch, SystemCounters, WorkloadSample):
        print(f"   {record.__name__}: {', '.join(record.model_fields)}")
    print(f"   Finding: {', '.join(Finding.model_fields)}")
    have = set(Bucket.model_fields)
    print(f"   Bucket: {', '.join(Bucket.model_fields)}")
    missing = 0
    for row, wanted in CATALOGUE:
        held = [name for name in wanted if name in have]
        missing += not held
        print(f"   catalogue row '{row}': {', '.join(held) if held else 'no Bucket field'}")
    print(f"   {missing} of {len(CATALOGUE)} catalogue rows have no field in Bucket")


def allowed_values() -> None:
    print("3. Values the brief allows")
    choice = choose_tier(
        start=NOW - 45 * DAY,
        end=NOW - 44.5 * DAY,
        now=NOW,
        raw_retention_s=60 * DAY,
        minute_retention_s=30 * DAY,
    )
    print(
        "   retention.raw = 60d (docs/08: 'keep full detail longer'), minute = 30d; a 12-hour "
        f"window 45 days back is answered from the {choice.tier.value} tier, which was deleted "
        "15 days earlier"
    )
    forever = load_settings(overrides={"storage": {"retention": {"raw": "forever"}}})
    retention = forever.settings.storage.retention
    as_text, as_python = retention.model_dump_json(), retention.model_dump(mode="json")
    print(
        f"   retention.raw = 'forever': model_dump_json gives {as_text[:14]}..., and "
        f"model_dump(mode='json') gives raw={as_python['raw']!r}, which json.dumps writes as "
        f"{json.dumps(as_python['raw'])}"
    )


def start_time_three_ways() -> None:
    print("4. One process's start time, three ways (ProcessKey compares this float exactly)")
    stat = Path(f"/proc/{os.getpid()}/stat").read_text(encoding="ascii")
    ticks = int(stat[stat.rfind(")") + 2 :].split()[19])
    hertz = os.sysconf("SC_CLK_TCK")
    boot_line = next(
        line for line in Path("/proc/stat").read_text().splitlines() if line.startswith("btime")
    )
    boot_whole = float(boot_line.split()[1])
    boot_exact = time.time() - time.clock_gettime(time.CLOCK_BOOTTIME)
    library = psutil.Process().create_time()
    whole = ticks / hertz + boot_whole
    exact = ticks / hertz + boot_exact
    print(
        f"   psutil equals ticks/{hertz} + btime: {library == whole}; with boot time taken from "
        f"the two clocks instead of btime the value differs by {abs(exact - library):.3f} s. "
        f"The kernel's own figure is an integer: {ticks > 0} (clock ticks since boot)"
    )
    print(
        "   same pid, same process, unequal keys: "
        f"{ProcessKey(pid=1, started=library) != ProcessKey(pid=1, started=exact)}"
    )


def main() -> None:
    unavailable()
    fields()
    allowed_values()
    start_time_three_ways()


if __name__ == "__main__":
    main()
