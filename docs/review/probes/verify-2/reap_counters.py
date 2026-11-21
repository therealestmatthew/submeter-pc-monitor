"""Verify-2 probe (Linux): what a reaped child adds to its parent's CPU and I/O counters.

Clusters R1 and R2. A child burns a fixed amount of CPU and writes 4 MiB to a file in a
temporary folder, then waits. The probe samples itself and the child through the baseline
PsutilProvider and Sampler while the child is alive, then reaps the child and samples again.
It reports, from /proc, the child's last-seen own CPU and I/O, the jump in this process's
child-time counters (cutime + cstime) and in its own /proc/self/io at reaping, and what the
baseline sampler credits to the two processes over the two intervals.

It also starts a launcher that orphans a grandchild, to see whether that grandchild's CPU
reaches this process's child-time counters.

Nothing is timed. Burns about 0.4 CPU-seconds and writes 4 MiB inside a temporary folder,
which is removed. Run from the repository root:

    uv run python docs/review/probes/verify-2/reap_counters.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))

from submeter.collector.sampler import Sampler
from submeter.providers.psutil_provider import PsutilProvider

TICK = os.sysconf("SC_CLK_TCK")
MIB = 1 << 20
CHILD = (
    "import os, sys, time\n"
    "end = time.process_time() + 0.25\n"
    "while time.process_time() < end: pass\n"
    "with open(sys.argv[1], 'wb') as f:\n"
    "    f.write(b'x' * (4 << 20)); f.flush(); os.fsync(f.fileno())\n"
    "print('ready', flush=True)\n"
    "sys.stdin.readline()\n"
)
GRAND = "import time\nend = time.process_time() + 0.15\nwhile time.process_time() < end: pass\n"


def stat_times(pid: int | str) -> tuple[float, float]:
    """Own CPU seconds and reaped children's CPU seconds from /proc/PID/stat."""
    data = Path(f"/proc/{pid}/stat").read_text()
    fields = data[data.rfind(")") + 2 :].split()
    return (int(fields[11]) + int(fields[12])) / TICK, (int(fields[13]) + int(fields[14])) / TICK


def proc_io(pid: int | str) -> dict[str, int]:
    text = Path(f"/proc/{pid}/io").read_text()
    return {k: int(v) for k, v in (line.split(": ") for line in text.splitlines())}


def main() -> None:
    provider, sampler, me = PsutilProvider(), Sampler(), os.getpid()
    with tempfile.TemporaryDirectory() as folder:
        sampler.ingest(provider.snapshot())
        child = subprocess.Popen(
            [sys.executable, "-S", "-c", CHILD, f"{folder}/blob"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        assert child.stdin is not None and child.stdout is not None
        own_0, reaped_0 = stat_times("self")
        io_0 = proc_io("self")
        child.stdout.readline()
        child_own, _ = stat_times(child.pid)
        child_io = proc_io(child.pid)
        first = sampler.ingest(provider.snapshot())
        child.stdin.write("bye\n")
        child.stdin.flush()
        child.wait()
        _, reaped_1 = stat_times("self")
        io_1 = proc_io("self")
        second = sampler.ingest(provider.snapshot())
        assert first is not None and second is not None

        def credit(batch, pid: int) -> tuple[float, float]:
            for p in batch.processes:
                if p.key.pid == pid:
                    return p.cpu_s, (p.io_write_bytes or 0) / MIB
            return 0.0, 0.0

        c_cpu, c_io = credit(first, child.pid)
        m_cpu_1, m_io_1 = credit(first, me)
        m_cpu_2, m_io_2 = credit(second, me)
        print("1. child seen alive by the baseline sampler, then reaped by this process")
        print(
            f"  child last seen: own CPU {child_own:.2f} s, "
            f"write_bytes {child_io['write_bytes'] / MIB:.1f} MiB"
        )
        print(f"  this process's cutime+cstime rose at reaping by {reaped_1 - reaped_0:.2f} s")
        print(
            f"  this process's /proc/self/io rose at reaping by write_bytes "
            f"{(io_1['write_bytes'] - io_0['write_bytes']) / MIB:.1f} MiB, "
            f"wchar {(io_1['wchar'] - io_0['wchar']) / MIB:.1f} MiB"
        )
        print(f"  baseline sampler, interval 1: child cpu {c_cpu:.2f} s, io {c_io:.1f} MiB")
        print(f"  baseline sampler, interval 2: this process io {m_io_2:.1f} MiB (child gone)")
        print(
            f"  I/O a workload holding both is charged: {c_io + m_io_1 + m_io_2:.1f} MiB "
            f"for {child_io['write_bytes'] / MIB:.1f} MiB written"
        )
        print(
            f"  CPU if the child-time increase is added as the brief says: "
            f"{c_cpu + (reaped_1 - reaped_0):.2f} s for {child_own:.2f} s used"
        )
        del own_0, m_cpu_1, m_cpu_2

        before = stat_times("self")[1]
        launcher = (
            f"import subprocess, sys\n"
            f"p = subprocess.Popen([sys.executable, '-S', '-c', {GRAND!r}], "
            f"stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
            f"print(p.pid, flush=True)\n"
        )
        out = subprocess.run(
            [sys.executable, "-S", "-c", launcher], capture_output=True, text=True, check=True
        )
        grand = int(out.stdout.strip())
        last = 0.0
        while Path(f"/proc/{grand}").exists():
            try:
                last = stat_times(grand)[0]
            except OSError:
                break
            time.sleep(0.02)
        print("\n2. a grandchild orphaned by its launcher")
        print(
            f"  grandchild last seen with {last:.2f} s own CPU; this process's child-time "
            f"rose by {stat_times('self')[1] - before:.2f} s (the launcher only)"
        )


if __name__ == "__main__":
    main()
