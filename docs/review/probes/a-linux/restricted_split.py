"""Which processes would the Restricted bucket hold on Linux, and how much CPU time do they carry?

Run from the repository root, as the signed-in user:
    uv run python docs/review/probes/a-linux/restricted_split.py

Reads /proc/PID/stat and /proc/PID/status for every process, classifies each as own user,
other user or kernel thread (flag PF_KTHREAD in field 9), and sums CPU time since start
(utime + stime) per class. It also counts which classes have a readable /proc/PID/io, which is
what makes the baseline provider mark a process restricted. Reads only; prints counts only.
"""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

PF_KTHREAD = 0x00200000
TICK = os.sysconf("SC_CLK_TCK")


def classify(pid: str) -> tuple[str, float, bool] | None:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        status = Path(f"/proc/{pid}/status").read_text()
    except OSError:
        return None
    fields = stat[stat.rfind(")") + 2 :].split()
    flags, utime, stime = int(fields[6]), int(fields[11]), int(fields[12])
    uid = next(int(line.split()[1]) for line in status.splitlines() if line.startswith("Uid:"))
    if flags & PF_KTHREAD:
        kind = "kernel thread"
    else:
        kind = "own user" if uid == os.getuid() else "other user"
    try:
        Path(f"/proc/{pid}/io").read_bytes()
        io = True
    except OSError:
        io = False
    return kind, (utime + stime) / TICK, io


def main() -> None:
    count: Counter[str] = Counter()
    cpu: Counter[str] = Counter()
    io_denied: Counter[str] = Counter()
    for pid in (entry.name for entry in Path("/proc").iterdir() if entry.name.isdigit()):
        found = classify(pid)
        if found is None:
            continue
        kind, seconds, io = found
        count[kind] += 1
        cpu[kind] += seconds
        io_denied[kind] += not io
    total = sum(cpu.values())
    print("class          processes  io denied  CPU time since start  share")
    for kind in ("own user", "other user", "kernel thread"):
        print(
            f"{kind:<14} {count[kind]:>9}  {io_denied[kind]:>9}  {cpu[kind]:>17,.0f} s"
            f"  {cpu[kind] / total:>5.1%}"
        )
    print(f"kernel threads found by PF_KTHREAD, not by name or parent: {count['kernel thread']}")


if __name__ == "__main__":
    main()
