"""Can an unprivileged user get kernel totals for a process tree from cgroup v2, and how exact?

Run from the repository root, never as root:
    uv run python docs/review/probes/a-linux/cgroup_totals.py

It makes throwaway cgroups with mkdir inside the subtree systemd delegated to this user, moves
only its own child processes into them, reads the accounting files and removes every cgroup
again. It sets no limit and writes nothing but cgroup.procs and cgroup.subtree_control of the
cgroups it made. Paths are printed relative to the delegated subtree.
"""

from __future__ import annotations

import json
import os
import resource
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

ME = os.getuid()
JOIN = 'echo $$ > "$0/cgroup.procs" && exec "$@"'
FILES = ("cpu.stat", "memory.current", "memory.peak", "pids.current", "pids.peak", "io.stat")
BURN = "x = 0\nfor i in range(150000): x += i * i"
LEADER = """
import json, os, resource, sys, time
count, parallel, burn = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
born, cpu, lives = {}, 0.0, []
def reap():
    global cpu
    pid, _, usage = os.wait4(-1, 0)
    cpu += usage.ru_utime + usage.ru_stime
    lives.append(time.monotonic() - born.pop(pid))
for _ in range(count):
    if len(born) == parallel:
        reap()
    pid = os.posix_spawn(sys.executable, [sys.executable, "-S", "-c", burn], os.environ)
    born[pid] = time.monotonic()
while born:
    reap()
own = resource.getrusage(resource.RUSAGE_SELF)
report = {"children_cpu_s": cpu, "leader_cpu_s": own.ru_utime + own.ru_stime}
report |= {"mean_life_ms": 1000 * sum(lives) / len(lives), "longest_life_ms": 1000 * max(lives)}
print(json.dumps(report))
"""
THREADS = (
    "import threading, time\n"
    "for _ in range(8): threading.Thread(target=time.sleep, args=(30,), daemon=True).start()\n"
    "print('ready', flush=True); time.sleep(30)"
)
WRITER = (
    "import os, sys\n"
    "with open(sys.argv[1], 'wb') as f:\n"
    "    for _ in range(64): f.write(b'x' * (1 << 20))\n"
    "    f.flush(); os.fsync(f.fileno())"
)
Make = Callable[[Path], Path]


def own_cgroup() -> Path:
    return Path("/sys/fs/cgroup") / Path("/proc/self/cgroup").read_text().strip()[4:]


def delegated_root(start_at: Path) -> Path:
    top = start_at
    while top.parent.stat().st_uid == ME:
        top = top.parent
    return top


def start(group: Path, *argv: str, pipe: bool = False) -> subprocess.Popen[str]:
    """Start a command that joins the group before it runs."""
    command = ["/bin/sh", "-c", JOIN, str(group), *argv]
    return subprocess.Popen(
        command, text=True, stdout=subprocess.PIPE if pipe else None, stderr=subprocess.DEVNULL
    )


def reap(child: subprocess.Popen[str]) -> float:
    """Wait for a child and return the CPU seconds wait4 reports for it and its children."""
    _, status, usage = os.wait4(child.pid, 0)
    child.returncode = os.waitstatus_to_exitcode(status)
    return usage.ru_utime + usage.ru_stime


def usage_s(group: Path) -> float:
    return int((group / "cpu.stat").read_text().split()[1]) / 1e6


def mb(group: Path, name: str) -> str:
    return f"{int((group / name).read_text()) / 2**20:.1f} MB"


def value(group: Path, name: str) -> str:
    return (group / name).read_text().strip()


def populated(group: Path) -> str:
    return (group / "cgroup.events").read_text().split()[1]


def attempt(action: Callable[..., object], *args: object) -> str:
    try:
        action(*args)
        return "allowed"
    except OSError as error:
        return f"refused ({error.strerror})"


def lines(path: Path) -> int:
    return len(path.read_text().split())


def present(group: Path) -> str:
    return ", ".join(f"{name} {'yes' if (group / name).exists() else 'NO'}" for name in FILES)


def keys(group: Path) -> list[str]:
    return [line.split()[0] for line in (group / "cpu.stat").read_text().splitlines()]


