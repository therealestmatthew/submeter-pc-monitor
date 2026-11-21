"""What one read of /proc/PID/smaps_rollup costs, and how PSS, USS, RSS and cgroup memory relate.

Run from the repository root, never as root:
    uv run python docs/review/probes/a-linux/smaps_cost.py

Cost is the CPU time this process is charged for the read (the kernel walks the target's page
tables on the reader's account), best of three, not wall time. The second half adds up the
three memory units over this user's processes and sets them beside the kernel's own figures
for the cgroups those processes live in. It reads only, and prints names of units, not paths.
"""

from __future__ import annotations

import os
import re
import time
from collections import defaultdict
from pathlib import Path

ME = os.getuid()
PAGE = os.sysconf("SC_PAGE_SIZE")
GB = 2**30


def read(path: str) -> bytes:
    handle = os.open(path, os.O_RDONLY)
    try:
        return os.read(handle, 1 << 16)
    finally:
        os.close(handle)


def cost_us(path: str) -> float:
    best = float("inf")
    for _ in range(3):
        started = time.process_time_ns()
        read(path)
        best = min(best, (time.process_time_ns() - started) / 1000)
    return best


def rollup(pid: int) -> dict[str, int]:
    """Field name to bytes, from smaps_rollup, plus RssAnon from the cheap status file."""
    lines = read(f"/proc/{pid}/smaps_rollup").decode().splitlines()[1:]
    lines += [x for x in read(f"/proc/{pid}/status").decode().splitlines() if "RssAnon" in x]
    return {line.split(":")[0]: int(line.split()[1]) * 1024 for line in lines}


def own_processes() -> dict[int, dict[str, int]]:
    found = {}
    for name in os.listdir("/proc"):
        if name.isdigit() and os.stat(f"/proc/{name}").st_uid == ME:
            try:
                found[int(name)] = rollup(int(name))
            except OSError:
                continue
    return found


def costs(processes: dict[int, dict[str, int]]) -> None:
    ranked = sorted(processes, key=lambda pid: -processes[pid]["Rss"])
    each = {}
    for pid in ranked:
        try:
            each[pid] = cost_us(f"/proc/{pid}/smaps_rollup"), cost_us(f"/proc/{pid}/status")
        except OSError:
            continue
    ranked = [pid for pid in ranked if pid in each]
    top = ranked[:25]
    print(f"1. CPU time charged to the reader, {len(ranked)} processes of this user")
    for pid in ranked[:3]:
        rss = processes[pid]["Rss"] / GB
        print(
            f"  resident {rss:.2f} GB: smaps_rollup {each[pid][0]:,.0f} us "
            f"({each[pid][0] / 1000 / rss:.1f} ms per GB), status {each[pid][1]:.0f} us"
        )
    for label, chosen in (("the 25 largest", top), (f"all {len(ranked)}", ranked)):
        total = sum(each[pid][0] for pid in chosen) / 1000
        print(
            f"  smaps_rollup for {label}: {total:.1f} ms a round, which at one round every 30 s "
            f"is {total / 300:.3f}% of a core, and every 1 s is {total / 10:.1f}%"
        )
    status = sum(each[pid][1] for pid in ranked) / 1000
    print(f"  status for all {len(ranked)}: {status:.1f} ms a round")
    pss = sum(processes[pid]["Pss"] for pid in ranked)
    held = sum(processes[pid]["Pss"] for pid in top)
    print(f"  the 25 largest hold {held / pss:.0%} of the proportional memory of all {len(ranked)}")


def units(processes: dict[int, dict[str, int]]) -> None:
    def total(pids: list[int], *fields: str) -> float:
        return sum(processes[pid].get(field, 0) for pid in pids for field in fields) / GB

    def line(label: str, pids: list[int]) -> str:
        return (
            f"  {label}: {len(pids)} processes, RSS {total(pids, 'Rss'):.2f}, "
            f"PSS {total(pids, 'Pss'):.2f}, USS "
            f"{total(pids, 'Private_Clean', 'Private_Dirty'):.2f}, "
            f"anonymous RSS {total(pids, 'RssAnon'):.2f}, swap {total(pids, 'Swap'):.2f} GB"
        )

    print("\n2. the same processes in four units")
    print(line("all of this user's", list(processes)))
    groups = defaultdict(list)
    for pid in processes:
        try:
            groups[Path(f"/proc/{pid}/cgroup").read_text().strip()[3:]].append(pid)
        except OSError:
            continue
    largest = sorted(groups, key=lambda path: -total(groups[path], "Rss"))[:3]
    print("\n3. the three largest cgroups of this user, processes against the kernel's figures")
    for path in largest:
        group = Path("/sys/fs/cgroup" + path)
        name = re.sub(r"[0-9a-f]{8}-[0-9a-f-]{27}|\d{3,}", "N", group.name)
        print(line(name, groups[path]))
        try:
            stat = dict(line.split() for line in (group / "memory.stat").read_text().splitlines())
            current = int((group / "memory.current").read_text()) / GB
            peak = int((group / "memory.peak").read_text()) / GB
            swap = int((group / "memory.swap.current").read_text()) / GB
        except OSError:
            print("    the cgroup has no memory files")
            continue
        parts = {key: int(stat[key]) / GB for key in ("anon", "file", "shmem", "kernel")}
        print(
            f"    kernel: memory.current {current:.2f}, memory.peak {peak:.2f}, swap {swap:.2f}; "
            f"of current: anon {parts['anon']:.2f}, file {parts['file']:.2f} "
            f"(shmem {parts['shmem']:.2f}), kernel {parts['kernel']:.2f} GB"
        )


if __name__ == "__main__":
    mine = own_processes()
    costs(mine)
    units(mine)
