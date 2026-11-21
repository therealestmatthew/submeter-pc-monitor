"""What one process whose command line is not valid UTF-8 does to the raw file.

Starts one child of this probe whose last argument holds the byte 0xE9 on its own (a Latin-1
"e acute"), takes real snapshots with the baseline provider and sampler, and writes three ticks
through RawFile in a temporary folder. Prints what psutil returned for the child, whether each
write succeeded, and how many system and workload rows reached the file. Then the same three
ticks without that child, as the control. The child is stopped at the end. Linux only.

Run: uv run python docs/review/probes/d-privacy/nonutf8_cmdline.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from submeter.attribution.rules import Attributor, RuleSet, aggregate
from submeter.collector.sampler import Sampler
from submeter.providers.psutil_provider import PsutilProvider
from submeter.store.raw import RawFile


def run(path: Path, skip_pid: int | None) -> None:
    provider, sampler, raw = PsutilProvider(), Sampler(), RawFile(path)
    attributor = Attributor(RuleSet(), self_pid=os.getpid())
    sampler.ingest(provider.snapshot())
    for tick in range(1, 4):
        time.sleep(0.3)
        batch = sampler.ingest(provider.snapshot())
        assert batch is not None
        if skip_pid is not None:
            kept = tuple(p for p in batch.processes if p.key.pid != skip_pid)
            batch = batch.model_copy(update={"processes": kept})
        assignment = attributor.assign(batch.processes)
        workloads = aggregate(batch, assignment)
        names = {key: found.workload for key, found in assignment.items()}
        try:
            raw.write(batch, workloads, names, keyframe=tick == 1)
            outcome = "written"
        except Exception as error:  # the point is to see which error, if any
            outcome = f"FAILED with {type(error).__name__}"
        rows = raw.count("workload_raw")
        print(f"  tick {tick}: {outcome}; workload rows in the file so far: {rows}")
    raw.close()


def main() -> None:
    script = "import time; time.sleep(30)"
    child = subprocess.Popen([sys.executable, "-c", script, b"caf\xe9-FAKE"])
    try:
        time.sleep(0.5)
        import psutil

        last = psutil.Process(child.pid).cmdline()[-1]
        print(f"psutil gives the child's last argument as: {last!r}")
        with tempfile.TemporaryDirectory() as folder:
            print("with the child running:")
            run(Path(folder) / "a.db", None)
            print("control, the same child left out of each batch:")
            run(Path(folder) / "b.db", child.pid)
    finally:
        child.kill()
        child.wait()


if __name__ == "__main__":
    if not sys.platform.startswith("linux"):
        sys.exit("This probe is for Linux.")
    main()
