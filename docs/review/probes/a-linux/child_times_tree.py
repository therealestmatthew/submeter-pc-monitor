"""Child-time counters in a tree two levels deep, and where orphans' CPU time collects.

Run from the repository root:
    uv run python docs/review/probes/a-linux/child_times_tree.py

Part 1 builds parent -> child -> twelve short grandchildren. The child reaps the grandchildren
and is then reaped by the parent. The probe polls the tree from outside, as a collector would,
and adds the counters (cutime and cstime in /proc/PID/stat) in three ways.
Part 2 reads, for the processes that adopt orphans on this machine, how much CPU time of
other processes has collected in their counters since they started. Names only.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

TICK = os.sysconf("SC_CLK_TCK")
BURN = "x = 0\nfor i in range(1200000): x += i * i"
CHILD = (
    "import subprocess, sys\n"
    "for _ in range(12):\n"
    "    subprocess.run([sys.executable, '-S', '-c', sys.argv[1]])\n"
    "    exec(sys.argv[1])\n"
)
PARENT = (
    "import subprocess, sys\n"
    "child = subprocess.Popen([sys.executable, '-S', '-c', sys.argv[1], sys.argv[2]])\n"
    "print(child.pid, flush=True)\n"
    "child.wait()\n"
    "print('reaped', flush=True)\n"
    "sys.stdin.readline()\n"
)


def read(pid: int) -> tuple[str, int, float, float]:
    """Name, parent pid, own CPU seconds and the child-time counter, from /proc/PID/stat."""
    stat = Path(f"/proc/{pid}/stat").read_text()
    fields = stat[stat.rfind(")") + 2 :].split()
    own = (int(fields[11]) + int(fields[12])) / TICK
    reaped = (int(fields[13]) + int(fields[14])) / TICK
    return stat[stat.find("(") + 1 : stat.rfind(")")], int(fields[1]), own, reaped


def everyone() -> dict[int, tuple[str, int, float, float]]:
    found = {}
    for name in os.listdir("/proc"):
        if name.isdigit():
            try:
                found[int(name)] = read(int(name))
            except OSError:
                continue
    return found


def two_levels() -> None:
    command = [sys.executable, "-S", "-c", PARENT, CHILD, BURN]
    parent = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    assert parent.stdin is not None and parent.stdout is not None
    child = int(parent.stdout.readline())
    os.set_blocking(parent.stdout.fileno(), False)
    last: dict[int, tuple[float, float]] = {}
    seen = counters = ended_own = ended_counter = 0.0
    done = False
    while not done:
        done = bool(parent.stdout.read())
        now = everyone()
        below = {pid: v for pid, v in now.items() if pid == child or v[1] == child}
        watched = below | {parent.pid: now[parent.pid]}
        for pid, (_, _, own, reaped) in watched.items():
            before_own, before_reaped = last.get(pid, (0.0, 0.0))
            seen += own - before_own if pid in below else 0.0
            counters += reaped - before_reaped
        for pid, (own, reaped) in last.items():
            if pid not in watched:
                ended_own += own
                ended_counter += reaped
        last = {pid: (v[2], v[3]) for pid, v in watched.items()}
        time.sleep(0.1)
    truth = read(parent.pid)[3]
    print("1. a parent, its child and twelve grandchildren, polled every 0.1 s")
    print(f"  CPU time used below the parent (its own counter at the end): {truth:.2f} s")
    print(f"  polling alone, each process up to its last sighting:        {seen:.2f} s")
    total = seen + counters
    print(f"  polling plus every counter:                                 {total:.2f} s")
    total -= ended_own
    print(f"  less the last own time of each process that ended:          {total:.2f} s")
    total -= ended_counter
    print(f"  less the last counter of each process that ended as well:   {total:.2f} s")
    parent.stdin.close()
    parent.wait()


def adopters() -> None:
    table = everyone()
    me = os.getuid()
    print("\n2. where the CPU time of reaped children has collected on this machine")
    chosen = {1: "pid 1"}
    for pid, (name, ppid, _, _) in table.items():
        if name == "systemd" and ppid == 1 and os.stat(f"/proc/{pid}").st_uid == me:
            chosen[pid] = "this user's service manager, which adopts this login's orphans"
    for pid, label in chosen.items():
        name, _, own, reaped = table[pid]
        print(f"  {label} ({name}): own {own:,.0f} s, reaped children {reaped:,.0f} s")
    ranked = sorted(table.values(), key=lambda entry: -entry[3])[:6]
    names = ", ".join(f"{name} {reaped:,.0f} s" for name, _, _, reaped in ranked)
    print(f"  the six largest counters: {names}")
    total = sum(entry[3] for entry in table.values())
    own = sum(entry[2] for entry in table.values())
    print(f"  all counters together {total:,.0f} s; all live processes' own time {own:,.0f} s")


if __name__ == "__main__":
    two_levels()
    adopters()
