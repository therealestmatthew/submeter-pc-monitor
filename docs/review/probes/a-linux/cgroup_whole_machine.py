"""What the cgroup tree already accounts for, untagged, and what a signed-in user may read of it.

Run from the repository root, never as root:
    uv run python docs/review/probes/a-linux/cgroup_whole_machine.py [SECONDS]

Part 1 walks /sys/fs/cgroup and counts which accounting files exist and are readable, inside
and outside the subtree delegated to this user. Part 2 runs one spawner of short-lived
children for a few seconds and compares four totals over the same window: the machine's busy
time from /proc/stat, the root cgroup's cpu.stat, the sum over every process polled once a
second from /proc, and the cpu.stat of the one cgroup that held the spawner.
The only cgroup made is an empty-handed one for the spawner (no controller, no limit), and it
is removed at the end.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/sys/fs/cgroup")
ME = os.getuid()
MANAGER = ROOT / "user.slice" / f"user-{ME}.slice" / f"user@{ME}.service"
TICK = os.sysconf("SC_CLK_TCK")
FILES = ("cpu.stat", "memory.current", "memory.peak", "io.stat", "pids.current", "cgroup.procs")
JOIN = 'echo $$ > "$0/cgroup.procs" && exec "$@"'
SPAWNER = (
    "import os, sys, time\n"
    "end, cpu, count = time.monotonic() + float(sys.argv[1]), 0.0, 0\n"
    "code = 'sum(i * i for i in range(600_000))'\n"
    "while time.monotonic() < end:\n"
    "    pid = os.posix_spawn(sys.executable, [sys.executable, '-S', '-c', code], os.environ)\n"
    "    _, _, usage = os.wait4(pid, 0)\n"
    "    cpu += usage.ru_utime + usage.ru_stime; count += 1\n"
    "print(cpu, count)"
)


def readable(path: Path) -> bool:
    try:
        path.read_bytes()
        return True
    except OSError:
        return False


def census() -> None:
    there: dict[str, Counter[str]] = {"delegated to this user": Counter(), "elsewhere": Counter()}
    groups = Counter[str]()
    leaves = 0
    for folder, children, files in os.walk(ROOT):
        where = "delegated to this user" if Path(folder).is_relative_to(MANAGER) else "elsewhere"
        groups[where] += 1
        leaves += not children
        for name in FILES:
            if name in files:
                there[where][f"{name} present"] += 1
                there[where][f"{name} readable"] += readable(Path(folder) / name)
    print(f"1. {sum(groups.values())} cgroups on this machine, {leaves} of them leaves")
    for where, counts in there.items():
        print(f"  {where}: {groups[where]} cgroups")
        for name in FILES:
            print(f"    {name:<15} present in {counts[f'{name} present']:>3}, readable in "
                  f"{counts[f'{name} readable']:>3}")  # fmt: skip
    kinds = Counter(
        "scope" if child.name.endswith(".scope") else child.name.rsplit(".", 1)[-1]
        for child in (MANAGER / "app.slice").iterdir()
        if child.is_dir()
    )
    print(f"  directly below this user's app.slice: {dict(kinds)}")


def busy() -> tuple[float, float]:
    """Machine busy seconds, and the part of it spent in interrupts, from /proc/stat."""
    fields = [int(part) for part in Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
    user, nice, system, _idle, _iowait, irq, softirq, steal = fields[:8]
    return (user + nice + system + irq + softirq + steal) / TICK, (irq + softirq) / TICK


def usage(group: Path) -> float:
    return int((group / "cpu.stat").read_text().split()[1]) / 1e6


def processes() -> dict[tuple[int, int], float]:
    """(pid, start ticks) to CPU seconds for every process, read from /proc/PID/stat."""
    found: dict[tuple[int, int], float] = {}
    for name in os.listdir("/proc"):
        if name.isdigit():
            try:
                stat = Path(f"/proc/{name}/stat").read_text()
            except OSError:
                continue
            fields = stat[stat.rfind(")") + 2 :].split()
            found[(int(name), int(fields[19]))] = (int(fields[11]) + int(fields[12])) / TICK
    return found


def reconcile(seconds: int) -> None:
    group = Path("/sys/fs/cgroup" + Path("/proc/self/cgroup").read_text().strip()[3:])
    group = group / f"submeter-probe-m-{os.getpid()}"
    group.mkdir()
    try:
        command = [sys.executable, "-S", "-c", SPAWNER, str(seconds - 1.5)]
        spawner = subprocess.Popen(
            ["/bin/sh", "-c", JOIN, str(group), *command], stdout=subprocess.PIPE, text=True
        )
        time.sleep(0.5)
        busy_0, root_0 = busy(), usage(ROOT)
        top_0 = {child: usage(child) for child in ROOT.iterdir() if child.is_dir()}
        last, last_at, polled = processes(), time.clock_gettime(time.CLOCK_BOOTTIME), 0.0
        for _ in range(seconds):
            time.sleep(1.0)
            now, now_at = processes(), time.clock_gettime(time.CLOCK_BOOTTIME)
            for key, cpu in now.items():
                if key in last:
                    polled += cpu - last[key]
                elif key[1] / TICK >= last_at:
                    polled += cpu
            last, last_at = now, now_at
        busy_1, root_1 = busy(), usage(ROOT)
        top = sum(usage(child) - before for child, before in top_0.items() if child.exists())
        assert spawner.stdout is not None
        reaped, count = spawner.stdout.read().split()
        spawner.wait()
        held = usage(group)
    finally:
        group.rmdir()
    total, interrupts = busy_1[0] - busy_0[0], busy_1[1] - busy_0[1]
    root = root_1 - root_0
    print(f"\n2. {seconds} s with one spawner of short-lived children ({count} of them)")
    print(f"  machine busy, /proc/stat:                 {total:6.2f} CPU-s")
    print(f"    of which interrupts (irq + softirq):    {interrupts:6.2f}")
    print(f"  root cgroup cpu.stat:                     {root:6.2f}  (the same counters)")
    print(f"  sum of cpu.stat over the top-level cgroups: {top:5.2f}  (every task, exited or not)")
    print(
        f"  every process polled from /proc at 1 s:   {polled:6.2f}  ({polled / top:.0%} of that)"
    )
    print(f"    not seen by polling:                    {top - polled:6.2f}")
    print(f"  cpu.stat of the cgroup that held the spawner, whole run: {held:5.2f}")
    print(f"    its children, from wait4 as they ended:                {float(reaped):5.2f}")
    print(f"  probe cgroup removed: {not group.exists()}")


if __name__ == "__main__":
    census()
    reconcile(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
