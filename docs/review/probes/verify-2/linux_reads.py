"""Verify-2 probe (Linux): names, restricted flags and cgroup counters, read once.

Clusters R4, R12 and R13. Reads /proc and /sys/fs/cgroup once, runs one baseline
PsutilProvider snapshot, and prints counts:

- R12: for processes whose /proc/PID/exe is readable, how often psutil's name() (what the
  baseline stores as exe, psutil_provider.py:92) differs from the executable's file name;
- R13: of the processes the baseline marks restricted, how many are kernel threads
  (PF_KTHREAD), how many lack I/O, and how many lack a command line;
- R4: how many cgroups exist and in how many cpu.stat is readable by this user.

Nothing is timed and nothing is written. Prints no user, host or command-line text; process
names appear only as counts and as the first few name/executable pairs. Run from the
repository root:

    uv run python docs/review/probes/verify-2/linux_reads.py
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))

import psutil

from submeter.providers.psutil_provider import PsutilProvider

PF_KTHREAD = 0x00200000


def kernel_thread(pid: int) -> bool:
    try:
        data = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return False
    return bool(int(data[data.rfind(")") + 2 :].split()[6]) & PF_KTHREAD)


def r12() -> None:
    same = differ = unreadable = 0
    examples: list[tuple[str, str]] = []
    for process in psutil.process_iter():
        try:
            name = process.name()
            target = os.readlink(f"/proc/{process.pid}/exe")
        except (OSError, psutil.Error):
            unreadable += 1
            continue
        base = os.path.basename(target).removesuffix(" (deleted)")
        if name == base:
            same += 1
        else:
            differ += 1
            if len(examples) < 6 and (name, base) not in examples:
                examples.append((name, base))
    print(
        f"R12 exe readable: {same + differ}; name() equals the executable's file name: {same}; "
        f"differs: {differ}; exe unreadable: {unreadable}"
    )
    for name, base in examples:
        print(f"    name() {name!r} vs executable {base!r}")


def r13() -> None:
    snapshot = PsutilProvider().snapshot()
    restricted = [p for p in snapshot.processes if p.restricted]
    counts = Counter()
    for p in restricted:
        counts["kernel thread" if kernel_thread(p.key.pid) else "user process"] += 1
        counts["I/O missing"] += p.io_read_bytes is None
        counts["command line missing"] += p.cmdline is None
        counts["CPU above zero"] += p.cpu_s > 0
    kthreads = sum(1 for p in snapshot.processes if kernel_thread(p.key.pid))
    print(
        f"R13 baseline snapshot: {len(snapshot.processes)} processes, {len(restricted)} "
        f"restricted; all kernel threads: {kthreads}"
    )
    print(f"    of the restricted: {dict(counts)}")


def r4() -> None:
    root = Path("/sys/fs/cgroup")
    total = readable = 0
    for folder, _dirs, files in os.walk(root):
        if "cgroup.procs" not in files:
            continue
        total += 1
        try:
            text = (Path(folder) / "cpu.stat").read_text()
        except OSError:
            continue
        readable += text.startswith("usage_usec")
    print(f"R4 cgroups: {total}; cpu.stat readable with usage_usec: {readable}")


def main() -> None:
    print(f"running as root: {os.geteuid() == 0}")
    r12()
    r13()
    r4()


if __name__ == "__main__":
    main()
