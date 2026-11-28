"""The two Linux cost scripts of P0 (P0-W2-T4): one round of reading every leaf cgroup's cpu.stat
(R60, B5, gate P0.6) and one round of reading every readable process's smaps_rollup (R46, B6,
gate P0.7). Each script is loaded by path, because scripts/ is not a package.

Every input is inline, in the format of docs/review/probes/a-linux/ (docs/PLAN.md 7.3.1). The
few values taken from the review's Linux outputs are numbers only, with no user or host name
(docs/PLAN.md 7.3 rule 3); each input names its source in a comment.
"""

from __future__ import annotations

import functools
import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest

PROBES = Path(__file__).resolve().parents[1] / "scripts" / "probes"
GB = 1024**3  # docs/08-configuration.md:115
MB = 1024**2


@functools.cache
def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"linux_costs_{name}", PROBES / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up here
    spec.loader.exec_module(module)
    return module


# Source: docs/review/probes/a-linux/cgroup_totals.out.txt, section 1, "cpu.stat keys": the ten
# keys of a leaf cgroup's cpu.stat there, in that order, one "key value" pair a line.
# usage_usec is the 10.677 s printed there; the other values are made up.
CPU_STAT_LEAF = """\
usage_usec 10677123
user_usec 9876543
system_usec 800580
nice_usec 0
core_sched.force_idle_usec 0
nr_periods 0
nr_throttled 0
throttled_usec 0
nr_bursts 0
burst_usec 0
"""

# Source: docs/review/probes/a-linux/cgroup_totals.out.txt, section A: the five keys of a cgroup
# without the cpu controller. usage_usec is the 0.050 s printed there; the rest made up.
CPU_STAT_NO_CONTROLLER = """\
usage_usec 50211
user_usec 41003
system_usec 9208
nice_usec 0
core_sched.force_idle_usec 0
"""

# Source: the file docs/review/probes/a-linux/smaps_cost.py reads, /proc/PID/smaps_rollup: a
# "[rollup]" header line, then "Name:  value kB" lines. Rss is the 0.84 GB of the largest process
# in docs/review/probes/a-linux/smaps_cost.out.txt (880804 kB); the other values are made up,
# with Shared_* plus Private_* equal to Rss. The header's addresses are made up.
SMAPS_ROLLUP = """\
55d0c4a00000-7ffc1b5ff000 ---p 00000000 00:00 0                          [rollup]
Rss:              880804 kB
Pss:              512345 kB
Pss_Dirty:        400000 kB
Pss_Anon:         390000 kB
Pss_File:         120000 kB
Pss_Shmem:          2345 kB
Shared_Clean:     300000 kB
Shared_Dirty:      10000 kB
Private_Clean:    100000 kB
Private_Dirty:    470804 kB
Referenced:       850000 kB
Anonymous:        400000 kB
KSM:                   0 kB
LazyFree:              0 kB
AnonHugePages:         0 kB
ShmemPmdMapped:        0 kB
FilePmdMapped:         0 kB
Shared_Hugetlb:        0 kB
Private_Hugetlb:       0 kB
Swap:              20000 kB
SwapPss:           20000 kB
Locked:                0 kB
"""

# Source: docs/review/probes/a-linux/cgroup_whole_machine.out.txt, section 1: "235 cgroups on
# this machine, 224 of them leaves". The CPU seconds per round are made up.
LEAVES = 224
ROUNDS_S = [0.0031, 0.0029, 0.0042, 0.0030, 0.0110, 0.0033, 0.0028]

# Source: docs/review/probes/a-linux/smaps_cost.out.txt, section 1: the resident memory of the
# three largest processes, 0.84, 0.63 and 0.54 GB, in kB. The round's CPU time is made up.
RESIDENT_KB = [880804, 660603, 566231]
ROUND_CPU_S = 0.0567


def test_cpu_stat_is_parsed() -> None:
    cgroup = load("linux_cgroup_cost")
    leaf = cgroup.parse_cpu_stat(CPU_STAT_LEAF)
    assert leaf["usage_usec"] == 10677123
    assert leaf["user_usec"] == 9876543
    assert leaf["system_usec"] == 800580
    assert len(leaf) == 10
    bare = cgroup.parse_cpu_stat(CPU_STAT_NO_CONTROLLER)
    assert (bare["usage_usec"], bare["user_usec"], bare["system_usec"]) == (50211, 41003, 9208)


