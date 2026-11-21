"""The route systemd supports for an unprivileged user: a transient scope it delegates.

Run from the repository root, never as root:
    uv run python docs/review/probes/a-linux/cgroup_scope.py

Part 1 reads where this login's processes live and who owns those cgroups. Part 2 asks the
user's own systemd for a short-lived scope with Delegate=yes, and inside it tries the layout
a launcher needs: one sub-group for itself, one for the command. Part 3 looks at what is left
once the scope has ended. Nothing is limited, and systemd removes the scope by itself.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/sys/fs/cgroup")
ME = os.getuid()
HOLDER = r"""
import json, os, subprocess, sys
scope = "/sys/fs/cgroup" + open("/proc/self/cgroup").read().strip()[3:]
def read(path):
    with open(scope + "/" + path) as handle:
        return handle.read().strip()
def write(path, text):
    try:
        with open(scope + "/" + path, "w") as handle:
            handle.write(text)
        return "allowed"
    except OSError as error:
        return "refused (" + error.strerror + ")"
report = {"slice": scope.split("/")[-2]}
report["owned by this user"] = os.stat(scope).st_uid == os.getuid()
report["controllers in the scope"] = read("cgroup.controllers")
report["processes in the scope at start"] = len(read("cgroup.procs").split())
report["passing memory down while this process is in it"] = write(
    "cgroup.subtree_control", "+memory")
os.mkdir(scope + "/holder"); os.mkdir(scope + "/payload")
report["moving this process into a sub-group"] = write("holder/cgroup.procs", str(os.getpid()))
report["passing cpu, memory and pids down after that"] = write(
    "cgroup.subtree_control", "+cpu +memory +pids")
join = 'echo $$ > "$0/cgroup.procs" && exec "$@"'
burn = "x = 0\nfor i in range(3000000): x += i * i"
command = ["/bin/sh", "-c", join, scope + "/payload", sys.executable, "-S", "-c", burn]
child = subprocess.Popen(command)
_, _, usage = os.wait4(child.pid, 0)
child.returncode = 0
report["payload files"] = sorted(n for n in os.listdir(scope + "/payload") if n in sys.argv[1:])
report["payload CPU seconds, kernel"] = int(read("payload/cpu.stat").split()[1]) / 1e6
report["payload CPU seconds, wait4"] = round(usage.ru_utime + usage.ru_stime, 6)
report["payload still populated"] = read("payload/cgroup.events").split()[1]
report["payload memory.peak MB, read after its last process ended"] = round(
    int(read("payload/memory.peak")) / 2**20, 1)
print(json.dumps(report))
sys.exit(7)
"""
FILES = ("cpu.stat", "memory.current", "memory.peak", "pids.current", "pids.peak", "io.stat")


def tidy(text: str) -> str:
    return re.sub(r"\d{3,}|[0-9a-f]{8}-[0-9a-f-]{27}", "N", text)


def where_this_login_lives() -> None:
    mine = ROOT / Path("/proc/self/cgroup").read_text().strip()[4:]
    print("1. where this login's processes live")
    for level in [*reversed(mine.parents[: len(mine.relative_to(ROOT).parts) - 1]), mine]:
        owner = "this user" if level.stat().st_uid == ME else "root"
        procs = "this user" if (level / "cgroup.procs").stat().st_uid == ME else "root"
        down = (level / "cgroup.subtree_control").read_text().strip() or "nothing"
        print(
            f"  {tidy(level.name):<40} owner {owner:<9} cgroup.procs {procs:<9} passes down {down}"
        )
    unit = subprocess.run(
        ["systemctl", "--user", "show", mine.name, "-p", "Delegate"], capture_output=True, text=True
    ).stdout.strip()
    print(f"  the scope this shell is in: {unit}")
    service = Path("/usr/lib/systemd/system/user@.service").read_text()
    print(f"  user@.service says: {re.findall(r'^Delegate=.*$', service, re.M)}")
    for scope in sorted((ROOT / "user.slice" / f"user-{ME}.slice").glob("session-*.scope")):
        pids = (scope / "cgroup.procs").read_text().split()
        own = sorted(Path(f"/proc/{p}/comm").read_text().strip() for p in pids if _owner(p) == ME)
        owner = "this user" if scope.stat().st_uid == ME else "root"
        print(f"  outside the delegated subtree: {tidy(scope.name)}, owner {owner}, holding")
        print(f"    {len(own)} of this user's processes: {own}")


def _owner(pid: str) -> int:
    try:
        return os.stat(f"/proc/{pid}").st_uid
    except OSError:
        return -1


def transient_scope() -> str:
    unit = f"submeter-probe-{os.getpid()}"
    command = ["systemd-run", "--user", "--scope", "--collect", "--quiet", "--unit", unit]
    command += ["-p", "Delegate=yes", "--", sys.executable, "-S", "-c", HOLDER, *FILES]
    done = subprocess.run(command, capture_output=True, text=True)
    print("\n2. a transient scope with Delegate=yes, asked of the user's own systemd")
    if not done.stdout.strip():
        print(f"  failed: {tidy(done.stderr.strip())}")
        return unit
    for key, item in json.loads(done.stdout).items():
        print(f"  {key}: {item}")
    print(f"  exit code passed through systemd-run: {done.returncode} (the holder exited with 7)")
    return unit


def afterwards(unit: str) -> None:
    base = ROOT / "user.slice" / f"user-{ME}.slice" / f"user@{ME}.service"
    deadline = time.monotonic() + 3
    while list(base.glob(f"*/{unit}.scope")) and time.monotonic() < deadline:
        time.sleep(0.05)
    left = list(base.glob(f"*/{unit}.scope"))
    show = subprocess.run(
        ["systemctl", "--user", "show", f"{unit}.scope", "-p", "LoadState", "-p", "CPUUsageNSec"],
        capture_output=True,
        text=True,
    ).stdout.split()
    print("\n3. after the scope's last process ended")
    print(f"  scope directory, with the sub-groups made inside it, still there: {bool(left)}")
    print(f"  what systemd still knows about it: {show}")
    bare = dict(os.environ)
    bare.pop("DBUS_SESSION_BUS_ADDRESS", None)
    bare.pop("XDG_RUNTIME_DIR", None)
    lost = subprocess.run(
        ["systemd-run", "--user", "--scope", "--quiet", "/bin/true"],
        capture_output=True,
        text=True,
        env=bare,
    )
    print("\n4. the same request from a login with no session bus (as under su, sudo -u or cron)")
    print(f"  exit code {lost.returncode}: {tidy(lost.stderr.strip())[:150]}")


if __name__ == "__main__":
    where_this_login_lives()
    afterwards(transient_scope())
