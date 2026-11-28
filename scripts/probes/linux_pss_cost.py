"""What one round of reading every readable process's smaps_rollup (full PSS) costs (R46, B6, P0.7).

Run it from the repository root:  uv run python scripts/probes/linux_pss_cost.py

It lists the pids under /proc once, then reads and parses /proc/PID/smaps_rollup for each of them
once, and charges the round the CPU time time.process_time() says this process spent on it. The
kernel walks the target's page tables on the reader's account, so the cost grows with the memory
read. It prints the process count, their resident GB (1 GB = 1024**3 bytes,
docs/08-configuration.md:115), the CPU ms of the round and the ms per GB resident. Then, under
CQ-07, it picks the 25 largest of those processes by resident bytes, reads only theirs in a
second round and prints the same figures for it, so B6 has both rounds from one run. A pid that
vanishes or refuses the read during a round is skipped and counted, never read as 0.

It prints figures and decides nothing: the threshold is the owner's (B6). On CI the output is
labelled a CI-runner figure, because the runner is not the machine Submeter is for. It only
reads /proc: it changes no process and no setting, and opens no connection. On a system without
/proc it says so and exits 2.
"""

from __future__ import annotations

import os
import platform
import re
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

PROC = Path("/proc")
GB = 1024**3  # docs/08-configuration.md:115
TOP = 25  # CQ-07: the 25-largest round that B6's default compares with
USS_INTERVAL_S = 30.0  # B6 is judged at the 30 s uss_interval
LABEL = (
    "CI-runner figure: CPU time of one round of reading every readable process's "
    "/proc/PID/smaps_rollup, full PSS (R46, decision B6, gate P0.7)"
)
FIELD = re.compile(r"^(\w+):\s+(\d+) kB$")


@dataclass(frozen=True)
class PssFigures:
    """One round: how many processes were read, their resident memory and the round's CPU."""

    processes: int
    resident_gb: float
    cpu_ms: float
    ms_per_gb: float | None  # None when nothing was resident: unavailable, never 0


def parse_smaps_rollup(text: str) -> dict[str, int]:
    """Field name to bytes from /proc/PID/smaps_rollup; the file gives kB, the header no field."""
    found: dict[str, int] = {}
    for line in text.splitlines():
        match = FIELD.match(line.strip())
        if match:
            found[match.group(1)] = int(match.group(2)) * 1024
    return found


def pss_round_figures(resident_bytes: Sequence[int], cpu_s: float) -> PssFigures:
    """The figures of one round, from each process's resident bytes and the round's CPU seconds."""
    resident_gb = sum(resident_bytes) / GB
    cpu_ms = cpu_s * 1000
    return PssFigures(
        processes=len(resident_bytes),
        resident_gb=resident_gb,
        cpu_ms=cpu_ms,
        ms_per_gb=cpu_ms / resident_gb if resident_gb > 0 else None,
    )


def largest(resident_by_pid: Mapping[int, int], count: int = TOP) -> list[int]:
    """The pids of the count largest processes by resident bytes, largest first."""
    ranked = sorted(resident_by_pid, key=lambda pid: (-resident_by_pid[pid], pid))
    return ranked[:count]


def _lines(name: str, found: PssFigures, skipped: int) -> list[str]:
    per_gb = "unavailable" if found.ms_per_gb is None else f"{found.ms_per_gb:.2f} ms"
    return [
        f"{name}: processes read: {found.processes}",
        f"{name}: resident: {found.resident_gb:.3f} GB",
        f"{name}: CPU for the round: {found.cpu_ms:.3f} ms",
        f"{name}: CPU per GB resident: {per_gb}",
        f"{name}: share of one core, one round every {USS_INTERVAL_S:.0f} s: "
        f"{found.cpu_ms / 1000 / USS_INTERVAL_S:.4%}",
        f"{name}: reads skipped (process gone, read refused or no memory map): {skipped}",
    ]


def report(full: PssFigures, full_skipped: int, top: PssFigures, top_skipped: int) -> str:
    """The text the script prints, from the full round and the 25-largest round."""
    return "\n".join(
        [
            LABEL,
            f"{platform.platform()} | Python {platform.python_version()} | "
            f"{os.cpu_count()} logical cores",
            *_lines("full round", full, full_skipped),
            *_lines(f"{TOP}-largest round", top, top_skipped),
            f"full round minus {TOP}-largest round: {full.cpu_ms - top.cpu_ms:.3f} ms of CPU",
        ]
    )


def _pids() -> list[int]:
    return sorted(int(name) for name in os.listdir(PROC) if name.isdigit())


def _one_round(pids: Sequence[int]) -> tuple[float, dict[int, int], int]:
    """CPU seconds spent reading every pid's smaps_rollup once, resident bytes by pid, skipped."""
    resident: dict[int, int] = {}
    skipped = 0
    started = time.process_time()
    for pid in pids:
        try:
            fields = parse_smaps_rollup((PROC / str(pid) / "smaps_rollup").read_text())
        except OSError:
            skipped += 1
            continue
        if "Rss" in fields:
            resident[pid] = fields["Rss"]
        else:
            skipped += 1  # an exited process's file can be empty: no reading, not 0
    return time.process_time() - started, resident, skipped


def main() -> int:
    if not (PROC / "self" / "smaps_rollup").is_file():
        print(
            f"unavailable: {PROC} has no smaps_rollup on this system, so full PSS cannot be "
            "read. Run this on Linux 4.14 or later."
        )
        return 2
    full_s, resident, full_skipped = _one_round(_pids())
    top_s, top_resident, top_skipped = _one_round(largest(resident))
    full = pss_round_figures(list(resident.values()), full_s)
    top = pss_round_figures(list(top_resident.values()), top_s)
    print(report(full, full_skipped, top, top_skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
