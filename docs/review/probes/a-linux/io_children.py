"""Does a parent's /proc/PID/io include the I/O of the children it has reaped?

Run from the repository root:
    uv run python docs/review/probes/a-linux/io_children.py

A child writes 32 MB to a file in a temporary folder. The probe reads the child's io file and
its own before the write, after it, and after reaping the child. The same three moments are
fed through the baseline provider and sampler, to see what the two processes add up to there.
A second run puts a shell that only waits between the probe and the writer.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))

from submeter.collector.sampler import Sampler
from submeter.core.models import SampleBatch
from submeter.providers.psutil_provider import PsutilProvider

MB = 1 << 20
WRITER = (
    "import os, sys\n"
    "sys.stdin.readline()\n"
    "with open(sys.argv[1], 'wb') as f:\n"
    "    for _ in range(32): f.write(b'x' * (1 << 20))\n"
    "    f.flush(); os.fsync(f.fileno())\n"
    "print('written', flush=True)\n"
    "sys.stdin.readline()\n"
)


def io(pid: int | str) -> dict[str, int]:
    text = Path(f"/proc/{pid}/io").read_text()
    return {key: int(number) for key, number in (line.split(": ") for line in text.splitlines())}


def grew(now: dict[str, int], before: dict[str, int]) -> str:
    return ", ".join(
        f"{key} +{(now[key] - before[key]) / MB:.1f} MB" for key in ("wchar", "write_bytes")
    )


def written(batch: SampleBatch | None, pids: set[int]) -> dict[int, float]:
    assert batch is not None
    return {
        process.key.pid: (process.io_write_bytes or 0) / MB
        for process in batch.processes
        if process.key.pid in pids
    }


def main() -> None:
    provider, sampler, me = PsutilProvider(), Sampler(), os.getpid()
    with tempfile.TemporaryDirectory() as folder:
        child = subprocess.Popen(
            [sys.executable, "-S", "-c", WRITER, f"{folder}/blob"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        assert child.stdin is not None and child.stdout is not None
        pids = {me, child.pid}
        sampler.ingest(provider.snapshot())
        mine_0, child_0 = io("self"), io(child.pid)

        child.stdin.write("write\n")
        child.stdin.flush()
        child.stdout.readline()
        mine_1, child_1 = io("self"), io(child.pid)
        first = written(sampler.ingest(provider.snapshot()), pids)

        child.stdin.write("exit\n")
        child.stdin.flush()
        child.wait()
        mine_2 = io("self")
        second = written(sampler.ingest(provider.snapshot()), pids)

        print("1. the child wrote 32 MB, then exited and was reaped by this probe")
        print(f"  child while alive, after writing: {grew(child_1, child_0)}")
        print(f"  this probe before reaping the child: {grew(mine_1, mine_0)}")
        print(f"  this probe after reaping the child:  {grew(mine_2, mine_1)}")
        print("  baseline sampler, write_bytes deltas for the two processes:")
        wrote = first.get(child.pid, 0)
        print(
            f"    interval in which the child wrote: child {wrote:.1f} MB, probe {first[me]:.1f} MB"
        )
        print(f"    interval in which it was reaped:   probe {second[me]:.1f} MB (child gone)")
        total = sum(first.values()) + sum(second.values())
        print(f"    a workload holding both is charged {total:.1f} MB for 32 MB written")

        before = io("self")
        script = f'echo go | {sys.executable} -S -c "$0" {folder}/blob2 >/dev/null; exit 0'
        subprocess.run(["/bin/sh", "-c", script, WRITER.replace("sys.stdin.readline()\n", "", 2)])
        print("\n2. the same writer started by a shell that only waits for it")
        print(f"  this probe after reaping the shell: {grew(io('self'), before)}")


if __name__ == "__main__":
    main()
