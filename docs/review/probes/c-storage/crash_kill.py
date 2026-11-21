"""Probe: kill a writer with SIGKILL in the middle of its writes, many times, and inspect the file.

Reads and measures only. Writes one raw file in a temporary folder. No timing is reported.

    .venv/bin/python docs/review/probes/c-storage/crash_kill.py [TRIALS]

A child process writes ticks to one raw file through the baseline's RawFile as fast as it can,
300 processes a tick, and prints each tick once its write has returned. The parent kills it after
a random number of ticks, so the kill lands inside a write, then checks integrity, how many
acknowledged ticks are missing, which side files are left, and whether the per-process CPU rows
still add up to the workload rows. The next child reopens the same file and carries on.

    crash_kill.py --write PATH FIRST_TICK      (the child; runs until killed)
"""

from __future__ import annotations

import random
import signal
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from _synth import DAY0, pipeline, proc, snap

from submeter.store.raw import RawFile

PROCESSES = 300


def rate(pid: int) -> float:
    """CPU seconds per tick. Most are under the 0.5% write threshold, so their rows are held."""
    return 0.0004 * (pid % 20)


PER_TICK = sum(rate(pid) for pid in range(PROCESSES))


def write_forever(path: Path, first: int) -> None:
    raw = RawFile(path)
    shots = (
        snap(DAY0 + tick, [proc(pid, rate(pid) * tick) for pid in range(PROCESSES)])
        for tick in range(first, 10**9)
    )
    for batch, workloads, names in pipeline(shots):
        tick = round(batch.taken_at - DAY0)
        raw.write(batch, workloads, names, keyframe=tick % 600 == 0)
        print(tick, flush=True)


def inspect(path: Path) -> tuple[str, int, int, float, float, list[str]]:
    """Side files as the kill left them, then what a fresh connection finds in the file."""
    side = sorted(f"{p.name[-4:]} {p.stat().st_size} B" for p in path.parent.glob("*.db-*"))
    db = sqlite3.connect(path)
    verdict = db.execute("PRAGMA integrity_check").fetchone()[0]
    ticks, workload_cpu, last = db.execute(
        "SELECT COUNT(*), SUM(cpu_s), MAX(ts) FROM workload_raw"
    ).fetchone()
    process_cpu = db.execute("SELECT SUM(cpu_s) FROM process_raw").fetchone()[0]
    db.close()
    return verdict, ticks, round(last - DAY0), workload_cpu / ticks, process_cpu, side


def main() -> None:
    trials = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    rng = random.Random(7)
    with tempfile.TemporaryDirectory() as folder:
        path, first, held_total = Path(folder) / "2026-11-20.db", 0, 0.0
        print(f"{PROCESSES} processes a tick, {PER_TICK:.3f} CPU-s a tick in total")
        for trial in range(1, trials + 1):
            child = subprocess.Popen(
                [sys.executable, __file__, "--write", str(path), str(first)],
                stdout=subprocess.PIPE,
                text=True,
            )
            assert child.stdout is not None
            for _ in range(rng.randint(20, 150)):
                child.stdout.readline()
            child.send_signal(signal.SIGKILL)
            acknowledged = [int(line) for line in child.stdout.read().split()]
            child.wait()
            verdict, ticks, stored, per_tick, process_cpu, side = inspect(path)
            held = ticks * PER_TICK - process_cpu - held_total
            held_total += held
            last_ack = acknowledged[-1] if acknowledged else stored
            print(
                f"trial {trial:2d}: integrity {verdict}; last tick acknowledged {last_ack}, last "
                f"stored {stored}, acknowledged ticks missing {max(0, last_ack - stored)}; "
                f"workload cpu a tick {per_tick:.3f}; CPU held back in memory and lost with the "
                f"process {held:.2f} s; side files before reopening: {side}"
            )
            first = stored + 1
        RawFile(path).close()
        left = sorted(p.name for p in Path(folder).iterdir())
        print(f"after a clean open and close: {left}")
        print(
            f"process rows are short of the workload rows by {held_total:.2f} CPU-s over "
            f"{trials} kills"
        )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--write":
        write_forever(Path(sys.argv[2]), int(sys.argv[3]))
    else:
        main()
