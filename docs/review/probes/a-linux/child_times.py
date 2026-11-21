"""What a parent's child-time counters (cutime and cstime in /proc/PID/stat) can recover.

Run from the repository root:
    uv run python docs/review/probes/a-linux/child_times.py

Each case starts a parent that starts a child doing a fixed amount of arithmetic. The probe
reads the parent's counters from outside, as a collector would. The last part polls a parent
that starts many short children and a few long ones, and compares three totals: what polling
saw, polling plus the counters, and polling plus the counters less what was already seen.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

TICK = os.sysconf("SC_CLK_TCK")
BURN = "x = 0\nfor i in range(5000000): x += i * i"
HEAD = (
    "import os, signal, subprocess, sys, time\n"
    "burn, python = sys.argv[1], sys.executable\n"
    "def shell(script):\n"
    "    done = subprocess.run(['/bin/sh', '-c', script, python, burn], capture_output=True)\n"
    "    return done.stdout.decode().strip()\n"
)
TAIL = "\nprint('done', flush=True)\nsys.stdin.readline()"
CASES = {
    "child waited for": "subprocess.run([python, '-S', '-c', burn])",
    "grandchild, waited for by a shell in between": 'shell(\'"$0" -S -c "$1"; exit 0\')',
    "grandchild orphaned, its parent exits at once": (
        'orphan = shell(\'"$0" -S -c "$1" >/dev/null 2>&1 & echo $!\')\n'
        "print('orphan', orphan, flush=True)\n"
        "while os.path.exists('/proc/' + orphan): time.sleep(0.02)"
    ),
    "child ended while the parent ignores SIGCHLD": (
        "signal.signal(signal.SIGCHLD, signal.SIG_IGN)\n"
        "pid = os.posix_spawn(python, [python, '-S', '-c', burn], os.environ)\n"
        "while os.path.exists(f'/proc/{pid}'): time.sleep(0.02)"
    ),
}
SPAWNER = (
    "import os, sys\n"
    "live, cpu = set(), 0.0\n"
    "def reap():\n"
    "    global cpu\n"
    "    pid, _, usage = os.wait4(-1, 0)\n"
    "    live.discard(pid); cpu += usage.ru_utime + usage.ru_stime\n"
    "for n in range(80):\n"
    "    if len(live) == 3: reap()\n"
    "    loops = '9000000' if n % 20 == 0 else '300000'\n"
    "    code = 'x = 0\\nfor i in range(' + loops + '): x += i * i'\n"
    "    live.add(os.posix_spawn(sys.executable, [sys.executable, '-S', '-c', code], os.environ))\n"
    "while live: reap()\n"
    "print(cpu, flush=True)\n"
    "sys.stdin.readline()"
)


def times(pid: int) -> tuple[int, float, float]:
    """Parent pid, own CPU seconds and reaped children's CPU seconds, from /proc/PID/stat."""
    stat = Path(f"/proc/{pid}/stat").read_text()
    fields = stat[stat.rfind(")") + 2 :].split()
    own = (int(fields[11]) + int(fields[12])) / TICK
    return int(fields[1]), own, (int(fields[13]) + int(fields[14])) / TICK


def case(name: str, body: str) -> None:
    command = [sys.executable, "-S", "-c", HEAD + body + TAIL, BURN]
    parent = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    assert parent.stdin is not None and parent.stdout is not None
    line, note = parent.stdout.readline(), ""
    if line.startswith("orphan"):
        adopter, _, _ = times(int(line.split()[1]))
        before = times(adopter)[2]
        parent.stdout.readline()
        comm = Path(f"/proc/{adopter}/comm").read_text().strip()
        note = (
            f"; adopted by '{comm}' (pid 1: {adopter == 1}), whose own counter rose by "
            f"{times(adopter)[2] - before:.2f} s"
        )
    print(f"  {name}: parent's counter shows {times(parent.pid)[2]:.2f} s{note}")
    parent.stdin.close()
    parent.wait()


def children_of(parent: int) -> dict[int, float]:
    found: dict[int, float] = {}
    for name in os.listdir("/proc"):
        if name.isdigit():
            try:
                ppid, own, _ = times(int(name))
            except OSError:
                continue
            if ppid == parent:
                found[int(name)] = own
    return found


def polled() -> None:
    command = [sys.executable, "-S", "-c", SPAWNER]
    parent = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    assert parent.stdin is not None and parent.stdout is not None
    os.set_blocking(parent.stdout.fileno(), False)
    last: dict[int, float] = {}
    seen = naive = exact = counter = 0.0
    finished = b""
    while not finished:
        time.sleep(0.5)
        finished = parent.stdout.read() or b""
        alive = children_of(parent.pid)
        now = times(parent.pid)[2]
        sighted = sum(own - last.get(pid, 0.0) for pid, own in alive.items())
        gone = sum(own for pid, own in last.items() if pid not in alive)
        seen += sighted
        naive += sighted + (now - counter)
        exact += sighted + (now - counter) - gone
        counter, last = now, alive
    truth = float(finished)
    print(f"  truth, from wait4 inside the parent: {truth:.2f} s for 80 children")
    print(f"  polling alone, each child up to its last sighting: {seen:.2f} s")
    print(f"  polling plus the parent's counter: {naive:.2f} s ({naive / truth - 1:+.0%})")
    print(f"  the same, less the last sighting of each child that ended: {exact:.2f} s")
    parent.stdin.close()
    parent.wait()


def main() -> None:
    reference = subprocess.Popen([sys.executable, "-S", "-c", BURN])
    _, _, usage = os.wait4(reference.pid, 0)
    reference.returncode = 0
    print(f"the child's work costs {usage.ru_utime + usage.ru_stime:.2f} s of CPU time")
    print(f"counters are in ticks of {1000 // TICK} ms\n\n1. what reaches the parent's counter")
    for name, body in CASES.items():
        case(name, body)
    print("\n2. a parent polled every 0.5 s while it runs 76 short children and 4 long ones")
    polled()


if __name__ == "__main__":
    main()
