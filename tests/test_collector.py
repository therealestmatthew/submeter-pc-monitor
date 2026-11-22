"""Tests for the collector's records, provider and sampler. Run with: uv run pytest"""

from __future__ import annotations

import contextlib
import ctypes
import itertools
import os
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

import psutil
import pytest
from pydantic import ValidationError

from submeter.attribution.rules import Rule
from submeter.collector.sampler import Sampler
from submeter.core import models
from submeter.core.models import ProcessCounters, ProcessKey, ProcessSample
from submeter.providers.psutil_provider import PsutilProvider
from submeter.store.raw import RawFile

SECRET = "sk-abcdefghijklmnopqrstu"


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


# ---- records ---------------------------------------------------------------------------------
def test_reprs_leave_out_the_command_line() -> None:
    cmdline = ("tool", "--api-key", SECRET)
    counters = ProcessCounters(
        key=ProcessKey(pid=1, started=1.0), cmdline=cmdline, cwd=SECRET, cpu_s=0.0, memory_bytes=0
    )
    assert SECRET not in repr(counters) and SECRET not in str(counters)
    assert not any(ProcessSample.model_fields[name].repr for name in ("cmdline", "cwd"))


def test_validation_errors_leave_out_the_command_line() -> None:
    with pytest.raises(ValidationError) as caught:
        ProcessCounters.model_validate(
            {"key": {"pid": 1, "started": 1.0}, "cwd": ("x", SECRET), "cpu_s": 0, "memory_bytes": 0}
        )
    assert SECRET not in str(caught.value)


def test_counters_carry_an_optional_child_time() -> None:
    key = ProcessKey(pid=1, started=1.0)
    assert ProcessCounters(key=key, cpu_s=0.0, memory_bytes=0).children_cpu_s is None
    counters = ProcessCounters(key=key, cpu_s=0.0, memory_bytes=0, children_cpu_s=2.5)
    assert counters.children_cpu_s == 2.5


# ---- provider --------------------------------------------------------------------------------
def test_failed_reads_keep_the_process(monkeypatch: pytest.MonkeyPatch) -> None:
    fakes = [
        fake_process(10, io_counters=OSError(5, "Input/output error"), cwd=ValueError("x")),
        fake_process(11, cmdline=psutil.ZombieProcess(11)),
        fake_process(12, cpu_times=RuntimeError("/proc/PID/stat was empty")),
    ]
    monkeypatch.setattr(psutil, "process_iter", lambda: iter(fakes))
    io_error, zombie, broken = PsutilProvider(read_cwd=True).snapshot().processes
    assert io_error.cpu_s == zombie.cpu_s == 1.5 and broken.restricted
    assert io_error.io_read_bytes is None and io_error.cwd is None and zombie.cmdline is None


def test_a_failed_cpu_read_is_no_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    fake, sampler = fake_process(42), Sampler()
    fake.cpu_times.side_effect = [SimpleNamespace(user=500.0, system=0.0), RuntimeError("x")] * 2
    monkeypatch.setattr(psutil, "process_iter", lambda: iter([fake]))
    *_, batch = (sampler.ingest(PsutilProvider().snapshot()) for _ in range(3))
    assert batch is not None and batch.processes[0].cpu_s == 0.0  # not its lifetime 500 s


def test_windows_memory_is_private_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "windll", mock.Mock(), raising=False)  # its clock reads 0
    monkeypatch.setattr(psutil, "process_iter", lambda: iter([fake_process(10)]))  # no 'private'
    assert PsutilProvider().snapshot().processes[0].memory_bytes == 300  # vms, not rss


def test_windows_threads_are_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "windll", mock.Mock(), raising=False)  # its clock reads 0
    fake = fake_process(10)
    monkeypatch.setattr(psutil, "process_iter", lambda: iter([fake]))
    provider, sampler = PsutilProvider(), Sampler()
    sampler.ingest(provider.snapshot())
    batch = sampler.ingest(provider.snapshot())
    assert batch is not None and batch.processes[0].threads is None
    fake.num_threads.assert_not_called()
    raw = RawFile(tmp_path / "raw.db")
    raw.write(batch, (), {}, keyframe=True)
    raw.close()
    with contextlib.closing(sqlite3.connect(tmp_path / "raw.db")) as db:
        assert db.execute("SELECT threads FROM process_raw").fetchall() == [(None,)]


