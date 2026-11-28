"""Record builders and helpers shared by the component test files.

Each builder moved here unchanged from the test file that held it. Where two copies shared a
name, the copy from the store tests carries the suffix ``_store``.
"""

from __future__ import annotations

import contextlib
import itertools
import os
from collections.abc import Mapping
from types import SimpleNamespace
from typing import Any
from unittest import mock

from submeter.attribution.rules import Attribution
from submeter.core.models import (
    ProcessCounters,
    ProcessKey,
    ProcessSample,
    SampleBatch,
    Snapshot,
    SystemCounters,
    WorkloadSample,
)

MB = 1024**2
DAY0 = 1_795_132_800.0  # 2026-11-20 00:00:00 UTC
HOUR = 3600.0
SECRET = "sk-abcdefghijklmnopqrstu"


# ---- snapshots, from the baseline tests ------------------------------------------------------
def proc(
    pid: int, cpu: float, *, started: float = 100.0, parent: int | None = None, **extra: object
) -> ProcessCounters:
    fields: dict[str, object] = {"exe": "tool", "cmdline": ("tool",), "memory_bytes": 50 * MB}
    fields.update(extra)
    return ProcessCounters(
        key=ProcessKey(pid=pid, started=started), parent_pid=parent, cpu_s=cpu, **fields
    )


def snap(
    at: float, processes: list[ProcessCounters], busy: float = 0.0, mono: float | None = None
) -> Snapshot:
    system = SystemCounters(
        logical_cores=4,
        cpu_busy_s=(busy, 0.0, 0.0, 0.0),
        memory_total_bytes=16 * 1024**3,
        memory_available_bytes=8 * 1024**3,
    )
    return Snapshot(
        taken_at=at,
        monotonic=at if mono is None else mono,
        processes=tuple(processes),
        system=system,
    )


def workload(
    at: float, cpu: float, memory: int = 100 * MB, name: str = "agents", interval: float = 1.0
) -> WorkloadSample:
    return WorkloadSample(
        taken_at=at,
        interval_s=interval,
        workload=name,
        source="polled",
        cpu_s=cpu,
        memory_bytes=memory,
        io_read_bytes=0,
        io_write_bytes=0,
        processes=1,
        started=0,
    )


# ---- batches, from the store tests -----------------------------------------------------------
def workload_store(at: float, cpu: float, interval: float, **extra: object) -> WorkloadSample:
    fields: dict[str, object] = {"workload": "steady", "source": "polled", "memory_bytes": 100}
    fields |= {"io_read_bytes": 0, "io_write_bytes": 0, "processes": 1, "started": 0, **extra}
    return WorkloadSample(taken_at=at, interval_s=interval, cpu_s=cpu, **fields)


def batch(at: float, interval: float, **extra: object) -> SampleBatch:
    fields: dict[str, object] = {"gap": False, "processes": (), "exited": (), "logical_cores": 8}
    fields |= {"cpu_busy_s": 0.0, "memory_available_bytes": 1, **extra}
    return SampleBatch(taken_at=at, interval_s=interval, **fields)


def process(pid: int, cpu: float, **extra: object) -> ProcessSample:
    fields: dict[str, object] = {"exe": "tool", "cmdline": ("tool",), "cwd": None, "threads": 1}
    fields |= {"parent_pid": None, "io_read_bytes": 0, "io_write_bytes": 0, "memory_bytes": 100}
    fields |= {"first_seen": True, "restricted": False, **extra}
    return ProcessSample(key=ProcessKey(pid=pid, started=1.0), cpu_s=cpu, **fields)


# ---- samples, from the attribution tests -----------------------------------------------------
def sample(pid: int, exe: str, parent: int | None = None, **extra: object) -> ProcessSample:
    """A process started at 100 + pid, so a lower pid is always the older process."""
    key = ProcessKey(pid=pid, started=100.0 + pid)
    fields: dict[str, object] = {"key": key, "parent_pid": parent, "exe": exe, "cmdline": (exe,)}
    fields |= {"cwd": None, "cpu_s": 0.0, "io_read_bytes": 0, "io_write_bytes": 0, "threads": 1}
    fields |= {"memory_bytes": MB, "first_seen": False, "restricted": False}
    return ProcessSample.model_validate(fields | extra)


def names(assignment: Mapping[ProcessKey, Attribution]) -> dict[int, str]:
    return {key.pid: value.workload for key, value in assignment.items()}


# ---- psutil stand-in, from the collector tests -----------------------------------------------
def fake_process(pid: int, **reads: object) -> Any:
    """A stand-in for psutil.Process. A read whose value is an exception raises it."""
    reads = {
        "create_time": 100.0,
        "cpu_times": SimpleNamespace(user=1.0, system=0.5),
        "memory_info": SimpleNamespace(rss=100, vms=300),
        "num_threads": 3,
        "cmdline": ["tool"],
        "cwd": "/work",
        "ppid": 1,
        "name": "tool",
        "exe": "/usr/bin/tool",
        "uids": SimpleNamespace(real=getattr(os, "getuid", lambda: 0)()),
    } | reads
    calls = {name: mock.Mock(side_effect=itertools.repeat(value)) for name, value in reads.items()}
    process = mock.NonCallableMock([*reads, "pid", "oneshot"], oneshot=contextlib.nullcontext)
    process.configure_mock(pid=pid, **calls)  # configure_mock, because Mock(name=) is its label
    return process
