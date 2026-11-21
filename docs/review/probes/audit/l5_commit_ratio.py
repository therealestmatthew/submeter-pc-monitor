"""Audit probe for cluster L5: does Committed_AS / CommitLimit exceed 1 on this Linux machine?

Reads /proc/meminfo and /proc/sys/vm/overcommit_memory only. Prints the commit ratio the
built-in 'memory nearly full' rule (commit_fraction above 0.90) would see, next to the
share of memory in use (1 - MemAvailable / MemTotal), and the swap size that sets
CommitLimit in modes 0 and 1. No timing, no writes, nothing sent anywhere.

    python3 docs/review/probes/audit/l5_commit_ratio.py
"""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    fields: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        name, _, rest = line.partition(":")
        fields[name] = int(rest.split()[0])  # kB
    mode = Path("/proc/sys/vm/overcommit_memory").read_text().strip()
    ratio_pct = Path("/proc/sys/vm/overcommit_ratio").read_text().strip()
    committed, limit = fields["Committed_AS"], fields["CommitLimit"]
    total, avail, swap = fields["MemTotal"], fields["MemAvailable"], fields["SwapTotal"]
    gib = 1024 * 1024
    print(f"vm.overcommit_memory {mode}; vm.overcommit_ratio {ratio_pct}%")
    print(f"MemTotal {total / gib:.1f} GiB, SwapTotal {swap / gib:.1f} GiB")
    print(f"CommitLimit {limit / gib:.1f} GiB = swap + ratio x RAM")
    print(f"Committed_AS {committed / gib:.1f} GiB")
    print(f"commit_fraction = Committed_AS / CommitLimit = {committed / limit:.2f}")
    print(f"memory in use = 1 - MemAvailable / MemTotal = {1 - avail / total:.2f}")
    print(f"built-in rule 'commit_fraction above 0.90' would fire: {committed / limit > 0.90}")
    print(
        f"Committed_AS / (MemTotal + SwapTotal) = {committed / (total + swap):.2f} "
        "(the denominator Windows uses for its commit limit: RAM plus page file)"
    )


if __name__ == "__main__":
    main()