def test_smaps_rollup_is_parsed() -> None:
    pss = load("linux_pss_cost")
    rollup = pss.parse_smaps_rollup(SMAPS_ROLLUP)
    assert rollup["Rss"] == 880804 * 1024
    assert rollup["Pss"] == 512345 * 1024
    assert rollup["Swap"] == 20000 * 1024
    assert all(":" not in name and "[" not in name for name in rollup)  # the header is no field


def test_round_statistics() -> None:
    cgroup = load("linux_cgroup_cost")
    found = cgroup.round_statistics(ROUNDS_S, LEAVES)
    # Sorted: 0.0028 0.0029 0.0030 0.0031 0.0033 0.0042 0.0110; the middle of seven is 0.0031.
    assert found.median_s == pytest.approx(0.0031)
    assert found.worst_s == pytest.approx(0.0110)
    assert found.per_leaf_s == pytest.approx(0.0031 / 224)
    assert found.share_at_2s == pytest.approx(0.0031 / 2)  # 0.155% of one core
    assert found.share_at_5s == pytest.approx(0.0031 / 5)  # 0.062% of one core
    # An even number of rounds: the median is the mean of the two middle rounds.
    even = cgroup.round_statistics([0.004, 0.001, 0.003, 0.002], 10)
    assert even.median_s == pytest.approx(0.0025)
    assert even.worst_s == pytest.approx(0.004)
    assert even.per_leaf_s == pytest.approx(0.00025)


def test_pss_round_figures() -> None:
    pss = load("linux_pss_cost")
    resident = [kb * 1024 for kb in RESIDENT_KB]
    found = pss.pss_round_figures(resident, ROUND_CPU_S)
    resident_gb = (880804 + 660603 + 566231) * 1024 / GB  # 2.01 GB
    assert found.processes == 3
    assert found.resident_gb == pytest.approx(resident_gb)
    assert found.cpu_ms == pytest.approx(56.7)
    assert found.ms_per_gb == pytest.approx(56.7 / resident_gb)
    # With nothing resident there is no ms per GB: it is unavailable, never 0.
    empty = pss.pss_round_figures([], 0.0001)
    assert (empty.processes, empty.resident_gb, empty.ms_per_gb) == (0, 0.0, None)


def test_pss_25_largest_round() -> None:
    pss = load("linux_pss_cost")
    # 30 processes, made up: pid 2000 + i holds (i * 7 mod 30 + 1) * 50 MB, so the sizes are 50 MB
    # to 1500 MB, each once (7 and 30 share no factor), in a shuffled order.
    resident = {2000 + i: ((i * 7) % 30 + 1) * 50 * MB for i in range(30)}
    chosen = pss.largest(resident)
    assert len(chosen) == 25
    assert set(chosen) == {pid for pid, size in resident.items() if size >= 6 * 50 * MB}
    # Sizes 6 to 30 times 50 MB: (465 - 15) * 50 MB = 22500 MB.
    found = pss.pss_round_figures([resident[pid] for pid in chosen], 0.0123)
    assert found.processes == 25
    assert found.resident_gb == pytest.approx(22500 / 1024)


def test_outputs_are_labelled_ci_runner_figure() -> None:
    cgroup = load("linux_cgroup_cost")
    text = cgroup.report(LEAVES, ROUNDS_S, 3)
    assert text.startswith("CI-runner figure")
    assert "224" in text
    # A read that vanished or was refused is counted and printed, never added as 0.
    assert re.search(r"^.*skipped.*\b3\b", text, re.MULTILINE), text

    pss = load("linux_pss_cost")
    full = pss.pss_round_figures([kb * 1024 for kb in RESIDENT_KB], ROUND_CPU_S)
    top = pss.pss_round_figures([880804 * 1024], 0.0246)
    text = pss.report(full, 7, top, 0)
    assert text.startswith("CI-runner figure")
    assert re.search(r"^.*skipped.*\b7\b", text, re.MULTILINE), text
