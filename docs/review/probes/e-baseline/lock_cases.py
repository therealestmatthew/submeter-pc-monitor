"""Probe: what the one-instance lock leaves behind when its holder is killed.

Starts one child of its own that takes the lock in a temporary folder, kills that child, and
looks at the lock and at the pid file beside it. Run from the repository root:

    uv run python docs/review/probes/e-baseline/lock_cases.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psutil

from submeter.store.files import InstanceLock

HOLD = (
    "import sys, time; from pathlib import Path; from submeter.store.files import InstanceLock; "
    "lock = InstanceLock(Path(sys.argv[1])); print(lock.acquire(), flush=True); time.sleep(60)"
)


def main() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as name:
        path = Path(name) / "collector.lock"
        holder = subprocess.Popen(
            [sys.executable, "-c", HOLD, str(path)], stdout=subprocess.PIPE, text=True
        )
        assert holder.stdout is not None and holder.stdout.readline().strip() == "True"
        lock = InstanceLock(path)
        recorded = lock.pid_file.read_text(encoding="ascii")
        print(f"while held: holder() is the child: {lock.holder() == holder.pid}")
        print(f"pid file holds a pid and nothing else: {recorded.strip().isdigit()}")
        holder.kill()
        holder.wait()
        time.sleep(0.5)
        stale = lock.holder()
        print(
            f"after the holder is killed: holder() still returns its pid: {stale == holder.pid}; "
            f"a process with that pid exists: {psutil.pid_exists(holder.pid)}"
        )
        took = lock.acquire()
        print(f"the lock itself is free again: {took}")
        lock.release()
        print(f"after a clean release the pid file is gone: {not lock.pid_file.exists()}")


if __name__ == "__main__":
    main()