def test_another_users_command_line_is_not_kept_on_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    # A Windows host has no clock_gettime, so the Linux clocks get a stand-in.
    monkeypatch.setattr("submeter.providers.psutil_provider._clocks", lambda: (0.0, None))
    monkeypatch.setattr(os, "getuid", lambda: 1000, raising=False)
    own, other = (
        fake_process(pid, uids=SimpleNamespace(real=uid)) for pid, uid in [(1, 1000), (2, 0)]
    )
    monkeypatch.setattr(psutil, "process_iter", lambda: iter([own, other]))
    mine, theirs = PsutilProvider().snapshot().processes
    assert mine.cmdline == ("tool",) and not mine.restricted
    assert theirs.cmdline is None and theirs.restricted


def test_exe_is_the_executable_file_and_name_is_kept_apart(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = fake_process(1, exe="/usr/bin/python3.12", name="pytest")
    monkeypatch.setattr(psutil, "process_iter", lambda: iter([fake]))
    provider, sampler = PsutilProvider(), Sampler()
    sampler.ingest(provider.snapshot())
    batch = sampler.ingest(provider.snapshot())
    assert batch is not None and batch.processes[0].exe == "python3.12"
    assert batch.processes[0].name == "pytest"
    assert Rule(workload="x", exe=("python3*",)).matches(batch.processes[0])
    assert Rule(workload="y", name=("pytest",)).matches(batch.processes[0])


def test_windows_idle_process_is_not_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "windll", mock.Mock(), raising=False)  # its clock reads 0
    idle = fake_process(
        0, name="System Idle Process", cpu_times=SimpleNamespace(user=0, system=9e4)
    )
    monkeypatch.setattr(psutil, "process_iter", lambda: iter([idle, fake_process(10)]))
    assert [p.key.pid for p in PsutilProvider().snapshot().processes] == [10]


# ---- sampler ---------------------------------------------------------------------------------
def tick(
    wall: float, clock: float, awake: float | None, *processes: ProcessCounters
) -> models.Snapshot:
    system = models.SystemCounters(
        logical_cores=4, cpu_busy_s=(clock,), memory_total_bytes=0, memory_available_bytes=0
    )
    return models.Snapshot(
        taken_at=wall, monotonic=clock, awake=awake, processes=processes, system=system
    )


def test_suspend_is_told_by_the_clock_that_stops_not_by_the_wall_clock() -> None:
    sampler = Sampler()
    sampler.ingest(tick(10_000, 100, 100))
    asleep = sampler.ingest(tick(6_400, 104, 101))  # 3 s asleep; wall clock stepped back an hour
    awake = sampler.ingest(tick(6_501, 105, 102))  # both clocks agree; wall clock stepped ahead
    assert asleep is not None and asleep.gap
    assert awake is not None and not awake.gap


def test_a_gap_is_past_three_expected_intervals_and_keeps_its_cpu() -> None:
    def counters(cpu: float) -> ProcessCounters:
        return ProcessCounters(key=ProcessKey(pid=1, started=0.0), cpu_s=cpu, memory_bytes=0)

    sampler = Sampler()
    sampler.ingest(tick(1000, 100, 100, counters(5.0)), expected_s=60)
    slow = sampler.ingest(tick(1060.05, 160.05, 160.05, counters(6.0)), expected_s=60)
    stall = sampler.ingest(tick(1095.05, 195.05, 195.05, counters(9.0)))  # 35 s at a 1 s cadence
    assert slow is not None and not slow.gap
    assert stall is not None and stall.gap and stall.cpu_busy_s == pytest.approx(35.0)
    assert stall.processes[0].cpu_s == 3.0
