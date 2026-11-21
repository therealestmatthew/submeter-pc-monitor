"""After the lock holder is killed, what does InstanceLock.holder() still say?

Run:  uv run python docs/review/probes/d-privacy/stale_pid.py

`submeter daemon stop` has to find the running collector, and NAME.pid is the only handle the
baseline offers. The probe starts a child that takes the lock, kills that child (its own child
and nothing else), then asks the baseline who holds the lock. It works in a temporary folder.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import psutil

from submeter.store.files import InstanceLock

HOLD = (
    "import sys, time; from pathlib import Path; from submeter.store.files import InstanceLock; "
    "print(InstanceLock(Path(sys.argv[1])).acquire(), flush=True); time.sleep(60)"
)


def main() -> None:
    with tempfile.TemporaryDirectory() as name:
        path = Path(name) / "collector.lock"
        child = subprocess.Popen(
            [sys.executable, "-c", HOLD, str(path)], stdout=subprocess.PIPE, text=True
        )
        assert child.stdout is not None
        took = child.stdout.readline().strip()
        lock = InstanceLock(path)
        print(
            f"child took the lock: {took}; holder() names the child: {lock.holder() == child.pid}"
        )
        child.kill()
        child.wait()
        child.stdout.close()
        recorded = lock.holder()
        print(f"after the child was killed, holder() still names it: {recorded == child.pid}")
        print(f"a process with that pid exists now: {psutil.pid_exists(child.pid)}")
        print(f"the pid file holds only: {lock.pid_file.read_text()!r} (no start time)")
        print(f"the lock itself is free again: {lock.acquire()}")
        lock.release()


if __name__ == "__main__":
    main()
