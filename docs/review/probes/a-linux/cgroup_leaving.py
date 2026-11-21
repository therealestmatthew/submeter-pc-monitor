"""Who may move a process into a tagged group, and what takes a process out of one again?

Run from the repository root, never as root:
    uv run python docs/review/probes/a-linux/cgroup_leaving.py

Part 1 reproduces the kernel's containment rule with this probe's own cgroups: a move needs
write access to cgroup.procs of the common ancestor of source and destination. A login whose
processes sit in a root-owned session scope fails that test; here the ancestor's file is made
read-only for a moment instead, which the kernel checks in the same way.
Part 2 starts commands inside a tagged group and prints where they end up: a plain child, a
command started through the user's systemd, and a snap application's own launcher.
Only this probe's children are moved. Every cgroup made here is removed.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path("/sys/fs/cgroup")
ME = os.getuid()
MANAGER = ROOT / "user.slice" / f"user-{ME}.slice" / f"user@{ME}.service"
JOIN = 'echo $$ > "$0/cgroup.procs" && exec "$@"'
SHOW = "cat /proc/self/cgroup"


def tidy(text: str) -> str:
    return re.sub(r"[0-9a-f]{8}-[0-9a-f-]{27}|\d{3,}", "N", text)


def attempt(path: Path, text: str) -> str:
    try:
        path.write_text(text)
        return "allowed"
    except OSError as error:
        return f"refused ({error.strerror})"


def containment(base: Path) -> None:
    outer, source, target = base / "outer", base / "outer" / "from", base / "outer" / "to"
    for group in (outer, source, target):
        group.mkdir()
    sleeper = subprocess.Popen(["/bin/sh", "-c", JOIN, str(source), "/bin/sleep", "30"])
    time.sleep(0.2)
    procs = outer / "cgroup.procs"
    print("1. moving a process between two groups under a common ancestor")
    try:
        os.chmod(procs, 0o444)
        print(
            "  ancestor's cgroup.procs not writable by this user: "
            f"{attempt(target / 'cgroup.procs', str(sleeper.pid))}"
        )
        os.chmod(procs, 0o644)
        print(
            "  ancestor's cgroup.procs writable by this user:     "
            f"{attempt(target / 'cgroup.procs', str(sleeper.pid))}"
        )
    finally:
        os.chmod(procs, 0o644)
        sleeper.kill()
        sleeper.wait()
        remove(target, source, outer)
    session = [
        scope
        for scope in (ROOT / "user.slice" / f"user-{ME}.slice").glob("session-*.scope")
        if (scope / "cgroup.procs").stat().st_uid != ME
    ]
    owner = (ROOT / "user.slice" / f"user-{ME}.slice" / "cgroup.procs").stat().st_uid
    print(
        f"  session scopes of this user that are owned by root: {len(session)}; their common "
        f"ancestor with the delegated subtree has cgroup.procs owned by uid {owner}"
    )


def remove(*groups: Path) -> None:
    for group in groups:
        deadline = time.monotonic() + 3
        while group.exists() and time.monotonic() < deadline:
            try:
                group.rmdir()
            except OSError:
                time.sleep(0.05)


def lands(group: Path, *command: str) -> str:
    done = subprocess.run(
        ["/bin/sh", "-c", JOIN, str(group), *command], capture_output=True, text=True, timeout=60
    )
    where = done.stdout.strip().splitlines()[-1:] or [f"no answer ({done.stderr.strip()[:60]})"]
    path = where[0][3:] if where[0].startswith("0::") else where[0]
    inside = path.startswith(str(group)[len(str(ROOT)) :])
    verdict = "still inside the group" if inside else "OUTSIDE the group"
    return f"{verdict}: .../{tidy(path).rsplit('/', 1)[-1]}"


def leaving(base: Path) -> None:
    group = base / "tagged"
    group.mkdir()
    print("\n2. commands started inside a tagged group, and where they run")
    try:
        print(f"  a plain child:                         {lands(group, '/bin/sh', '-c', SHOW)}")
        run = ["systemd-run", "--user", "--scope", "--collect", "--quiet", "/bin/sh", "-c", SHOW]
        print(f"  through systemd-run --user --scope:    {lands(group, *run)}")
        snaps = [
            name
            for name in ("firefox", "thunderbird", "code", "chromium")
            if Path(f"/snap/bin/{name}").exists()
        ]
        if shutil.which("snap") and snaps:
            run = ["snap", "run", "--shell", snaps[0], "-c", SHOW]
            print(f"  through the launcher of a snap ({snaps[0]}): {lands(group, *run)}")
        else:
            print("  no snap application found to try")
        usage = int((group / "cpu.stat").read_text().split()[1]) / 1e6
        populated = (group / "cgroup.events").read_text().split()[1]
        print(f"  the tagged group afterwards: populated {populated}, CPU charged {usage:.3f} s")
    finally:
        for pid in (group / "cgroup.procs").read_text().split():
            os.kill(int(pid), signal.SIGKILL)
        remove(group)


def main() -> None:
    base = MANAGER / f"submeter-probe-l-{os.getpid()}"
    base.mkdir()
    try:
        containment(base)
        leaving(base)
    finally:
        remove(base)
        print(f"\nevery probe cgroup removed: {not base.exists()}")


if __name__ == "__main__":
    main()
