"""Probe: what "recover reaped children's CPU time from the parent's child-time counters" adds.

docs/17-build-prompt.md asks the Linux provider to recover CPU of reaped children from the
parent's child-time counters. This checks, on Linux, two things that rule depends on:

1. A child that was seen alive: its CPU is in its own counters while it lives, and the whole
   of it lands again in the parent's child-time counters when the parent reaps it.
2. A grandchild orphaned by its parent: it is reaped by a subreaper or init, so its CPU never
   reaches the original parent's child-time counters.

Burns about 0.8 CPU-seconds in short child processes. Writes only to a temporary folder, which
it removes. Run from the repository root:

    uv run python docs/review/probes/e-baseline/children_time.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psutil

BURN = "import time\nend = time.process_time() + {0}\nwhile time.process_time() < end: pass\n"


def child_time() -> float:
    times = psutil.Process().cpu_times()
    return times.children_user + times.children_system


def seen_then_reaped() -> None:
    print("1. A child seen alive, then reaped by this process")
    code = BURN.format(0.4) + "time.sleep(1.0)\n"
    before = child_time()
    child = subprocess.Popen([sys.executable, "-c", code])
    time.sleep(0.8)
    seen = sum(psutil.Process(child.pid).cpu_times()[:2])
    child.wait()
    added = child_time() - before
    print(
        f"   last seen alive with {seen:.2f} CPU-s; the parent's child time then rose by "
        f"{added:.2f} CPU-s; crediting both gives {seen + added:.2f} for {added:.2f} used"
    )


def orphaned_grandchild(folder: Path) -> None:
    print("2. A grandchild whose parent exits first")
    report = folder / "grandchild.txt"
    grand = BURN.format(0.3) + (
        f"import os\nt = os.times()\nopen({str(report)!r}, 'w').write(str(t.user + t.system))\n"
    )
    launcher = (
        f"import subprocess, sys\nsubprocess.Popen([sys.executable, '-c', {grand!r}])\n"
        "sys.exit(0)\n"
    )
    before = child_time()
    subprocess.run([sys.executable, "-c", launcher], check=True)
    for _ in range(50):
        if report.exists() and report.read_text():
            break
        time.sleep(0.1)
    used = float(report.read_text())
    added = child_time() - before
    print(
        f"   the grandchild used {used:.2f} CPU-s; this process's child time rose by "
        f"{added:.2f} CPU-s (the launcher's own start-up only)"
    )


def main() -> None:
    seen_then_reaped()
    with tempfile.TemporaryDirectory() as name:
        orphaned_grandchild(Path(name))


if __name__ == "__main__":
    main()
