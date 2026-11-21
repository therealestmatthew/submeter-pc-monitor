"""Probe: what the baseline's workload memory total is, against the brief's "USS or PSS".

The psutil provider puts one memory figure per process in ProcessCounters.memory_bytes (RSS on
Linux, private bytes on Windows) and aggregate() sums it per workload. docs/06 says workload
totals use USS or PSS. This groups the signed-in user's own processes by name, as a rule on
exe would, and prints the summed RSS beside the summed PSS and USS for the largest groups.
Reads /proc only; writes nothing. Run from the repository root:

    uv run python docs/review/probes/e-baseline/memory_sum.py
"""

from __future__ import annotations

import os
from collections import defaultdict

import psutil

MIB = 1024**2


def main() -> None:
    groups: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
    me = os.getuid()
    for process in psutil.process_iter():
        try:
            if process.uids().real != me:
                continue
            full = process.memory_full_info()
            groups[process.name()].append((full.rss, full.pss, full.uss))
        except psutil.Error:
            continue
    multi = {name: rows for name, rows in groups.items() if len(rows) > 1}
    largest = sorted(multi.items(), key=lambda item: -sum(row[0] for row in item[1]))[:5]
    print("name, processes, summed RSS, summed PSS, summed USS (MiB), RSS over PSS")
    for name, rows in largest:
        rss, pss, uss = (sum(row[i] for row in rows) / MIB for i in range(3))
        figures = f"{rss:>9.0f} {pss:>9.0f} {uss:>9.0f}  x{rss / pss:.2f}"
        print(f"   {name[:16]:<16} {len(rows):>3} {figures}")
    every = [row for rows in groups.values() for row in rows]
    rss, pss = (sum(row[i] for row in every) / MIB for i in range(2))
    print(f"all {len(every)} own processes: RSS {rss:.0f} MiB, PSS {pss:.0f} MiB, x{rss / pss:.2f}")


if __name__ == "__main__":
    main()
