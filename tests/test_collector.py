"""Tests for the collector's records, provider and sampler. Run with: uv run pytest"""

from __future__ import annotations

import contextlib
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


def test_windows_memory_is_private_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(psutil, "process_iter", lambda: iter([fake_process(10)]))  # no 'private'
    assert PsutilProvider().snapshot().processes[0].memory_bytes == 300  # vms, not rss


def test_windows_threads_are_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
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
