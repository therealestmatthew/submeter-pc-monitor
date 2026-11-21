"""Probe W8: how many times InstanceLock.acquire() tries the lock before giving up.

Wraps submeter.store.files._try_lock in a counter that always refuses (as Windows would while
it has not yet released a dead holder's lock), calls acquire() once and reports the attempts
and the elapsed wall time bucket (under or over 100 ms; not a measurement). Then writes a pid
file naming a pid that has exited, with no lock held, and reports what holder() returns.
Everything is created inside a temporary folder that is removed afterwards.

Run from the repository root:  uv run python docs/review/probes/verify-3/w8_lock_attempts.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psutil

from submeter.store import files


def main() -> None:
    attempts = {"n": 0}
    original = files._try_lock

    def refuse(fd: int) -> bool:
        attempts["n"] += 1
        return False

    with tempfile.TemporaryDirectory() as name:
        path = Path(name) / "collector.lock"
        files._try_lock = refuse  # type: ignore[assignment]
        try:
            started = time.monotonic()
            took = files.InstanceLock(path).acquire()
            quick = (time.monotonic() - started) < 0.1
        finally:
            files._try_lock = original  # type: ignore[assignment]
        print(f"refused lock: acquire() returned {took} after {attempts['n']} attempt(s); ")
        print(f"returned within 100 ms (no waiting): {quick}")

        dead = subprocess.run(
            [sys.executable, "-c", "import os; print(os.getpid())"],
            capture_output=True,
            text=True,
            check=True,
        )
        dead_pid = int(dead.stdout.strip())
        lock = files.InstanceLock(path)
        lock.pid_file.write_text(str(dead_pid), encoding="ascii")
        print(
            f"pid file left by an exited holder: holder() returns that pid: "
            f"{lock.holder() == dead_pid}; a process with that pid exists now: "
            f"{psutil.pid_exists(dead_pid)}; lock free: {lock.acquire()}"
        )
        lock.release()


if __name__ == "__main__":
    main()