def main() -> None:
    mine = own_cgroup()
    top = delegated_root(mine)
    print(f"delegated subtree starts {len(mine.relative_to(top).parts)} levels above this shell")
    print(f"  controllers there: {value(top, 'cgroup.controllers')}")
    print(f"  passed to its children: {value(top, 'cgroup.subtree_control')}")
    print(f"  this shell's own cgroup has: {value(mine, 'cgroup.controllers')}")
    made: list[Path] = []

    def make(path: Path) -> Path:
        path.mkdir()
        made.append(path)
        return path

    try:
        under_shell(make(mine / f"submeter-probe-a-{os.getpid()}"))
        base = make(top / f"submeter-probe-b-{os.getpid()}")
        print(f"\nB. cgroup made directly below the delegated root: {present(base)}")
        (base / "cgroup.subtree_control").write_text("+cpu +memory +pids")
        io = attempt((base / "cgroup.subtree_control").write_text, "+io")
        print(f"  passing cpu, memory and pids to its children: allowed; passing io: {io}")
        run = make(base / "run")
        print(f"  B/run: {present(run)}")
        short_children(run)
        after_exit(run)
        threads(run)
        left_behind(run)
        page_cache(run)
        nesting(run, make)
        rules(base, make)
    finally:
        for group in reversed(made):
            if not group.exists():
                continue
            for pid in (group / "cgroup.procs").read_text().split():
                os.kill(int(pid), signal.SIGKILL)  # only this probe's own children are in here
            deadline = time.monotonic() + 5
            while attempt(group.rmdir) != "allowed" and time.monotonic() < deadline:
                time.sleep(0.05)
        print(f"\nevery probe cgroup removed: {not any(group.exists() for group in made)}")


def under_shell(group: Path) -> None:
    print(f"\nA. cgroup made below this shell's own cgroup: {present(group)}")
    waited = reap(start(group, sys.executable, "-S", "-c", BURN))
    print(f"  one child moved in: cpu.stat {usage_s(group):.3f} s, wait4 {waited:.3f} s")
    print(f"  cpu.stat keys: {keys(group)}")


def short_children(run: Path) -> None:
    leader = start(run, sys.executable, "-S", "-c", LEADER, "200", "4", BURN, pipe=True)
    assert leader.stdout is not None
    report = json.loads(leader.stdout.read())
    tree, kernel = reap(leader), usage_s(run)
    print("\n1. 200 short children, 4 at a time, all started inside B/run")
    print(
        f"  mean life {report['mean_life_ms']:.0f} ms, longest {report['longest_life_ms']:.0f} ms"
    )
    print(
        f"  sum of the children's own CPU time from wait4: {report['children_cpu_s']:.3f} s; "
        f"the leader itself: {report['leader_cpu_s']:.3f} s"
    )
    print(f"  whole tree as wait4 reports it to this probe: {tree:.3f} s")
    print(f"  cpu.stat usage_usec of the group: {kernel:.3f} s ({kernel / tree - 1:+.2%})")
    print(f"  cpu.stat keys: {keys(run)}")


def after_exit(run: Path) -> None:
    time.sleep(2)
    print("\n2. two seconds after its last process exited")
    print(f"  directory still there: {run.is_dir()}; populated {populated(run)}")
    print(
        f"  cpu.stat {usage_s(run):.3f} s, memory.current {mb(run, 'memory.current')}, "
        f"memory.peak {mb(run, 'memory.peak')}, pids.current {value(run, 'pids.current')}, "
        f"pids.peak {value(run, 'pids.peak')}"
    )
    counters = [name for name in sorted(os.listdir(run)) if "fork" in name or "total" in name]
    print(f"  files that count processes ever started: {counters or 'none'}")
    print(f"  every file in the group: {' '.join(sorted(os.listdir(run)))}")


def threads(run: Path) -> None:
    child = start(run, sys.executable, "-S", "-c", THREADS, pipe=True)
    assert child.stdout is not None
    child.stdout.readline()
    print("\n3. one process with 8 extra threads")
    print(
        f"  pids.current {value(run, 'pids.current')}, "
        f"lines in cgroup.procs {lines(run / 'cgroup.procs')}, "
        f"lines in cgroup.threads {lines(run / 'cgroup.threads')}"
    )
    child.kill()
    child.wait()


