"""Verify G8: an unexpected exception from one process's read, and zombie processes.

Reads and measures only. Starts two short children of its own (`sleep 2` and `true`) and reaps
them before it ends. psutil is patched inside this process only.

    uv run python docs/review/probes/verify-1/read_errors.py

1. io_counters() for one child raises what psutil 7.2.2 raises for an empty or malformed
   /proc/PID/io (RuntimeError, ValueError) or a bare OSError: does provider.snapshot() return?
2. A real zombie (exited, not yet reaped): which psutil calls the provider makes succeed, and is
   the process in the provider's snapshot?
"""

from __future__ import annotations

import subprocess
import time

import psutil
from _helpers import DAY0  # noqa: F401  (puts src on the path)

from submeter.providers.psutil_provider import PsutilProvider


def part1() -> None:
    print("1. one process's io_counters() raises; does the whole snapshot survive?")
    child = subprocess.Popen(["sleep", "2"])
    original = psutil.Process.io_counters
    try:
        for error in (
            RuntimeError("/proc/PID/io file was empty"),
            ValueError("field was not found"),
            OSError(5, "Input/output error"),
        ):

            def failing(self: psutil.Process, error: Exception = error) -> object:
                if self.pid == child.pid:
                    raise error
                return original(self)

            psutil.Process.io_counters = failing  # type: ignore[method-assign]
            try:
                snapshot = PsutilProvider().snapshot()
                print(f"   {type(error).__name__}: snapshot returned {len(snapshot.processes)}")
            except Exception as escaped:
                print(f"   {type(error).__name__}: snapshot() raised {type(escaped).__name__}")
    finally:
        psutil.Process.io_counters = original  # type: ignore[method-assign]
        child.wait()


def part2() -> None:
    print("2. a zombie child")
    child = subprocess.Popen(["true"])
    time.sleep(0.3)
    try:
        process = psutil.Process(child.pid)
        print(f"   status {process.status()}")
        for call in ("create_time", "cpu_times", "memory_info", "num_threads", "cmdline"):
            try:
                value = getattr(process, call)()
                print(f"   {call}: ok ({type(value).__name__})")
            except psutil.Error as error:
                print(f"   {call}: {type(error).__name__}")
        for call in ("io_counters", "ppid", "name"):
            try:
                getattr(process, call)()
                print(f"   {call}: ok")
            except psutil.Error as error:
                print(f"   {call}: {type(error).__name__}")
        snapshot = PsutilProvider().snapshot()
        present = any(p.key.pid == child.pid for p in snapshot.processes)
        print(f"   in PsutilProvider().snapshot(): {present}")
    finally:
        child.wait()


if __name__ == "__main__":
    part1()
    part2()
