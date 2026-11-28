"""What one round of reading every leaf cgroup's cpu.stat costs on this machine (R60, B5, P0.6).

Run it from the repository root:  uv run python scripts/probes/linux_cgroup_cost.py

It lists the leaf cgroups under /sys/fs/cgroup (cgroup v2) once, then reads and parses every
leaf's cpu.stat in each of 100 rounds, and charges each round the CPU time time.process_time()
says this process spent on it. It prints the leaf count, the median and worst CPU per round, the
cost per leaf (median round over the leaf count), and the share of one core the median round
takes at a 2 s and at a 5 s interval. A leaf that vanishes or refuses a read during a round is
skipped and counted, never read as 0.

It prints figures and decides nothing: the threshold is the owner's (B5). On CI the output is
labelled a CI-runner figure, because the runner is not the machine Submeter is for. It only
reads /sys: it changes no process and no setting, and opens no connection. On a system without
a cgroup v2 tree at /sys/fs/cgroup it says so and exits 2.
"""

from __future__ import annotations

import os
import platform
import statistics
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path("/sys/fs/cgroup")
ROUNDS = 100
INTERVALS_S = (2.0, 5.0)
LABEL = (
    "CI-runner figure: CPU time of one round of reading every leaf cgroup's cpu.stat "
    "(R60, decision B5, gate P0.6)"
)


@dataclass(frozen=True)
class RoundStatistics:
    """CPU seconds per round, and what the median round costs per leaf and per interval."""

    median_s: float
    worst_s: float
    per_leaf_s: float | None  # None when there is no leaf: unavailable, never 0
    share_at_2s: float  # fraction of one core
    share_at_5s: float


def parse_cpu_stat(text: str) -> dict[str, int]:
    """Key to value from a cgroup v2 cpu.stat file: one "key value" pair a line."""
    found: dict[str, int] = {}
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        if len(parts) != 2:
            raise ValueError(f"a cpu.stat line has two fields, got {line!r}")
        found[parts[0]] = int(parts[1])
    return found


def round_statistics(cpu_s: Sequence[float], leaves: int) -> RoundStatistics:
    """The median and worst of the CPU seconds per round, its cost per leaf and share of a core."""
    if not cpu_s:
        raise ValueError("no round was measured")
    median = statistics.median(cpu_s)
    return RoundStatistics(
        median_s=median,
        worst_s=max(cpu_s),
        per_leaf_s=median / leaves if leaves > 0 else None,
        share_at_2s=median / INTERVALS_S[0],
        share_at_5s=median / INTERVALS_S[1],
    )


def report(leaves: int, cpu_s: Sequence[float], skipped: int) -> str:
    """The text the script prints, from the leaf count, CPU seconds per round and skipped reads."""
    found = round_statistics(cpu_s, leaves)
    per_leaf = "unavailable" if found.per_leaf_s is None else f"{found.per_leaf_s * 1e6:.2f} us"
    return "\n".join(
        [
            LABEL,
            f"{platform.platform()} | Python {platform.python_version()} | "
            f"{os.cpu_count()} logical cores",
            f"leaf cgroups: {leaves}",
            f"rounds: {len(cpu_s)}, each reading and parsing every leaf's cpu.stat once",
            f"median CPU per round: {found.median_s * 1000:.3f} ms",
            f"worst CPU per round: {found.worst_s * 1000:.3f} ms",
            f"cost per leaf (median round / leaf count): {per_leaf}",
            f"share of one core, median round every 2 s: {found.share_at_2s:.4%}",
            f"share of one core, median round every 5 s: {found.share_at_5s:.4%}",
            f"reads skipped (cgroup gone or read refused): {skipped} of {leaves * len(cpu_s)}",
        ]
    )


def _leaves(root: Path) -> list[Path]:
    """Every cgroup below root, root included, that has no child cgroup and has a cpu.stat."""
    found: list[Path] = []
    for folder, children, files in os.walk(root):
        if not children and "cpu.stat" in files:
            found.append(Path(folder) / "cpu.stat")
    return found


def _one_round(files: Sequence[Path]) -> tuple[float, int]:
    """CPU seconds this process spent reading and parsing every file once, and the reads skipped."""
    skipped = 0
    started = time.process_time()
    for path in files:
        try:
            parse_cpu_stat(path.read_text())
        except OSError:
            skipped += 1
    return time.process_time() - started, skipped


def main() -> int:
    if not (ROOT / "cgroup.controllers").is_file():
        print(
            f"unavailable: {ROOT} holds no cgroup v2 tree on this system, so there is no "
            "cpu.stat to read. Run this on Linux with cgroup v2."
        )
        return 2
    files = _leaves(ROOT)
    if not files:
        print(f"unavailable: no leaf cgroup under {ROOT} has a cpu.stat.")
        return 2
    rounds: list[float] = []
    skipped = 0
    for _ in range(ROUNDS):
        spent, missed = _one_round(files)
        rounds.append(spent)
        skipped += missed
    print(report(len(files), rounds, skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
