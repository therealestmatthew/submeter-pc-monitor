"""Read-only re-check of the Linux platform leads in verifier batch 4 (clusters L1-L9).

Run from the repository root, never as root:
    uv run python docs/review/probes/verify-4/linux_platform_readonly.py

It only reads /proc, /sys/fs/cgroup and `systemctl show`, and calls the baseline psutil
provider once. It makes no cgroup, starts no systemd scope, writes nothing, times nothing and
sends nothing anywhere. Counts only: no command line, user name or unit name is printed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))

from submeter.providers.psutil_provider import PsutilProvider

CG = Path("/sys/fs/cgroup")
ME = os.getuid()
MANAGER = CG / "user.slice" / f"user-{ME}.slice" / f"user@{ME}.service"
GB = 1 << 30


def read(path: Path) -> str:
    try:
        return path.read_text().strip()
    except OSError as error:
        return f"<{type(error).__name__}>"


def kv(path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    for line in read(path).splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].isdigit():
            out[parts[0].rstrip(":")] = int(parts[1])
    return out


def delegation() -> None:
    print("L1/L2/L3. where a tagged group can live, and what it passes down")
    for label, group in (
        ("root", CG),
        ("user.slice", CG / "user.slice"),
        ("user-N.slice", MANAGER.parent),
        ("user@N.service", MANAGER),
        ("app.slice", MANAGER / "app.slice"),
    ):
        stat = group.stat()
        procs = (group / "cgroup.procs").stat()
        owner = "this user" if stat.st_uid == ME else f"uid {stat.st_uid}"
        procs_owner = "this user" if procs.st_uid == ME else f"uid {procs.st_uid}"
        down = read(group / "cgroup.subtree_control") or "nothing"
        print(f"  {label:15} owner {owner:9} cgroup.procs {procs_owner:9} passes down: {down}")
    shown = subprocess.run(
        ["systemctl", "show", f"user@{ME}.service", "-p", "Delegate", "-p", "DelegateControllers"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.split()
    print(f"  systemctl show user@N.service: {shown}")
    apps = [child for child in (MANAGER / "app.slice").iterdir() if child.is_dir()]
    print(
        f"  groups directly below app.slice (siblings a delegated scope would affect): {len(apps)}"
    )
    own = read(Path("/proc/self/cgroup")).split("::", 1)[-1]
    here = CG / own.lstrip("/")
    print(
        "  this process's own group passes down:",
        read(here / "cgroup.subtree_control") or "nothing",
    )
    leftover = [p for p in CG.rglob("submeter-probe*")] if MANAGER.exists() else []
    print(f"  probe cgroups left anywhere by earlier reviewers: {len(leftover)}")
    bus = Path(f"/run/user/{ME}/bus")
    print(
        f"  user bus socket present: {bus.exists()}; "
        f"DBUS_SESSION_BUS_ADDRESS set: {'DBUS_SESSION_BUS_ADDRESS' in os.environ}"
    )
    files = sorted(p.name for p in (MANAGER / "app.slice").iterdir() if p.is_file())
    print(f"  io.* files in app.slice: {[f for f in files if f.startswith('io.')]}")
    counters = [f for f in files if any(k in f for k in ("fork", "started", "spawn", "total"))]
    print(f"  files that could count processes started: {counters or 'none'}")
    print(f"  pids.* files: {[f for f in files if f.startswith('pids.')]}")


def group_memory() -> None:
    print("\nL4. what the kernel's memory figure holds, in this user's live leaf groups")
    total = {"current": 0, "anon": 0, "file": 0, "kernel": 0}
    groups = 0
    for events in MANAGER.rglob("cgroup.events"):
        group = events.parent
        if any(child.is_dir() for child in group.iterdir()):
            continue  # leaves only, so nothing is counted twice
        current = read(group / "memory.current")
        if not current.isdigit():
            continue
        stat = kv(group / "memory.stat")
        groups += 1
        total["current"] += int(current)
        for key in ("anon", "file", "kernel"):
            total[key] += stat.get(key, 0)
    share = {k: round(v / total["current"], 2) for k, v in total.items() if k != "current"}
    print(f"  {groups} leaf groups, memory.current {total['current'] / GB:.2f} GB; shares {share}")


def commit() -> None:
    print("\nL5. commit against the commit limit")
    info = kv(Path("/proc/meminfo"))
    mode = read(Path("/proc/sys/vm/overcommit_memory"))
    ratio = info["Committed_AS"] / info["CommitLimit"]
    used = 1 - info["MemAvailable"] / info["MemTotal"]
    print(f"  vm.overcommit_memory {mode}; Committed_AS / CommitLimit {ratio:.2f}")
    print(f"  memory in use (1 - MemAvailable/MemTotal) {used:.2f}")
    print(f"  the built-in rule 'commit_fraction above 0.90' would be: {ratio > 0.90}")


def gpu() -> None:
    print("\nL7. GPU sources")
    drivers = {}
    for card in sorted(Path("/sys/class/drm").glob("card[0-9]")):
        driver = card / "device" / "driver"
        drivers[card.name] = driver.resolve().name if driver.exists() else "?"
        busy = card / "device" / "gpu_busy_percent"
        if busy.exists():
            print(f"  {card.name}: gpu_busy_percent present (device-wide)")
    print(f"  cards and drivers: {drivers}")
    clients, denied_other, other = 0, 0, 0
    for pid_dir in Path("/proc").iterdir():
        if not pid_dir.name.isdigit():
            continue
        try:
            uid = pid_dir.stat().st_uid
        except OSError:
            continue
        try:
            infos = list((pid_dir / "fdinfo").iterdir())
        except OSError:
            if uid != ME:
                denied_other += 1
            continue
        if uid != ME:
            other += 1
        for info in infos:
            try:
                if "drm-client-id" in info.read_text():
                    clients += 1
                    break
            except OSError:
                continue
    print(f"  processes with a DRM client in fdinfo (readable ones): {clients}")
    print(f"  other users' processes: fdinfo denied {denied_other}, readable {other}")


def other_users() -> None:
    print("\nL8. arithmetic only, from the lead's own measured rate (no timing here)")
    sizes = []
    for status in Path("/proc").glob("[0-9]*/status"):
        try:
            if status.parent.stat().st_uid != ME:
                continue
            fields = kv(status)
        except OSError:
            continue
        if "VmRSS" in fields:
            sizes.append(fields["VmRSS"] * 1024)
    top = sorted(sizes, reverse=True)[:25]
    print(
        f"  own processes {len(sizes)}, resident {sum(sizes) / GB:.2f} GB,",
        f"top 25 {sum(top) / GB:.2f} GB",
    )
    for ms_per_gb in (25.1, 29.3):
        cost = ms_per_gb * sum(top) / GB / 30_000
        print(f"  at {ms_per_gb} ms per GB and one round every 30 s: {cost:.2%} of a core")
    print(f"  lead's figure re-derived: 241.6 ms / 30 s = {241.6 / 30_000:.3%}")

    print("\nL9. other users' command lines")
    mounts = [line.split() for line in read(Path("/proc/mounts")).splitlines()]
    options = [m[3] for m in mounts if len(m) > 3 and m[1] == "/proc"]
    print(f"  /proc options: {options}; hidepid set: {any('hidepid' in o for o in options)}")
    with_args = readable = 0
    for cmdline in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            if cmdline.parent.stat().st_uid == ME:
                continue
            raw = cmdline.read_bytes()
        except OSError:
            continue
        if raw:
            readable += 1
            if len([part for part in raw.split(b"\0") if part]) > 1:
                with_args += 1
    print(
        f"  other users' processes with a non-empty command line: {readable};",
        f"with args: {with_args}",
    )
    snapshot = PsutilProvider().snapshot()
    kept = 0
    for counters in snapshot.processes:
        try:
            uid = Path(f"/proc/{counters.key.pid}").stat().st_uid
        except OSError:
            continue
        if uid != ME and counters.cmdline:
            kept += 1
    print(
        f"  baseline provider: {len(snapshot.processes)} processes; "
        f"other users' (root included) handed on with a command line: {kept}"
    )


if __name__ == "__main__":
    delegation()
    group_memory()
    commit()
    gpu()
    other_users()