def left_behind(run: Path) -> None:
    start(run, "/bin/sh", "-c", "setsid sleep 60 >/dev/null 2>&1 &").wait()
    time.sleep(0.2)
    stay = [int(pid) for pid in (run / "cgroup.procs").read_text().split()]
    stat = Path(f"/proc/{stay[0]}/stat").read_text()
    parent = int(stat[stat.rfind(")") + 2 :].split()[1])
    print("\n4. the command returned and left one background process")
    print(
        f"  still in the group: {len(stay)}; populated {populated(run)}; its parent is now "
        f"pid 1: {parent == 1}, named {Path(f'/proc/{parent}/comm').read_text().strip()}"
    )
    print(f"  removing the group now: {attempt(run.rmdir)}")
    os.kill(stay[0], signal.SIGKILL)
    while populated(run) != "0":
        time.sleep(0.02)
    print(f"  after that process ended: populated {populated(run)}, directory there {run.is_dir()}")


def page_cache(run: Path) -> None:
    with tempfile.TemporaryDirectory() as folder:
        before = mb(run, "memory.current")
        child = start(run, sys.executable, "-S", "-c", WRITER, f"{folder}/blob")
        _, _, usage = os.wait4(child.pid, 0)
        child.returncode = 0
        stat = dict(line.split() for line in (run / "memory.stat").read_text().splitlines())
        print("\n5. a child wrote a 64 MB file and exited; the group is empty again")
        print(f"  the child's own peak resident memory: {usage.ru_maxrss / 1024:.1f} MB")
        print(
            f"  memory.current before {before}, after {mb(run, 'memory.current')}, "
            f"memory.peak {mb(run, 'memory.peak')}, populated {populated(run)}"
        )
        print(
            f"  memory.stat: anon {int(stat['anon']) / 2**20:.1f} MB, "
            f"file {int(stat['file']) / 2**20:.1f} MB, kernel {int(stat['kernel']) / 2**20:.1f} MB"
        )
    time.sleep(0.5)
    print(f"  after the file was deleted: memory.current {mb(run, 'memory.current')}")


def nesting(run: Path, make: Make) -> None:
    before = usage_s(run)
    (run / "cgroup.subtree_control").write_text("+cpu +memory +pids")
    inner = make(run / "inner")
    reap(start(inner, sys.executable, "-S", "-c", BURN.replace("150000", "3000000")))
    spent = usage_s(inner)
    print("\n6. a group nested inside B/run")
    print(f"  B/run/inner: {present(inner)}")
    print(f"  inner used {spent:.3f} s; B/run grew by {usage_s(run) - before:.3f} s")
    inner.rmdir()
    print(f"  after inner was removed, B/run still holds it: {usage_s(run) - before:.3f} s")
    refused = start(run, "/bin/true").wait()
    print(f"  moving a process into B/run while it passes controllers down: exit code {refused}")
    (run / "cgroup.subtree_control").write_text("-cpu -memory -pids")


def rules(base: Path, make: Make) -> None:
    held, away = make(base / "held"), make(base / "away")
    sleeper = start(held, "/bin/sleep", "30")
    time.sleep(0.2)
    print("\n7. the rules a launcher has to work inside")
    answer = attempt((held / "cgroup.subtree_control").write_text, "+memory")
    print(f"  a group that holds a process passing memory to its children: {answer}")
    leave = 'echo $$ > "$0/cgroup.procs" && cat /proc/self/cgroup'
    mover = start(held, "/bin/sh", "-c", leave, str(away), pipe=True)
    assert mover.stdout is not None
    where = mover.stdout.read().strip().rsplit("/", 1)[-1]
    mover.wait()
    print(f"  a tagged process moving itself to a sibling group: ended up in '{where}'")
    print(f"  CPU time charged to the group it left: {usage_s(held):.3f} s")
    sleeper.kill()
    sleeper.wait()
    print(
        f"  resource limits set by this probe: none; own CPU {resource.getrusage(0).ru_utime:.2f} s"
    )


if __name__ == "__main__":
    main()
