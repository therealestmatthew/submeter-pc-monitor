"""Tests for the psutil provider: what it reads, and what it reports when a read fails."""

from __future__ import annotations

import contextlib
import ctypes
import os
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import psutil
import pytest
from builders import fake_process

from submeter.attribution.rules import Rule
from submeter.collector.sampler import Sampler
from submeter.providers.psutil_provider import PsutilProvider
from submeter.store.raw import RawFile


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
