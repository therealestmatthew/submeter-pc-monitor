"""Verify G6: a pid that is reused while psutil's process_iter() cache holds the old process.

Reads and measures only. Starts one child, `sleep 6`, and waits for it to end. A reused pid is
imitated the way psutil's own tests imitate it: the cached Process object for the child is
given an older identity and start time, so psutil believes the pid now belongs to a newer
process. Snapshots are spaced 1.1 s apart so the Sampler's "born in this interval" test sees a
real 1-second cadence.

    uv run python docs/review/probes/verify-1/pid_reuse.py
"""

from __future__ import annotations

import subprocess
import time

import psutil
from _helpers import DAY0  # noqa: F401  (puts src on the path)

from submeter.collector.sampler import Sampler
from submeter.providers.psutil_provider import PsutilProvider


def main() -> None:
    child = subprocess.Popen(["sleep", "6"])
    provider, sampler = PsutilProvider(), Sampler()
    try:
        time.sleep(0.2)
        sampler.ingest(provider.snapshot())
        cached = psutil._pmap[child.pid]  # type: ignore[attr-defined]
        cached._ident = (child.pid, cached._ident[1] - 10.0)
        cached._create_time = cached.create_time() - 10.0
        print("a pid psutil believes was reused after snapshot 0")
        for tick in (1, 2, 3):
            time.sleep(1.1)
            snapshot = provider.snapshot()
            batch = sampler.ingest(snapshot)
            assert batch is not None
            mine = [p for p in batch.processes if p.key.pid == child.pid]
            if not mine:
                print(f"   snapshot {tick}: pid missing from the snapshot")
                continue
            p = mine[0]
            print(
                f"   snapshot {tick}: present, first_seen {p.first_seen}, born "
                f"{snapshot.taken_at - p.key.started:.1f} s before this snapshot, credited "
                f"{p.cpu_s:.2f} CPU-s"
            )
    finally:
        child.wait()


if __name__ == "__main__":
    main()
