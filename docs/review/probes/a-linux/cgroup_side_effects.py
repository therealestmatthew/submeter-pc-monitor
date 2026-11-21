"""Does putting a tagged tree into its own cgroup change how the machine schedules anything?

Run from the repository root, never as root:
    uv run python docs/review/probes/a-linux/cgroup_side_effects.py

Part 1 asks the user's own systemd for three short scopes (plain, Delegate=yes, and
Delegate="memory pids") and reads, from inside each, which controllers the scope got and what
app.slice passes down to every application while the scope exists.
Part 2 puts one busy process in group X and four in group Y, all five pinned to one CPU, and
compares X's share of that CPU when the parent passes the cpu controller down and when it does
not. Only this probe's own children are pinned. No limit or weight is written anywhere, and
every cgroup made here is removed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/sys/fs/cgroup")
ME = os.getuid()
MANAGER = ROOT / "user.slice" / f"user-{ME}.slice" / f"user@{ME}.service"
JOIN = 'echo $$ > "$0/cgroup.procs" && exec "$@"'
INSIDE = (
    "import json, pathlib\n"
    "scope = pathlib.Path('/sys/fs/cgroup' + open('/proc/self/cgroup').read().strip()[3:])\n"
    "print(json.dumps({\n"
    "    'parent': scope.parent.name,\n"
    "    'scope': (scope / 'cgroup.controllers').read_text().strip(),\n"
    "    'down': (scope.parent / 'cgroup.subtree_control').read_text().strip(),\n"
    "    'cpu.stat present': (scope / 'cpu.stat').exists(),\n"
    "    'memory.peak present': (scope / 'memory.peak').exists(),\n"
    "    'cpu.weight present': (scope / 'cpu.weight').exists(),\n"
    "}))"
)
BURN = (
    "import os, sys, time\n"
    "os.sched_setaffinity(0, {int(sys.argv[1])})\n"
    "end = time.monotonic() + float(sys.argv[2])\n"
    "while time.monotonic() < end: pass"
)


def passed_down(group: Path) -> str:
    return (group / "cgroup.subtree_control").read_text().strip() or "nothing"


def scopes() -> None:
    print("1. what a transient scope switches on for its neighbours")
    print(f"  app.slice passes down, before: {passed_down(MANAGER / 'app.slice')}")
    for label, properties in (
        ("plain scope", []),
        ("Delegate=yes", ["-p", "Delegate=yes"]),
        ("Delegate=memory pids", ["-p", "Delegate=memory pids"]),
    ):
        command = ["systemd-run", "--user", "--scope", "--collect", "--quiet", *properties, "--"]
        done = subprocess.run(
            [*command, sys.executable, "-S", "-c", INSIDE], capture_output=True, text=True
        )
        if not done.stdout.strip():
            print(f"  {label}: failed ({done.stderr.strip()[:80]})")
            continue
        seen = json.loads(done.stdout)
        print(
            f"  {label}: scope has [{seen['scope']}]; {seen['parent']} passes down "
            f"[{seen['down']}] while it runs; cpu.stat "
            f"{seen['cpu.stat present']}, memory.peak {seen['memory.peak present']}, "
            f"cpu.weight {seen['cpu.weight present']}"
        )
    time.sleep(0.5)
    print(f"  app.slice passes down, afterwards: {passed_down(MANAGER / 'app.slice')}")
    apps = [child for child in (MANAGER / "app.slice").iterdir() if child.is_dir()]
    print(f"  cgroups directly below app.slice that the change applies to: {len(apps)}")


def usage(group: Path) -> int:
    return int((group / "cpu.stat").read_text().split()[1])


def share(parent: Path, cpu: int, seconds: float) -> float:
    """One burner in parent/x and four in parent/y on one CPU. Returns x's share of their sum."""
    x, y = parent / "x", parent / "y"
    x.mkdir()
    y.mkdir()
    try:
        burn = [sys.executable, "-S", "-c", BURN, str(cpu), str(seconds)]
        burners = [
            subprocess.Popen(["/bin/sh", "-c", JOIN, str(group), *burn])
            for group in (x, y, y, y, y)
        ]
        time.sleep(seconds / 4)
        x0, y0 = usage(x), usage(y)
        time.sleep(seconds / 2)
        dx, dy = usage(x) - x0, usage(y) - y0
        for burner in burners:
            burner.wait()
        return dx / (dx + dy)
    finally:
        x.rmdir()
        y.rmdir()


def weights() -> None:
    cpu = max(os.sched_getaffinity(0))
    parent = MANAGER / f"submeter-probe-w-{os.getpid()}"
    parent.mkdir()
    print("\n2. one busy process in group X against four in group Y, all on one CPU")
    try:
        print(f"  the delegated root passes down: {passed_down(MANAGER)}")
        off = share(parent, cpu, 2.0)
        (parent / "cgroup.subtree_control").write_text("+cpu")
        on = share(parent, cpu, 2.0)
        (parent / "cgroup.subtree_control").write_text("-cpu")
        print(f"  cpu controller not passed down to X and Y: X gets {off:.0%} (per thread: 20%)")
        print(f"  cpu controller passed down to X and Y:     X gets {on:.0%} (per group: 50%)")
        print("  weight written by this probe: none; each group keeps the default weight of 100")
    finally:
        parent.rmdir()
        print(f"  probe cgroup removed: {not parent.exists()}")


if __name__ == "__main__":
    scopes()
    weights()
