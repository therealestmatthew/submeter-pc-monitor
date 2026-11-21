"""What a signed-in user may read in /proc, for its own processes and for everyone else's.

Run from the repository root, never as root:
    uv run python docs/review/probes/a-linux/proc_readability.py

It tries each per-process file the design relies on (docs/09-telemetry.md) for every process
and prints counts only. No command line, path or name of a user is printed. Then it runs the
baseline provider and says how many processes it marks restricted, and why.
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))

from submeter.attribution.rules import Attributor, RuleSet
from submeter.collector.sampler import Sampler
from submeter.providers.psutil_provider import PsutilProvider

FILES = ("stat", "statm", "status", "cmdline", "io", "smaps_rollup", "cwd", "exe", "fd")
LINKS = {"cwd", "exe"}
PF_KTHREAD = 0x00200000


def kind_of(pid: int, me: int) -> str | None:
    try:
        owner = os.stat(f"/proc/{pid}").st_uid
        stat = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return None
    flags = int(stat[stat.rfind(")") + 2 :].split()[6])
    if flags & PF_KTHREAD:
        return "kernel thread"
    return "own user" if owner == me else "other user"


def attempt(pid: int, name: str) -> str:
    path = f"/proc/{pid}/{name}"
    try:
        if name in LINKS:
            os.readlink(path)
            return "readable"
        if name == "fd":
            os.listdir(path)
            return "readable"
        with open(path, "rb") as handle:
            return "readable" if handle.read() else "empty"
    except PermissionError:
        return "denied"
    except OSError:
        return "gone"


def main() -> None:
    me = os.getuid()
    print(f"root: {me == 0}; /proc mount options: {mount_options()}")
    print(f"kernel.yama.ptrace_scope = {Path('/proc/sys/kernel/yama/ptrace_scope').read_text()}")
    pids = [int(name) for name in os.listdir("/proc") if name.isdigit()]
    kinds = {pid: kind for pid in pids if (kind := kind_of(pid, me)) is not None}
    print("processes by owner:", dict(Counter(kinds.values())))
    others = {os.stat(f"/proc/{p}").st_uid for p, k in kinds.items() if k == "other user"}
    print(f"distinct other owners: {len(others)} (root among them: {0 in others})\n")

    table: dict[str, dict[str, Counter[str]]] = {}
    for pid, kind in kinds.items():
        for name in FILES:
            table.setdefault(kind, {}).setdefault(name, Counter())[attempt(pid, name)] += 1
    for kind in ("own user", "other user", "kernel thread"):
        print(kind)
        for name in FILES:
            print(f"  {name:<13} {dict(table.get(kind, {}).get(name, {}))}")

    with_args = sum(
        1 for pid, kind in kinds.items() if kind == "other user" and len(arguments(pid)) > 1
    )
    print(f"\nother users' processes whose command line shows arguments: {with_args}")
    hidden = [p for p, k in kinds.items() if k == "own user" and attempt(p, "io") == "denied"]
    root_owned = sum(1 for p in hidden if os.stat(f"/proc/{p}/io").st_uid == 0)
    print(
        f"own-user processes whose io file is denied: {len(hidden)}, of which {root_owned} have "
        "files owned by root (the process gave up being dumpable) and the rest are refused by "
        "another check (a namespace or a security module)"
    )
    baseline(kinds)


def arguments(pid: int) -> list[bytes]:
    try:
        return [part for part in Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0") if part]
    except OSError:
        return []


def mount_options() -> str:
    for line in Path("/proc/mounts").read_text().splitlines():
        fields = line.split()
        if fields[1] == "/proc":
            return fields[3]
    return "not found"


def baseline(kinds: dict[int, str]) -> None:
    """What the baseline provider and the attribution rules make of the same machine."""
    provider, sampler = PsutilProvider(), Sampler()
    sampler.ingest(provider.snapshot())
    snapshot = provider.snapshot()
    batch = sampler.ingest(snapshot)
    assert batch is not None
    restricted = [p for p in snapshot.processes if p.restricted]
    by_kind = Counter(kinds.get(p.key.pid, "started since") for p in restricted)
    print(f"\nbaseline provider: {len(snapshot.processes)} processes, {len(restricted)} restricted")
    print("  restricted by owner:", dict(by_kind))
    print(
        "  restricted with command line read:",
        sum(1 for p in restricted if p.cmdline is not None),
        "| with I/O unread:",
        sum(1 for p in restricted if p.io_read_bytes is None),
        "| with CPU time and memory read:",
        sum(1 for p in restricted if p.cpu_s > 0 or p.memory_bytes > 0),
    )
    total_cpu = sum(p.cpu_s for p in snapshot.processes)
    held = sum(p.cpu_s for p in restricted)
    print(f"  share of all process CPU time since boot held by restricted: {held / total_cpu:.0%}")
    assigned = Attributor(RuleSet()).assign(batch.processes)
    print("  with no rules, workloads are:", dict(Counter(a.workload for a in assigned.values())))
    print(f"  capability line: {provider.capability().status.value}, {provider.capability().note}")


if __name__ == "__main__":
    main()
